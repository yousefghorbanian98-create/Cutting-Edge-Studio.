"""R3 — EDL-to-render must use approved encoder and never fake output."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient

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
        },
        {
            "source": "/tmp/b.mp4",
            "in_point": 0.0,
            "out_point": 1.0,
            "timeline_start": 1.0,
            "duration": 1.0,
        },
    ],
}


def _settings(tmp: Path) -> Settings:
    return Settings(data_dir=tmp / "data", home_dir=tmp / "home", log_to_file=False)


def test_render_rejects_empty_edl() -> None:
    with tempfile.TemporaryDirectory() as td:
        s = _settings(Path(td))
        with TestClient(create_app(s)) as c:
            pid = c.post("/api/v1/projects", json={"name": "R3"}).json()["id"]
            r = c.post(f"/api/v1/projects/{pid}/render/jobs", json={"edl": {"segments": []}})
            assert r.status_code == 422


def test_render_requires_encoder_and_returns_503_when_missing() -> None:
    with tempfile.TemporaryDirectory() as td:
        s = _settings(Path(td))
        with TestClient(create_app(s)) as c:
            pid = c.post("/api/v1/projects", json={"name": "R3"}).json()["id"]
            caps = c.get(f"/api/v1/projects/{pid}/render/capabilities").json()
            assert caps["render"]["available"] is False
            assert (
                "ffmpeg" in caps["render"]["reason"].lower()
                or "encoder" in caps["render"]["reason"].lower()
            )
            r = c.post(f"/api/v1/projects/{pid}/render/jobs", json={"edl": MIN_EDL})
            assert r.status_code == 503


def test_render_encoder_probe_exposes_gpl_safety(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        s = _settings(Path(td))
        bin_dir = s.binaries_dir / "ffmpeg" / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        (bin_dir / "ffmpeg").write_text("#!/bin/sh\necho encoders:; exit 0\n")
        (bin_dir / "ffmpeg").chmod(0o755)
        (bin_dir / "ffprobe").write_text("#!/bin/sh\necho probe; exit 0\n")
        (bin_dir / "ffprobe").chmod(0o755)

        import app.services.media.ffmpeg as ff
        import app.services.render.orchestrator as orch

        def fake_probe(binaries, timeout=30):
            return {"libx264", "libx265", "h264_nvenc"}

        monkeypatch.setattr(orch, "_probe_encoder", fake_probe)

        from app.services.render.orchestrator import pick_encoder

        chosen = pick_encoder(s)
        assert chosen == "h264_nvenc"
        assert "libx264" in ff.FORBIDDEN_ENCODERS


def test_render_job_never_uses_forbidden_encoder() -> None:
    from app.services.media.ffmpeg import FFmpegBinaries
    from app.services.stylematch.render import build_edl_command

    bins = FFmpegBinaries(ffmpeg=Path("/tmp/ffmpeg"), ffprobe=Path("/tmp/ffprobe"))
    edl = MIN_EDL | {"width": 1080, "height": 1920}
    with pytest.raises(ValueError, match="not allowed"):
        build_edl_command(bins, edl, Path("/tmp/out.mp4"), encoder="libx264")
