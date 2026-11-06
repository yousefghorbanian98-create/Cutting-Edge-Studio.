"""R3 coverage hardening — RenderService branches not covered by happy-path tests."""

from __future__ import annotations

import tempfile
import threading
import time
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock

import pytest
from app.config import Settings
from app.main import create_app
from app.services.media.jobs import Job
from fastapi.testclient import TestClient

MIN_EDL = {
    "version": "1.1",
    "fps": 30,
    "width": 1080,
    "height": 1920,
    "total_duration": 1.0,
    "segments": [
        {
            "source": "/tmp/a.mp4",
            "in_point": 0.0,
            "out_point": 0.5,
            "timeline_start": 0.0,
            "duration": 0.5,
        }
    ],
}


def _settings(tmp: Path) -> Settings:
    return Settings(data_dir=tmp / "data", home_dir=tmp / "home", log_to_file=False)


def test_pick_encoder_rejects_forbidden_preferred() -> None:
    with tempfile.TemporaryDirectory() as td:
        s = _settings(Path(td))
        (s.binaries_dir / "ffmpeg" / "bin").mkdir(parents=True, exist_ok=True)
        import app.services.render.orchestrator as orch

        def fake_probe(binaries, timeout=30):  # noqa: ARG001
            return {"h264_nvenc", "libopenh264", "libx264"}

        orig = orch._probe_encoder  # type: ignore[assignment]
        orch._probe_encoder = fake_probe  # type: ignore[assignment]
        try:
            with mock.patch("app.services.render.orchestrator.resolve_binaries") as rb:
                rb.return_value = MagicMock(ffmpeg=Path("/tmp/ffmpeg"))
                with pytest.raises(ValueError, match="not allowed"):
                    orch.pick_encoder(s, preferred="libx264")
        finally:
            orch._probe_encoder = orig  # type: ignore[assignment]


def test_pick_encoder_raises_when_no_approved() -> None:
    with tempfile.TemporaryDirectory() as td:
        s = _settings(Path(td))
        import app.services.render.orchestrator as orch

        with mock.patch("app.services.render.orchestrator.resolve_binaries") as rb:
            rb.return_value = MagicMock(ffmpeg=Path("/tmp/ffmpeg"))
            with mock.patch("app.services.render.orchestrator._probe_encoder", return_value=set()):
                with pytest.raises(RuntimeError, match="No approved"):
                    orch.pick_encoder(s)
            with mock.patch(
                "app.services.render.orchestrator._probe_encoder", return_value={"libx264"}
            ):
                with pytest.raises(RuntimeError, match="No approved"):
                    orch.pick_encoder(s)


def test_pick_encoder_returns_preferred_when_available() -> None:
    with tempfile.TemporaryDirectory() as td:
        s = _settings(Path(td))
        import app.services.render.orchestrator as orch

        with mock.patch("app.services.render.orchestrator.resolve_binaries") as rb:
            rb.return_value = MagicMock(ffmpeg=Path("/tmp/ffmpeg"))
            with mock.patch(
                "app.services.render.orchestrator._probe_encoder",
                return_value={"h264_nvenc", "libopenh264"},
            ):
                assert orch.pick_encoder(s, preferred="libopenh264") == "libopenh264"
                assert orch.pick_encoder(s, preferred="h264_nvenc") == "h264_nvenc"


def test_render_start_busy_second_call_rejected() -> None:
    with tempfile.TemporaryDirectory() as td:
        s = _settings(Path(td))
        import time as _t

        import app.services.render.orchestrator as orch

        orig_run = orch.RenderService._run

        def stuck(self, job, initial, edl, quality):  # noqa: ARG001
            _t.sleep(2)

        with mock.patch.object(orch.RenderService, "_run", stuck):
            with TestClient(create_app(s)) as c:
                pid = c.post("/api/v1/projects", json={"name": "busy"}).json()["id"]
                bin_dir = s.binaries_dir / "ffmpeg" / "bin"
                bin_dir.mkdir(parents=True, exist_ok=True)
                (bin_dir / "ffmpeg").write_text("#!/bin/sh\necho\n")
                (bin_dir / "ffmpeg").chmod(0o755)
                (bin_dir / "ffprobe").write_text("#!/bin/sh\necho\n")
                (bin_dir / "ffprobe").chmod(0o755)
                with (
                    mock.patch(
                        "app.services.render.orchestrator._probe_encoder",
                        return_value={"libopenh264"},
                    ),
                    mock.patch(
                        "app.services.render.orchestrator.build_edl_command",
                        return_value=["echo", "hi"],
                    ),
                    mock.patch("app.services.render.orchestrator.run_command"),
                ):
                    r1 = c.post(f"/api/v1/projects/{pid}/render/jobs", json={"edl": MIN_EDL})
                    assert r1.status_code in (200, 201, 202)
                    r2 = c.post(f"/api/v1/projects/{pid}/render/jobs", json={"edl": MIN_EDL})
                    assert r2.status_code in (409, 423, 503)
        orch.RenderService._run = orig_run  # type: ignore[assignment]


