"""FFmpeg resolution and command construction (no execution)."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.config import Settings
from app.services.media.ffmpeg import (
    H264_ENCODERS,
    FFmpegNotFoundError,
    available_h264_encoder,
    export_command,
    forbidden_encoders_present,
    parse_encoders,
    probe_command,
    proxy_command,
    resolve_binaries,
    thumbnail_command,
)
from tests.fixtures import ENCODER_LIST, fake_ffmpeg_tree


def _settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path / "data", home_dir=tmp_path / "install", log_to_file=False)


def test_resolves_bundled_binaries_first(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    fake_ffmpeg_tree(settings.binaries_dir)
    binaries = resolve_binaries(settings, allow_path_fallback=False)
    assert binaries.ffmpeg.name == "ffmpeg"
    assert binaries.ffprobe.name == "ffprobe"
    assert binaries.as_dict()["ffmpeg"].endswith("ffmpeg")


def test_missing_binaries_raise_actionable_error(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    with pytest.raises(FFmpegNotFoundError, match="LGPL shared build"):
        resolve_binaries(settings, allow_path_fallback=False)


def test_encoder_parsing_prefers_nvenc_and_flags_gpl() -> None:
    encoders = parse_encoders(ENCODER_LIST)
    assert {"h264_nvenc", "libopenh264", "libx264", "aac"} <= encoders
    assert available_h264_encoder(encoders) == "h264_nvenc"
    assert forbidden_encoders_present(encoders) == {"libx264", "libx265", "libx262"} - {
        "libx265",
        "libx262",
    }
    assert available_h264_encoder({"libiomp5"}) is None
    assert H264_ENCODERS == ("h264_nvenc", "libopenh264")


def test_probe_and_thumbnail_commands(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    fake_ffmpeg_tree(settings.binaries_dir)
    binaries = resolve_binaries(settings, allow_path_fallback=False)
    probe = probe_command(binaries, tmp_path / "a.mp4")
    assert probe[1:3] == ["-v", "error"]
    assert "-show_streams" in probe
    assert probe[-1].endswith("a.mp4")

    thumb = thumbnail_command(binaries, tmp_path / "a.mp4", tmp_path, count=10, width=320)
    assert "fps=10/1,scale=320:-1,tile=10x1" in " ".join(thumb)
    assert thumb[-1].endswith("a-strip.jpg")


def test_proxy_command_uses_faststart_and_rejects_gpl(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    fake_ffmpeg_tree(settings.binaries_dir)
    binaries = resolve_binaries(settings, allow_path_fallback=False)
    args = proxy_command(binaries, tmp_path / "a.mp4", tmp_path / "p.mp4", width=960, height=540)
    assert "+faststart" in args
    assert "scale=960:540:force_original_aspect_ratio=decrease,fps=30" in args
    with pytest.raises(ValueError, match="not allowed"):
        proxy_command(binaries, tmp_path / "a.mp4", tmp_path / "p.mp4", encoder="libx264")


def test_export_command_nvenc_profile_and_gpl_guard(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    fake_ffmpeg_tree(settings.binaries_dir)
    binaries = resolve_binaries(settings, allow_path_fallback=False)

    nvenc = export_command(
        binaries,
        tmp_path / "a.mp4",
        tmp_path / "o.mp4",
        encoder="h264_nvenc",
        width=1080,
        height=1920,
        fps=30,
        bitrate_kbps=12000,
    )
    assert nvenc[nvenc.index("-c:v") + 1] == "h264_nvenc"
    assert "p5" in nvenc
    assert "hq" in nvenc
    assert "high" in nvenc
    assert "yuv420p" in nvenc
    assert "pad=1080:1920" in " ".join(nvenc)

    openh264 = export_command(
        binaries,
        tmp_path / "a.mp4",
        tmp_path / "o2.mp4",
        encoder="libopenh264",
        width=1920,
        height=1080,
        fps=60,
        bitrate_kbps=8000,
    )
    assert "-maxrate" in openh264

    with pytest.raises(ValueError, match="not allowed"):
        export_command(
            binaries,
            tmp_path / "a.mp4",
            tmp_path / "o3.mp4",
            encoder="libx264",
            width=1920,
            height=1080,
            fps=30,
            bitrate_kbps=8000,
        )
