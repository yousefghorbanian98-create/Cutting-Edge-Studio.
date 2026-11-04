"""Reusable fixtures and fakes for the media pipeline tests."""

from __future__ import annotations

import json
from pathlib import Path

FFPROBE_VIDEO = {
    "streams": [
        {
            "codec_type": "video",
            "codec_name": "h264",
            "width": 1920,
            "height": 1080,
            "avg_frame_rate": "30000/1001",
            "tags": {"rotate": "0"},
        },
        {
            "codec_type": "audio",
            "codec_name": "aac",
            "sample_rate": "48000",
            "channels": 2,
        },
    ],
    "format": {"duration": "12.345", "bit_rate": "8000000"},
}

FFPROBE_ROTATED = {
    "streams": [
        {
            "codec_type": "video",
            "codec_name": "hevc",
            "width": 1920,
            "height": 1080,
            "avg_frame_rate": "60/1",
            "side_data_list": [{"rotation": -90}],
        }
    ],
    "format": {"duration": "3.0", "bit_rate": "12000000"},
}

ENCODER_LIST = """
 V..... = Video
 ------
 V....D h264_nvenc           NVIDIA NVENC H.264 encoder (codec h264)
 V....D libopenh264          OpenH264 H.264 / AVC encoder (codec h264)
 V....D libx264              libx264 H.264 / AVC (codec h264)
 A....D aac                  AAC encoder
"""


def fake_ffmpeg_tree(root: Path, *, include_ffprobe: bool = True) -> Path:
    """Create a fake bundled FFmpeg layout under ``root``."""
    bin_dir = root / "ffmpeg" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    (bin_dir / "ffmpeg").write_text("#!/bin/sh\n", encoding="utf-8")
    if include_ffprobe:
        (bin_dir / "ffprobe").write_text("#!/bin/sh\n", encoding="utf-8")
    return bin_dir


def write_json(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path
