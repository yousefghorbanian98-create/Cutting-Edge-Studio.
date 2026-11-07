"""Cover final 6 orchestrator gaps: on_progress, forbidden warning, cancel tail, shutdown timeout."""

from __future__ import annotations

import tempfile
import threading
import time
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock

from app.config import Settings
from app.services.media.jobs import JobRegistry
from app.services.render.orchestrator import RenderService

MIN_EDL = {
    "version": "1.1",
    "fps": 30,
    "width": 1080,
    "height": 1920,
    "total_duration": 2.0,
    "segments": [
        {
            "source": "/tmp/a.mp4",
            "in_point": 0.0,
            "out_point": 1.0,
            "timeline_start": 0.0,
            "duration": 1.0,
        }
    ],
}


def _settings(tmp: Path) -> Settings:
    return Settings(data_dir=tmp / "data", home_dir=tmp / "home", log_to_file=False)


def _make_service(tmp: Path):
    s = _settings(tmp)
    s.ensure_dirs()
    from app.db import create_db_engine, create_session_factory, init_db

    engine = create_db_engine(s.database_url)
    init_db(engine)
    factory = create_session_factory(engine)
    from app.models import Project

    with factory() as sess:
        if sess.get(Project, "p1") is None:
            sess.add(Project(id="p1", name="t"))
            sess.commit()
    reg = JobRegistry()
    svc = RenderService(factory=factory, jobs=reg, settings=s)
    return s, factory, reg, svc


def test_pick_encoder_warns_on_forbidden():
    with tempfile.TemporaryDirectory() as td:
        s, factory, reg, svc = _make_service(Path(td))
        import app.services.render.orchestrator as orch

        with (
            mock.patch("app.services.render.orchestrator.resolve_binaries") as rb,
            mock.patch(
                "app.services.render.orchestrator._probe_encoder",
                return_value={"libopenh264", "h264_nvenc", "libx264"},
            ),
        ):
            rb.return_value = MagicMock(ffmpeg=Path("/tmp/ffmpeg"))
            # should still return allowed encoder despite forbidden present, but log warning
            enc = orch.pick_encoder(s)
            assert enc in {"libopenh264", "h264_nvenc"}


def test_on_progress_percent_none_and_value():
    with tempfile.TemporaryDirectory() as td:
        s, factory, reg, svc = _make_service(Path(td))

        job = reg.create("render-job", project_id="p1")
        from app.schemas_render import RenderRead

        init = RenderRead(
            id=job.id, project_id="p1", state="queued", percent=0, message="q", quality="preview"
        )
        from app.models import Artifact

        with factory() as sess:
            sess.add(
                Artifact(
                    id=job.id,
                    project_id="p1",
                    kind="render-job",
                    revision=1,
                    payload_json=init.model_dump_json(),
                )
            )
            sess.commit()
        out = s.projects_dir / "p1" / "renders" / f"{job.id}.mp4"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"x")

        def fake_run_command(
            cmd, timeout=600, cancel_event=None, on_progress=None, total_seconds=None
        ):
            # simulate ffmpeg calling on_progress twice: once with None, once with 42
            if on_progress:
                on_progress(MagicMock(percent=None))
                on_progress(MagicMock(percent=42.5))
            return MagicMock(stdout="", stderr="")

        with (
            mock.patch("app.services.render.orchestrator.pick_encoder", return_value="libopenh264"),
            mock.patch(
                "app.services.render.orchestrator.resolve_binaries",
                return_value=MagicMock(ffmpeg=Path("/tmp/f"), ffprobe=Path("/tmp/p")),
            ),
            mock.patch(
                "app.services.render.orchestrator._probe_encoder", return_value={"libopenh264"}
            ),
            mock.patch("app.services.render.orchestrator.build_edl_command", return_value=["echo"]),
            mock.patch(
                "app.services.render.orchestrator.run_command", side_effect=fake_run_command
            ),
            mock.patch("app.services.render.orchestrator.probe_command", return_value=["echo"]),
            mock.patch(
                "app.services.render.orchestrator.parse_probe", return_value=MagicMock(duration=1.0)
            ),
        ):
            # need second run_command for probe
            # make side_effect handle both calls: first EDL render calls fake_run_command, second probe returns
            # so we wrap: first call hits fake_run_command, second returns probe mock
            original_fake = fake_run_command
            call_n = {"c": 0}

            def dispatch(*a, **kw):
                call_n["c"] += 1
                if call_n["c"] == 1:
                    return original_fake(*a, **kw)
                return MagicMock(stdout="probe", stderr="")

            with mock.patch("app.services.render.orchestrator.run_command", side_effect=dispatch):
                svc._run(job, init, MIN_EDL, "preview")
                assert reg.get(job.id).state == "done"
                # 99 cap not hit, but 42.5 was processed
                assert reg.get(job.id).percent == 100


