"""MediaService decisions: proxy need, plans, encoder detection."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.config import Settings
from app.services.media.probe import MediaInfo
from app.services.media.service import MediaService, needs_proxy


def _info(**overrides: object) -> MediaInfo:
    base = {
        "duration": 10.0,
        "width": 1920,
        "height": 1080,
        "fps": 30.0,
        "video_codec": "h264",
        "audio_codec": "aac",
        "bit_rate": 8_000_000,
        "has_audio": True,
    }
    base.update(overrides)
    return MediaInfo(**base)  # type: ignore[arg-type]


def test_needs_proxy_rules() -> None:
    assert needs_proxy(_info()) is False
    assert needs_proxy(_info(width=3840, height=2160)) is True
    assert needs_proxy(_info(bit_rate=60_000_000)) is True


def test_probe_wraps_missing_file(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path / "d", home_dir=tmp_path / "h", log_to_file=False)
    service = MediaService(settings, prober=None)
    with pytest.raises(FileNotFoundError, match="file not found"):
        service.probe(tmp_path / "missing.mp4")


def test_proxy_and_thumbnail_plans(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path / "d", home_dir=tmp_path / "h", log_to_file=False)
    from tests.fixtures import fake_ffmpeg_tree

    fake_ffmpeg_tree(settings.binaries_dir)
    service = MediaService(settings)
    source = tmp_path / "a.mp4"
    source.write_bytes(b"x")

    plan = service.proxy_plan(source, _info(), tmp_path)
    assert plan[0].endswith("ffmpeg")
    assert any("scale=" in part for part in plan)

    thumbs = service.thumbnail_plan(source, tmp_path, count=8)
    assert any("tile=8x1" in part for part in thumbs)


def test_encoder_detection_without_ffmpeg_returns_none(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path / "d", home_dir=tmp_path / "h", log_to_file=False)
    service = MediaService(settings)
    assert service.detect_h264_encoder() is None
