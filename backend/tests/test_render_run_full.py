"""R3 full _run coverage — mock FFmpeg to hit remaining 172-248 branches."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock

import pytest
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


def _make_service(tmp: Path, jobs: JobRegistry | None = None):
    s = _settings(tmp)
    s.ensure_dirs()
    engine = __import__("app.db", fromlist=["create_db_engine"]).create_db_engine(s.database_url)
    __import__("app.db", fromlist=["init_db"]).init_db(engine)
    factory = __import__("app.db", fromlist=["create_session_factory"]).create_session_factory(
        engine
    )
    reg = jobs or JobRegistry()
    svc = RenderService(factory=factory, jobs=reg, settings=s)
    # ensure base project exists for FK
    from app.models import Project as _Proj

    with factory() as _sess:
        if _sess.get(_Proj, "p1") is None:
            _sess.add(_Proj(id="p1", name="test"))
            _sess.commit()
    return s, factory, reg, svc, engine


def _ensure_project(factory, project_id: str = "p1") -> None:
    from app.models import Project as Proj

    with factory() as sess:
        if sess.get(Proj, project_id) is None:
            sess.add(Proj(id=project_id, name="test"))
            sess.commit()


def test_run_success_preview_forces_libopenh264():
    with tempfile.TemporaryDirectory() as td:
        s, factory, reg, svc, _ = _make_service(Path(td))
        from app.models import Artifact

        job = reg.create("render-job", project_id="p1")
        init = __import__("app.schemas_render", fromlist=["RenderRead"]).RenderRead(
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
        # output file must exist for success
        out_path = s.projects_dir / "p1" / "renders" / f"{job.id}.mp4"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"fake mp4 content")

        fake_probe = MagicMock(duration=1.5)
        with (
            mock.patch("app.services.render.orchestrator.pick_encoder", return_value="h264_nvenc"),
            mock.patch(
                "app.services.render.orchestrator.resolve_binaries",
                return_value=MagicMock(ffmpeg=Path("/tmp/ffmpeg"), ffprobe=Path("/tmp/ffprobe")),
            ),
            mock.patch(
                "app.services.render.orchestrator._probe_encoder",
                return_value={"libopenh264", "h264_nvenc"},
            ),
            mock.patch(
                "app.services.render.orchestrator.build_edl_command", return_value=["echo", "hi"]
            ) as bcmd,
            mock.patch("app.services.render.orchestrator.run_command") as rc,
            mock.patch("app.services.render.orchestrator.probe_command", return_value=["echo"]),
            mock.patch("app.services.render.orchestrator.parse_probe", return_value=fake_probe),
        ):
            # first call is EDL render, second is probe
            rc.side_effect = [
                MagicMock(stdout="", stderr=""),
                MagicMock(stdout="probe", stderr=""),
            ]
            svc._run(job, init, MIN_EDL, "preview")
            # forced libopenh264 for preview
            assert bcmd.call_args is not None
            assert bcmd.call_args[1]["encoder"] == "libopenh264"
            assert bcmd.call_args[1]["bitrate_kbps"] == 1200
            assert reg.get(job.id).state == "done"


def test_run_success_final_6000():
    with tempfile.TemporaryDirectory() as td:
        s, factory, reg, svc, _ = _make_service(Path(td))
        from app.models import Artifact

        job = reg.create("render-job", project_id="p1")
        init = __import__("app.schemas_render", fromlist=["RenderRead"]).RenderRead(
            id=job.id, project_id="p1", state="queued", percent=0, message="q", quality="final"
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
        out_path = s.projects_dir / "p1" / "renders" / f"{job.id}.mp4"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"fake")
        fake_probe = MagicMock(duration=2.0)
        with (
            mock.patch("app.services.render.orchestrator.pick_encoder", return_value="h264_nvenc"),
            mock.patch(
                "app.services.render.orchestrator.resolve_binaries",
                return_value=MagicMock(ffmpeg=Path("/tmp/ffmpeg")),
            ),
            mock.patch(
                "app.services.render.orchestrator.build_edl_command", return_value=["echo"]
            ) as bcmd,
            mock.patch("app.services.render.orchestrator.run_command") as rc,
            mock.patch("app.services.render.orchestrator.probe_command", return_value=["echo"]),
            mock.patch("app.services.render.orchestrator.parse_probe", return_value=fake_probe),
        ):
            rc.side_effect = [MagicMock(stdout="", stderr=""), MagicMock(stdout="p", stderr="")]
            svc._run(job, init, MIN_EDL, "final")
            assert bcmd.call_args[1]["bitrate_kbps"] == 6000
            assert reg.get(job.id).state == "done"


def test_run_empty_edl_failed_and_cleanup():
    with tempfile.TemporaryDirectory() as td:
        s, factory, reg, svc, _ = _make_service(Path(td))
        from app.models import Artifact

        job = reg.create("render-job", project_id="p1")
        init = __import__("app.schemas_render", fromlist=["RenderRead"]).RenderRead(
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
        svc._run(job, init, {"segments": []}, "preview")
        assert reg.get(job.id).state == "failed"
        assert "empty EDL" in reg.get(job.id).error


def test_run_cancelled_before_start():
    with tempfile.TemporaryDirectory() as td:
        s, factory, reg, svc, _ = _make_service(Path(td))
        from app.models import Artifact

        job = reg.create("render-job", project_id="p1")
        job.cancel_event.set()
        init = __import__("app.schemas_render", fromlist=["RenderRead"]).RenderRead(
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
        with (
            mock.patch("app.services.render.orchestrator.pick_encoder", return_value="libopenh264"),
            mock.patch(
                "app.services.render.orchestrator.resolve_binaries",
                return_value=MagicMock(ffmpeg=Path("/tmp/ffmpeg")),
            ),
            mock.patch(
                "app.services.render.orchestrator._probe_encoder", return_value={"libopenh264"}
            ),
            mock.patch("app.services.render.orchestrator.build_edl_command", return_value=["echo"]),
        ):
            svc._run(job, init, MIN_EDL, "preview")
            assert reg.get(job.id).state == "cancelled"


def test_run_output_missing():
    with tempfile.TemporaryDirectory() as td:
        s, factory, reg, svc, _ = _make_service(Path(td))
        from app.models import Artifact

        job = reg.create("render-job", project_id="p1")
        init = __import__("app.schemas_render", fromlist=["RenderRead"]).RenderRead(
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
        # no output file created
        with (
            mock.patch("app.services.render.orchestrator.pick_encoder", return_value="libopenh264"),
            mock.patch(
                "app.services.render.orchestrator.resolve_binaries",
                return_value=MagicMock(ffmpeg=Path("/tmp/ffmpeg")),
            ),
            mock.patch(
                "app.services.render.orchestrator._probe_encoder", return_value={"libopenh264"}
            ),
            mock.patch("app.services.render.orchestrator.build_edl_command", return_value=["echo"]),
            mock.patch("app.services.render.orchestrator.run_command", return_value=MagicMock()),
        ):
            svc._run(job, init, MIN_EDL, "preview")
            assert reg.get(job.id).state == "failed"
            assert "missing or empty" in reg.get(job.id).error


def test_run_no_duration():
    with tempfile.TemporaryDirectory() as td:
        s, factory, reg, svc, _ = _make_service(Path(td))
        from app.models import Artifact

        job = reg.create("render-job", project_id="p1")
        init = __import__("app.schemas_render", fromlist=["RenderRead"]).RenderRead(
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
        out_path = s.projects_dir / "p1" / "renders" / f"{job.id}.mp4"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"x")
        with (
            mock.patch("app.services.render.orchestrator.pick_encoder", return_value="libopenh264"),
            mock.patch(
                "app.services.render.orchestrator.resolve_binaries",
                return_value=MagicMock(ffmpeg=Path("/tmp/ffmpeg")),
            ),
            mock.patch(
                "app.services.render.orchestrator._probe_encoder", return_value={"libopenh264"}
            ),
            mock.patch("app.services.render.orchestrator.build_edl_command", return_value=["echo"]),
            mock.patch("app.services.render.orchestrator.run_command") as rc,
            mock.patch("app.services.render.orchestrator.probe_command", return_value=["echo"]),
            mock.patch(
                "app.services.render.orchestrator.parse_probe", return_value=MagicMock(duration=0)
            ),
        ):
            rc.side_effect = [MagicMock(stdout="", stderr=""), MagicMock(stdout="probe", stderr="")]
            svc._run(job, init, MIN_EDL, "preview")
            assert reg.get(job.id).state == "failed"
            assert "no duration" in reg.get(job.id).error.lower()


def test_read_live_merges_and_identity_mismatch():
    with tempfile.TemporaryDirectory() as td:
        s, factory, reg, svc, _ = _make_service(Path(td))
        from app.models import Artifact

        job = reg.create("render-job", project_id="p1")
        init = __import__("app.schemas_render", fromlist=["RenderRead"]).RenderRead(
            id=job.id,
            project_id="p1",
            state="running",
            percent=10,
            message="live",
            quality="preview",
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
            # live should merge
            reg.update(job.id, state="running", percent=55, message="Rendering 55%")
            rec = svc.read(sess, "p1", job.id)
            assert rec.percent == 55
            # identity mismatch
            bad = init.model_copy(update={"id": "other"})
            # rewrite payload with mismatched id
            row = sess.get(Artifact, job.id)
            row.payload_json = bad.model_dump_json()
            sess.commit()
            with pytest.raises(ValueError, match="identity does not match"):
                svc.read(sess, "p1", job.id)
            # no row
            with pytest.raises(FileNotFoundError):
                svc.read(sess, "p1", "nope")


def test_cancel_sets_event_when_active():
    with tempfile.TemporaryDirectory() as td:
        s, factory, reg, svc, _ = _make_service(Path(td))
        from app.models import Artifact

        job = reg.create("render-job", project_id="p1")
        init = __import__("app.schemas_render", fromlist=["RenderRead"]).RenderRead(
            id=job.id, project_id="p1", state="running", percent=5, message="x", quality="preview"
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
            assert job.cancel_event.is_set()


def test_persist_missing_raises():
    with tempfile.TemporaryDirectory() as td:
        s, factory, reg, svc, _ = _make_service(Path(td))
        init = __import__("app.schemas_render", fromlist=["RenderRead"]).RenderRead(
            id="missing",
            project_id="p1",
            state="done",
            percent=100,
            message="done",
            quality="preview",
        )
        with pytest.raises(FileNotFoundError):
            svc._persist(init)


def test_finish_persist_failed_marks_failed():
    with tempfile.TemporaryDirectory() as td:
        s, factory, reg, svc, _ = _make_service(Path(td))
        from app.schemas_render import RenderRead

        job = reg.create("render-job", project_id="p1")
        init = RenderRead(
            id=job.id, project_id="p1", state="queued", percent=0, message="q", quality="preview"
        )
        # make _persist raise
        with mock.patch.object(svc, "_persist", side_effect=RuntimeError("db down")):
            svc._finish(job, init, "done", report=None)  # type: ignore[arg-type]
            assert reg.get(job.id).state == "failed"
            assert "Could not save" in reg.get(job.id).error
