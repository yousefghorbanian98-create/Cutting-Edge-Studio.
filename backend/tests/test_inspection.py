"""Inspection uses actual IDs/jobs/artifacts; fake measurements here are explicit unit fixtures."""

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path

import pytest
from app.main import create_app
from app.models import Artifact
from app.schemas_inspection import InspectedFile, InspectionRead
from app.services.media.inspection import FFmpegInspector, decode_command
from app.services.media.probe import parse_probe
from app.services.media.progress import ProgressEvent
from app.services.media.runner import CommandCancelledError, CommandResult
from fastapi.testclient import TestClient
from tests.fixtures import FFPROBE_VIDEO
from tests.test_assets_api import FakeProber


class FixtureInspector:
    """Explicit metadata/decode fixture, never used by the production application."""

    def inspect(self, asset, cancel, progress):
        if cancel.is_set():
            raise CommandCancelledError("Fixture cancelled")
        progress(45)
        info = Path(asset.path).stat()
        return InspectedFile(
            asset_id=asset.id,
            role=asset.role,
            name=asset.name,
            sha256=hashlib.sha256(Path(asset.path).read_bytes()).hexdigest(),
            size_bytes=info.st_size,
            mtime_ns=str(info.st_mtime_ns),
            duration=asset.duration,
            width=asset.width,
            height=asset.height,
            fps=asset.fps,
            video_codec="h264",
            audio_codec="aac",
            has_audio=True,
            decoded_frames=12,
            decoded_seconds=12.345,
        )


class HoldingInspector(FixtureInspector):
    """Hold the worker so progress, busy protection and cancellation can be asserted."""

    def __init__(self) -> None:
        self.entered = threading.Event()

    def inspect(self, asset, cancel, progress):
        self.entered.set()
        progress(30)
        if cancel.wait(5):
            raise CommandCancelledError("Fixture cancelled")
        return super().inspect(asset, cancel, progress)


@pytest.fixture
def inspection_client(settings):
    binaries = settings.binaries_dir / "ffmpeg" / "bin"
    binaries.mkdir(parents=True)
    for name in ("ffmpeg", "ffprobe"):
        (binaries / name).touch()
    with TestClient(create_app(settings, prober=FakeProber(parse_probe(FFPROBE_VIDEO)))) as client:
        client.app.state.inspection.inspector = FixtureInspector()
        yield client


def inputs(client):
    project = client.post("/api/v1/projects", json={"name": "Inspection unit fixture"}).json()["id"]
    assets = []
    for role in ("reference", "source"):
        assets.append(
            client.post(
                f"/api/v1/projects/{project}/uploads",
                files={"file": (f"{role}.mp4", b"fixture-bytes")},
                data={"role": role},
            ).json()
        )
    url = f"/api/v1/projects/{project}/inspection"
    return (
        project,
        assets,
        url,
        {"reference_asset_id": assets[0]["id"], "source_asset_ids": [assets[1]["id"]]},
    )


def finished(client):
    thread = client.app.state.inspection.worker
    thread.join(timeout=3)
    assert not thread.is_alive()


def test_job_persists_report_and_never_produces_synthetic_dna(inspection_client):
    client = inspection_client
    project, assets, url, payload = inputs(client)
    response = client.post(url + "/jobs", json=payload)
    assert response.status_code == 202, response.text
    finished(client)
    result = client.get(url + "/latest").json()
    assert result["id"] == response.json()["id"]
    assert result["state"] == "done"
    assert result["percent"] == 100
    assert result["report"]["scope"] == "media-inspection-only"
    assert result["report"]["method"] == "ffprobe+ffmpeg-full-decode"
    assert result["stale"] is False
    assert [f["asset_id"] for f in result["report"]["files"]] == [a["id"] for a in assets]
    assert result["report"]["files"][0]["sha256"] == hashlib.sha256(b"fixture-bytes").hexdigest()
    assert "StyleDNA" in result["report"]["unavailable"]
    kinds = client.get(f"/api/v1/projects/{project}/stylematch/artifacts").json()
    assert [r["kind"] for r in kinds] == ["media-inspection"]
    assert client.get(url + f"/jobs/{result['id']}").json() == result


