"""Conservative scratch ownership/GC, actual subprocess hooks, no fake model output."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path

import psutil
import pytest
from app.main import create_app
from app.services.media.runner import run_command
from app.services.media.workspaces import (
    MARKER,
    ProcessIdentity,
    ScratchWorkspace,
    recover_workspaces,
)
from fastapi.testclient import TestClient


def abandoned(cache, kind="scenes"):
    cache.mkdir(parents=True, exist_ok=True)
    workspace = ScratchWorkspace(cache, kind).__enter__()
    # Explicit simulated reused PID identity: the current PID has a different creation time.
    workspace.record.owner.created += 1
    workspace.checkpoint()
    return workspace


def test_regular_cleanup_unlinks_scratch_alias_not_original_bytes(tmp_path):
    original = tmp_path / "original.mp4"
    original.write_bytes(b"owned source bytes")
    cache = tmp_path / "cache"
    workspace = abandoned(cache)
    os.link(original, workspace.path / "input")
    before = original.read_bytes()
    report = recover_workspaces(cache)
    assert report["removed"] == 1
    assert report["retained"] == 0
    assert not workspace.path.exists()
    assert original.read_bytes() == before


def test_actual_command_is_journalled_then_reaped_before_normal_cleanup(tmp_path):
    with ScratchWorkspace(tmp_path, "rhythm") as workspace:
        seen = []
        original_spawned = workspace.spawned

        def record(pid):
            original_spawned(pid)
            body = json.loads((workspace.path / MARKER).read_text())
            seen.append(body)

        workspace.spawned = record
        run_command(
            [sys.executable, "-c", "import time; time.sleep(.2); print('done')"],
            timeout=3,
            lifecycle=workspace,
        )
        assert len(seen) == 1
        assert not seen[0]["launching"]
        assert seen[0]["child"]["pid"] != os.getpid()
        assert workspace.record.child is None
        assert not workspace.record.launching
        assert recover_workspaces(tmp_path)["retained"] == 1  # live owner is never GC'ed
    assert not workspace.path.exists()


@pytest.mark.parametrize(
    "fault",
    [
        "unknown",
        "nested",
        "symlink",
        "marker-link",
        "oversize",
        "invalid",
        "folder",
        "launch",
        "live-child",
        "live-owner",
    ],
)
def test_ambiguous_or_live_owned_content_is_retained(tmp_path, fault):
    workspace = abandoned(tmp_path)
    external = tmp_path / "external"
    external.write_bytes(b"never remove user content")
    if fault == "unknown":
        (workspace.path / "not-a-scratch-file").write_text("keep")
    elif fault == "nested":
        (workspace.path / "input").mkdir()
    elif fault == "symlink":
        (workspace.path / "input").symlink_to(external)
    elif fault == "marker-link":
        (workspace.path / MARKER).unlink()
        (workspace.path / MARKER).symlink_to(external)
    elif fault == "oversize":
        (workspace.path / MARKER).write_bytes(b"x" * 4097)
    elif fault == "invalid":
        (workspace.path / MARKER).write_text("not-json")
    elif fault == "folder":
        workspace.record.folder = "../other"
        workspace.checkpoint()
    elif fault == "launch":
        workspace.before_spawn()
    elif fault == "live-child":
        workspace.record.child = ProcessIdentity.current(os.getpid())
        workspace.checkpoint()
    elif fault == "live-owner":
        workspace.record.owner = ProcessIdentity.current(os.getpid())
        workspace.checkpoint()
    report = recover_workspaces(tmp_path)
    assert report["retained"] == 1
    assert report["removed"] == 0
    assert workspace.path.exists()
    assert external.read_bytes() == b"never remove user content"


def test_legacy_and_unrelated_cache_is_not_inferred_from_age_or_prefix(tmp_path):
    for name in ("scenes-legacy", "rhythm-legacy", "user-stuff"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "input").write_text("leave untouched")
    assert recover_workspaces(tmp_path)["scanned"] == 0
    assert all((p / "input").exists() for p in tmp_path.iterdir())


def test_parent_directory_symlink_never_traversed(tmp_path):
    external = tmp_path / "user-directory"
    external.mkdir()
    (external / "input").write_text("keep")
    alias = tmp_path / "managed-scenes-alias"
    alias.symlink_to(external, target_is_directory=True)
    assert recover_workspaces(tmp_path)["retained"] == 1
    assert (external / "input").read_text() == "keep"


def test_callback_failure_reaps_child_and_preserves_original_error(tmp_path, monkeypatch):
    with ScratchWorkspace(tmp_path, "scenes") as workspace:
        pids = []

        def fail(pid):
            pids.append(pid)
            raise ValueError("Fixture journal callback error")

        monkeypatch.setattr(workspace, "spawned", fail)
        with pytest.raises(ValueError, match="journal callback"):
            run_command(
                [sys.executable, "-c", "import time; time.sleep(20)"],
                timeout=3,
                lifecycle=workspace,
            )
        assert not psutil.pid_exists(pids[0])
        assert not workspace.record.launching
    assert not workspace.path.exists()


def test_failed_spawn_never_claims_reaped_child(tmp_path):
    with ScratchWorkspace(tmp_path, "scenes") as workspace, pytest.raises(FileNotFoundError):
        run_command([str(tmp_path / "missing-executable")], lifecycle=workspace)
    # No child identity was publishable: keep, do not guess from the parent's death.
    assert workspace.path.exists()
    workspace.record.owner.created += 1
    workspace.checkpoint()
    assert recover_workspaces(tmp_path)["retained"] == 1


def test_real_dead_parent_workspace_is_recovered_at_app_startup(settings):
    settings.ensure_dirs()
    script = """