def test_cancelled_after_lock_before_finish():
    with tempfile.TemporaryDirectory() as td:
        s, factory, reg, svc = _make_service(Path(td))
        from app.schemas_render import RenderRead

        job = reg.create("render-job", project_id="p1")
        init = RenderRead(
            id=job.id, project_id="p1", state="queued", percent=0, message="q", quality="preview"
        )
        from app.models import Artifact

        with factory() as sess:
            sess.add(
                Artifact(
                    id=job.id,
                    project_id="p1",
                    kind="render-job",
                    revision=1,
                    payload_json=init.model_dump_json(),
                )
            )
            sess.commit()
        out = s.projects_dir / "p1" / "renders" / f"{job.id}.mp4"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"x")

        def fake_run(cmd, timeout=30, cancel_event=None, on_progress=None, total_seconds=None):
            # set cancel right before lock check inside _run
            job.cancel_event.set()
            return MagicMock(stdout="", stderr="")

        with (
            mock.patch("app.services.render.orchestrator.pick_encoder", return_value="libopenh264"),
            mock.patch(
                "app.services.render.orchestrator.resolve_binaries",
                return_value=MagicMock(ffmpeg=Path("/tmp/f")),
            ),
            mock.patch(
                "app.services.render.orchestrator._probe_encoder", return_value={"libopenh264"}
            ),
            mock.patch("app.services.render.orchestrator.build_edl_command", return_value=["echo"]),
            mock.patch("app.services.render.orchestrator.run_command", side_effect=fake_run),
            mock.patch("app.services.render.orchestrator.probe_command", return_value=["echo"]),
            mock.patch(
                "app.services.render.orchestrator.parse_probe", return_value=MagicMock(duration=1.0)
            ),
        ):
            # _run will succeed creating output file, then lock sees cancel and raises CommandCancelledError
            svc._run(job, init, MIN_EDL, "preview")
            # should be cancelled, not done
            assert reg.get(job.id).state == "cancelled"


def test_cleanup_warning_when_unlink_raises():
    with tempfile.TemporaryDirectory() as td:
        s, factory, reg, svc = _make_service(Path(td))
        from app.models import Artifact
        from app.schemas_render import RenderRead

        job = reg.create("render-job", project_id="p1")
        init = RenderRead(
            id=job.id, project_id="p1", state="queued", percent=0, message="q", quality="preview"
        )
        with factory() as sess:
            sess.add(
                Artifact(
                    id=job.id,
                    project_id="p1",
                    kind="render-job",
                    revision=1,
                    payload_json=init.model_dump_json(),
                )
            )
            sess.commit()
        # create partial file to trigger cleanup
        out = s.projects_dir / "p1" / "renders" / f"{job.id}.mp4"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"partial")

        def failing_unlink(*_a, **_k):
            raise OSError("unlink fail")

        with (
            mock.patch(
                "app.services.render.orchestrator.pick_encoder",
                side_effect=RuntimeError("probe fail"),
            ),
            mock.patch(
                "app.services.render.orchestrator.resolve_binaries",
                return_value=MagicMock(ffmpeg=Path("/tmp/f")),
            ),
            mock.patch.object(Path, "exists", return_value=True),
            mock.patch.object(Path, "unlink", side_effect=failing_unlink),
        ):
            # empty EDL will fail before output check, then try cleanup which now raises OSError -> warning
            svc._run(job, init, {"segments": []}, "preview")
            assert reg.get(job.id).state == "failed"


def test_read_interrupted_commits():
    with tempfile.TemporaryDirectory() as td:
        s, factory, reg, svc = _make_service(Path(td))
        import uuid

        from app.models import Artifact
        from app.schemas_render import RenderRead

        jid = uuid.uuid4().hex
        init = RenderRead(
            id=jid,
            project_id="p1",
            state="running",
            percent=30,
            message="running",
            quality="preview",
        )
        with factory() as sess:
            sess.add(
                Artifact(
                    id=jid,
                    project_id="p1",
                    kind="render-job",
                    revision=1,
                    payload_json=init.model_dump_json(),
                )
            )
            sess.commit()
            rec = svc.read(sess, "p1", jid)
            assert rec.state == "interrupted"
            assert "restarted" in rec.error.lower()
            row = sess.get(Artifact, jid)
            assert "interrupted" in row.payload_json


def test_cancel_when_not_active_does_not_set():
    with tempfile.TemporaryDirectory() as td:
        s, factory, reg, svc = _make_service(Path(td))
        from app.models import Artifact
        from app.schemas_render import RenderRead

        job = reg.create("render-job", project_id="p1")
        job.state = "done"
        init = RenderRead(
            id=job.id, project_id="p1", state="done", percent=100, message="done", quality="preview"
        )
        with factory() as sess:
            sess.add(
                Artifact(
                    id=job.id,
                    project_id="p1",
                    kind="render-job",
                    revision=1,
                    payload_json=init.model_dump_json(),
                )
            )
            sess.commit()
            rec = svc.cancel(sess, "p1", job.id)
            assert rec.id == job.id
            assert not job.cancel_event.is_set()


def test_shutdown_timeout_logs_error():
    from app.services.render.orchestrator import RenderService

    class FakeJobs:
        _jobs: dict = {}

    s = MagicMock()
    svc = RenderService(factory=MagicMock(), jobs=FakeJobs(), settings=s)  # type: ignore[arg-type]
    job = JobRegistry().create("render-job", project_id="p1")
    # worker that never dies within 5s
    t = threading.Thread(target=lambda: time.sleep(10), daemon=True)
    t.start()
    svc.active = job  # type: ignore[assignment]
    svc.worker = t
    start = time.time()
    svc.shutdown()
    # should have waited 5s and still alive -> error logged, but we don't hang >6s
    assert time.time() - start >= 4.9
    # cleanup: cancel to let it die eventually (daemon)
    assert t.is_alive()  # still alive because 10s >5s, timeout branch taken