def test_capabilities_do_not_promise_inference_from_present_files(inspection_client, settings):
    project, _, url, _ = inputs(inspection_client)
    model_dir = settings.home_dir / "models"
    model_dir.mkdir()
    (model_dir / "pretend.onnx").write_bytes(b"not-a-verified-model")
    result = inspection_client.get(url + "/capabilities").json()
    assert result["inspection"]["available"] is True
    assert result["model_analysis"]["available"] is False
    assert "verified" in result["model_analysis"]["reason"].lower()
    assert "runtime downloads" in result["model_analysis"]["reason"]
    assert inspection_client.get("/api/v1/projects/nope/inspection/capabilities").status_code == 404
    assert project


def test_missing_bundled_tools_block_without_falling_back_to_path(inspection_client, settings):
    _, _, url, payload = inputs(inspection_client)
    (settings.binaries_dir / "ffmpeg" / "bin" / "ffmpeg").unlink()
    caps = inspection_client.get(url + "/capabilities").json()
    assert caps["inspection"]["available"] is False
    assert inspection_client.post(url + "/jobs", json=payload).status_code == 503
    assert inspection_client.get(url + "/latest").status_code == 404
    assert inspection_client.app.state.jobs.list() == []


@pytest.mark.parametrize(
    "mutation",
    ["duplicate", "ref-in-source", "foreign", "wrong-role", "extra-labels", "empty", "too-many"],
)
def test_invalid_or_fabricated_inputs_rejected(inspection_client, mutation):
    _, assets, url, payload = inputs(inspection_client)
    if mutation == "duplicate":
        payload["source_asset_ids"] *= 2
    elif mutation == "ref-in-source":
        payload["source_asset_ids"] = [payload["reference_asset_id"]]
    elif mutation == "foreign":
        payload["source_asset_ids"] = ["f" * 32]
    elif mutation == "wrong-role":
        payload = {"reference_asset_id": assets[1]["id"], "source_asset_ids": [assets[0]["id"]]}
    elif mutation == "extra-labels":
        payload["analysis"] = {"moments": [{"score": 1}]}
    elif mutation == "empty":
        payload["source_asset_ids"] = []
    elif mutation == "too-many":
        payload["source_asset_ids"] = ["a" * 32] * 101
    assert inspection_client.post(url + "/jobs", json=payload).status_code == 422
    assert inspection_client.app.state.jobs.list() == []


def test_missing_input_is_visible_without_a_phantom_job(inspection_client):
    _, assets, url, payload = inputs(inspection_client)
    Path(assets[1]["path"]).unlink()
    response = inspection_client.post(url + "/jobs", json=payload)
    assert response.status_code == 422
    assert "unavailable" in response.json()["detail"]
    assert inspection_client.app.state.jobs.list() == []


def test_running_job_progress_busy_guard_project_scope_and_real_cancellation(inspection_client):
    _, _, url, payload = inputs(inspection_client)
    hold = HoldingInspector()
    inspection_client.app.state.inspection.inspector = hold
    response = inspection_client.post(url + "/jobs", json=payload).json()
    assert hold.entered.wait(2)
    current = inspection_client.get(url + f"/jobs/{response['id']}").json()
    assert current["state"] == "running"
    assert 0 < current["percent"] < 100
    assert current["report"] is None
    assert inspection_client.post(url + "/jobs", json=payload).status_code == 409
    other, _, other_url, _ = inputs(inspection_client)
    assert other
    assert inspection_client.get(other_url + f"/jobs/{response['id']}").status_code == 404
    assert inspection_client.post(other_url + f"/jobs/{response['id']}/cancel").status_code == 404
    assert inspection_client.post(url + f"/jobs/{response['id']}/cancel").status_code == 200
    finished(inspection_client)
    terminal = inspection_client.get(url + "/latest").json()
    assert terminal["state"] == "cancelled"
    assert terminal["percent"] < 100
    assert terminal["report"] is None