import os,sys
from pathlib import Path
from app.services.media.workspaces import ScratchWorkspace
w=ScratchWorkspace(Path(sys.argv[1]),'rhythm').__enter__()
(w.path/'audio.wav').write_bytes(b'owned partial PCM')
print(w.path,flush=True)
os._exit(0)
"""
    folder = Path(
        subprocess.check_output(
            [sys.executable, "-c", script, str(settings.cache_dir)], text=True
        ).strip()
    )
    assert folder.exists()
    with TestClient(create_app(settings)) as client:
        body = client.get("/api/v1/system/diagnostics").json()
        assert body["paths"]["data_dir"] == str(settings.data_dir)
        assert body["cache_recovery"]["removed"] == 1
        assert body["cache_recovery"]["retained"] == 0
    assert not folder.exists()


def test_absent_process_is_inactive_not_access_failure():
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(.2)"])
    identity = ProcessIdentity.current(child.pid)
    child.wait(timeout=3)
    assert not identity.alive()


def test_cancelled_native_command_reaps_before_workspace_removed(tmp_path):
    cancel = threading.Event()
    timer = threading.Timer(0.15, cancel.set)
    timer.start()
    from app.services.media.runner import CommandCancelledError

    try:
        with (
            ScratchWorkspace(tmp_path, "scenes") as workspace,
            pytest.raises(CommandCancelledError),
        ):
            run_command(
                [sys.executable, "-c", "import time; time.sleep(20)"],
                timeout=3,
                cancel_event=cancel,
                lifecycle=workspace,
            )
        assert not workspace.path.exists()
    finally:
        timer.cancel()
        timer.join()


def test_unreadable_process_identity_is_retained_and_logged(tmp_path, monkeypatch, caplog):
    workspace = abandoned(tmp_path)

    def denied(_self):
        raise psutil.AccessDenied(os.getpid())

    monkeypatch.setattr(ProcessIdentity, "alive", denied)
    assert recover_workspaces(tmp_path)["retained"] == 1
    assert workspace.path.exists()
    assert "scratch.recovery.retained" in caplog.text


def test_scan_budget_includes_unrelated_entries_and_never_sweeps_them(tmp_path):
    from app.services.media.workspaces import SCAN_LIMIT

    for index in range(SCAN_LIMIT + 1):
        (tmp_path / f"unrelated-{index}").touch()
    report = recover_workspaces(tmp_path)
    assert report["limited"] is True
    assert report["removed"] == report["retained"] == 0
    assert len(list(tmp_path.iterdir())) == SCAN_LIMIT + 1


def test_cleanup_permission_error_is_logged_and_actionable(tmp_path, monkeypatch, caplog):
    workspace = abandoned(tmp_path)

    def denied(_path):
        raise PermissionError("Fixture deletion denied")

    monkeypatch.setattr(Path, "unlink", denied)
    report = recover_workspaces(tmp_path)
    assert report["retained"] == 1
    assert "Fixture deletion denied" in report["entries"][0]["reason"]
    assert "scratch.recovery.retained" in caplog.text
    assert workspace.path.exists()


def test_reparse_directory_is_not_considered_ordinary(tmp_path, monkeypatch):
    import stat
    from types import SimpleNamespace

    from app.services.media.workspaces import ordinary

    monkeypatch.setattr(
        Path,
        "lstat",
        lambda _: SimpleNamespace(
            st_mode=stat.S_IFDIR, st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT
        ),
    )
    assert not ordinary(tmp_path, directory=True)
