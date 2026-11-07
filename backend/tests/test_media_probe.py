"""ffprobe JSON parsing."""

from __future__ import annotations

import json

import pytest
from app.services.media.probe import parse_probe
from tests.fixtures import FFPROBE_ROTATED, FFPROBE_VIDEO


def test_parses_video_and_audio_streams() -> None:
    info = parse_probe(FFPROBE_VIDEO)
    assert info.duration == pytest.approx(12.345)
    assert (info.width, info.height) == (1920, 1080)
    assert info.fps == pytest.approx(29.97, rel=1e-3)
    assert info.video_codec == "h264"
    assert info.audio_codec == "aac"
    assert info.has_audio is True
    assert info.bit_rate == 8_000_000
    assert info.pixels == 1920 * 1080
    assert info.is_portrait is False


def test_accepts_json_string_and_detects_portrait_rotation() -> None:
    info = parse_probe(json.dumps(FFPROBE_ROTATED))
    assert info.rotation == 90
    assert info.is_portrait is True
    assert info.has_audio is False
    assert info.fps == pytest.approx(60.0)


def test_audio_only_file() -> None:
    payload = {
        "streams": [{"codec_type": "audio", "codec_name": "aac"}],
        "format": {"duration": "5.0"},
    }
    info = parse_probe(payload)
    assert info.video_codec is None
    assert info.width == 0
    assert info.fps == 0.0
    assert info.duration == pytest.approx(5.0)


def test_rejects_invalid_payloads() -> None:
    with pytest.raises(ValueError, match="invalid ffprobe json"):
        parse_probe("not json")
    with pytest.raises(ValueError, match="no streams"):
        parse_probe({"streams": []})
    with pytest.raises(ValueError, match="no audio or video"):
        parse_probe({"streams": [{"codec_type": "subtitle"}]})