def test_worker_failure_is_logged_and_retry_gets_a_new_job(inspection_client, caplog):
    _, _, url, payload = inputs(inspection_client)

    class BrokenInspector:
        def inspect(self, *_args: object):
            raise RuntimeError("Decoder failed")

    inspection_client.app.state.inspection.inspector = BrokenInspector()
    inspection_client.post(url + "/jobs", json=payload)
    finished(inspection_client)
    bad = inspection_client.get(url + "/latest").json()
    assert bad["state"] == "failed"
    assert bad["report"] is None
    assert "Decoder failed" in bad["error"]
    assert "inspection.failed" in caplog.text
    inspection_client.app.state.inspection.inspector = FixtureInspector()
    inspection_client.post(url + "/jobs", json=payload)
    finished(inspection_client)
    good = inspection_client.get(url + "/latest").json()
    assert good["state"] == "done"
    assert good["id"] != bad["id"]


def test_unsaved_result_never_reports_success(inspection_client, monkeypatch, caplog):
    _, _, url, payload = inputs(inspection_client)

    def fail(_result):
        raise RuntimeError("disk full")

    monkeypatch.setattr(inspection_client.app.state.inspection, "_persist", fail)
    inspection_client.post(url + "/jobs", json=payload)
    finished(inspection_client)
    result = inspection_client.get(url + "/latest").json()
    assert result["state"] == "failed"
    assert result["report"] is None
    assert result["percent"] < 100
    assert "Could not save" in result["error"]
    assert "inspection.persist.failed" in caplog.text


def test_completed_report_survives_backend_restart_and_detects_modified_inputs(
    inspection_client, settings
):
    _, assets, url, payload = inputs(inspection_client)
    inspection_client.post(url + "/jobs", json=payload)
    finished(inspection_client)
    saved = inspection_client.get(url + "/latest").json()
    with TestClient(create_app(settings)) as restarted:
        assert restarted.get(url + "/latest").json() == saved
        Path(assets[0]["path"]).write_bytes(b"changed")
        stale = restarted.get(url + "/latest").json()
        assert stale["stale"] is True
        assert stale["report"] == saved["report"]
        Path(assets[0]["path"]).unlink()
        assert restarted.get(url + "/latest").json()["stale"] is True


def test_orphaned_active_job_becomes_interrupted_not_done(inspection_client):
    project, _, url, payload = inputs(inspection_client)
    record = InspectionRead(
        id="orphaned", project_id=project, **payload, state="running", percent=35
    )
    with inspection_client.app.state.session_factory() as session:
        session.add(
            Artifact(
                id="orphaned",
                project_id=project,
                kind="media-inspection",
                payload_json=record.model_dump_json(),
            )
        )
        session.commit()
    restored = inspection_client.get(url + "/latest").json()
    assert restored["state"] == "interrupted"
    assert restored["percent"] == 35
    assert restored["report"] is None
    assert "restarted" in restored["error"]
    assert inspection_client.get(url + "/latest").json() == restored


def test_real_inspector_uses_ffprobe_and_full_decode_not_an_encoder(
    inspection_client, settings, monkeypatch
):
    _, assets, _, _ = inputs(inspection_client)
    from app.api.assets import _to_read
    from app.models import MediaAsset

    with inspection_client.app.state.session_factory() as session:
        asset = _to_read(session.get(MediaAsset, assets[0]["id"]))
    calls = []

    def command(args, **kwargs: object):
        calls.append(args)
        if "-show_streams" in args:
            return CommandResult(0, json.dumps(FFPROBE_VIDEO), "")
        kwargs["on_progress"](ProgressEvent(12.345, 1, 100, 30, done=True))
        return CommandResult(0, "", "")

    monkeypatch.setattr("app.services.media.inspection.run_command", command)
    measured = FFmpegInspector(settings).inspect(asset, threading.Event(), lambda _percent: None)
    assert len(calls) == 2
    assert measured.decoded_frames == 30
    assert measured.sha256 == hashlib.sha256(b"fixture-bytes").hexdigest()
    assert calls[1][-3:] == ["-f", "null", "-"]
    assert "-i" in calls[1]
    assert "-progress" in calls[1]
    assert "-xerror" in calls[1]
    assert not any("264" in arg for arg in calls[1])
    assert (
        decode_command(inspection_client.app.state.media_service.binaries(), Path(asset.path))
        == calls[1]
    )