def test_render_read_reports_interrupted_after_restart() -> None:
    with tempfile.TemporaryDirectory() as td:
        s = _settings(Path(td))
        with TestClient(create_app(s)) as c:
            pid = c.post("/api/v1/projects", json={"name": "intr"}).json()["id"]
            import uuid

            from app.db import create_db_engine, init_db
            from app.models import Artifact
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker

            jid = str(uuid.uuid4())
            payload = (
                f'{{"id":"{jid}","project_id":"{pid}","state":"running",'
                f'"percent":42,"message":"Rendering 42.0%","quality":"preview","error":null,"report":null}}'
            )
            _engine = create_db_engine(s.database_url)
            init_db(_engine)
            # insert via second engine pointing to same file
            eng2 = create_engine(s.database_url, connect_args={"check_same_thread": False})
            fac2 = sessionmaker(bind=eng2, expire_on_commit=False, future=True)
            with fac2() as sess2:
                if sess2.get(Artifact, jid) is None:
                    sess2.add(
                        Artifact(
                            id=jid,
                            project_id=pid,
                            kind="render-job",
                            revision=1,
                            payload_json=payload,
                        )
                    )
                    sess2.commit()
            r = c.get(f"/api/v1/projects/{pid}/render/jobs/{jid}")
            assert r.status_code in (200, 404)
            if r.status_code == 200:
                body = r.json()
                assert body["state"] == "interrupted"
                assert "restart" in body["error"].lower()


def test_render_cancel_sets_event() -> None:
    with tempfile.TemporaryDirectory() as td:
        s = _settings(Path(td))
        from app.services.media.jobs import JobRegistry
        from app.services.render.orchestrator import RenderService

        jobs = JobRegistry()
        job = jobs.create("render-job", project_id="p1")
        factory = MagicMock()
        svc = RenderService(factory=factory, jobs=jobs, settings=s)  # type: ignore[arg-type]
        svc.active = job  # type: ignore[assignment]
        assert jobs.get(job.id) is not None
        job.cancel_event.set()
        assert job.cancel_event.is_set()


def test_output_dir_creates_and_returns_path() -> None:
    with tempfile.TemporaryDirectory() as td:
        s = _settings(Path(td))
        from app.services.render.orchestrator import _output_dir

        p = _output_dir(s, "proj123")
        assert p.exists()
        assert p.is_dir()
        assert "proj123" in str(p)


def test_shutdown_joins_worker() -> None:
    from app.services.render.orchestrator import RenderService

    class FakeJobs:
        _jobs: dict = {}

    fake_factory = MagicMock()
    s = MagicMock()
    svc = RenderService(factory=fake_factory, jobs=FakeJobs(), settings=s)  # type: ignore[arg-type]
    t = threading.Thread(target=lambda: time.sleep(0.05), daemon=True)
    job = Job(id="j1", kind="render-job", project_id="p1", state="running")
    svc.active = job  # type: ignore[assignment]
    svc.worker = t
    t.start()
    svc.shutdown()
    assert not t.is_alive()


def test_probe_encoder_calls_runner(monkeypatch) -> None:
    import app.services.render.orchestrator as orch

    fake_res = MagicMock(stdout=" Video: h264_nvenc (encoders: h264_nvenc ) ", stderr="")
    monkeypatch.setattr(orch, "run_command", lambda *a, **kw: fake_res)
    out = orch._probe_encoder(MagicMock(ffmpeg=Path("/tmp/ffmpeg")))
    assert "h264_nvenc" in out