def test_actual_foreign_project_asset_cannot_be_submitted(inspection_client):
    _, _, url, payload = inputs(inspection_client)
    _, other, _, _ = inputs(inspection_client)
    payload["source_asset_ids"] = [other[1]["id"]]
    assert inspection_client.post(url + "/jobs", json=payload).status_code == 422
    assert inspection_client.app.state.jobs.list() == []


def test_start_commit_failure_rolls_back_and_returns_an_actionable_error(
    inspection_client, monkeypatch, caplog
):
    from sqlalchemy.orm import Session

    _, _, url, payload = inputs(inspection_client)

    def fail(_session):
        raise RuntimeError("storage not writable")

    with monkeypatch.context() as patch:
        patch.setattr(Session, "commit", fail)
        response = inspection_client.post(url + "/jobs", json=payload)
    assert response.status_code == 503
    assert "storage not writable" in response.json()["detail"]
    assert "inspection.start.failed" in caplog.text
    assert inspection_client.get(url + "/latest").status_code == 404
    assert inspection_client.app.state.inspection.worker is None


def test_corrupt_success_record_is_preserved_and_never_rendered_as_done(inspection_client, caplog):
    project, _, url, payload = inputs(inspection_client)
    corrupt = json.dumps(
        dict(id="corrupt", project_id=project, **payload, state="done", percent=100)
    )
    with inspection_client.app.state.session_factory() as session:
        session.add(
            Artifact(
                id="corrupt", project_id=project, kind="media-inspection", payload_json=corrupt
            )
        )
        session.commit()
    assert inspection_client.get(url + "/latest").status_code == 503
    assert inspection_client.post(url + "/jobs/corrupt/cancel").status_code == 503
    assert "inspection.read.failed" in caplog.text
    assert "inspection.cancel.failed" in caplog.text
    with inspection_client.app.state.session_factory() as session:
        assert session.get(Artifact, "corrupt").payload_json == corrupt


@pytest.mark.parametrize("condition", ["modified", "zero-frames", "cancelled"])
def test_real_inspector_never_confirms_changed_empty_or_cancelled_video(
    inspection_client, settings, monkeypatch, condition
):
    from app.api.assets import _to_read
    from app.models import MediaAsset

    _, assets, _, _ = inputs(inspection_client)
    with inspection_client.app.state.session_factory() as session:
        asset = _to_read(session.get(MediaAsset, assets[0]["id"]))
    cancel = threading.Event()
    if condition == "cancelled":
        cancel.set()

    def command(args, **kwargs: object):
        if "-show_streams" in args:
            return CommandResult(0, json.dumps(FFPROBE_VIDEO), "")
        kwargs["on_progress"](
            ProgressEvent(12.345, 1, 100, 0 if condition == "zero-frames" else 30, done=True)
        )
        if condition == "modified":
            Path(asset.path).write_bytes(b"changed-during-decode")
        return CommandResult(0, "", "")

    monkeypatch.setattr("app.services.media.inspection.run_command", command)
    expected = CommandCancelledError if condition == "cancelled" else ValueError
    with pytest.raises(expected):
        FFmpegInspector(settings).inspect(asset, cancel, lambda _percent: None)


def test_finished_job_cannot_be_cancelled_or_have_its_report_overwritten(inspection_client):
    _, _, url, payload = inputs(inspection_client)
    inspection_client.post(url + "/jobs", json=payload)
    finished(inspection_client)
    before = inspection_client.get(url + "/latest").json()
    after = inspection_client.post(url + f"/jobs/{before['id']}/cancel").json()
    assert after == before
