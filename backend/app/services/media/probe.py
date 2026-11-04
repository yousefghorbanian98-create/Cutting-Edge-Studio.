"""Parse ``ffprobe -print_format json`` output into a typed description."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any

from app.logging import get_logger

LOG = get_logger(__name__)


@dataclass(frozen=True)
class MediaInfo:
    """Everything the editor needs to know about an imported file."""

    duration: float
    width: int
    height: int
    fps: float
    video_codec: str | None
    audio_codec: str | None
    bit_rate: int
    has_audio: bool
    rotation: int = 0
    sample_rate: int = 0
    channels: int = 0
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def is_portrait(self) -> bool:
        """True when the displayed orientation is vertical (accounts for rotation)."""
        rotated = self.rotation in (90, 270)
        width, height = (self.height, self.width) if rotated else (self.width, self.height)
        return height > width

    @property
    def pixels(self) -> int:
        """Pixel count, useful for proxy decisions."""
        return self.width * self.height


def _parse_fraction(value: str | None) -> float:
    if not value or value == "0/0":
        return 0.0
    try:
        return float(Fraction(value))
    except (ValueError, ZeroDivisionError):
        LOG.debug("probe.fraction.unparsable", value=value)
        return 0.0


def _rotation_of(stream: dict[str, Any]) -> int:
    tags = stream.get("tags") or {}
    rotate = tags.get("rotate")
    if rotate is not None:
        try:
            return int(float(rotate))
        except (TypeError, ValueError):
            LOG.warning("probe.rotation.unparsable", value=rotate)
            return 0
    for side_data in stream.get("side_data_list") or []:
        if "rotation" in side_data:
            try:
                return abs(int(float(side_data["rotation"])))
            except (TypeError, ValueError):
                LOG.warning("probe.rotation.unparsable", value=side_data["rotation"])
                return 0
    return 0


def parse_probe(payload: str | dict[str, Any]) -> MediaInfo:
    """Convert raw ffprobe JSON into :class:`MediaInfo`.

    Raises:
        ValueError: when the payload is not valid ffprobe JSON.
    """
    if isinstance(payload, str):
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as error:
            msg = f"invalid ffprobe json: {error}"
            raise ValueError(msg) from error
    else:
        data = payload

    streams = data.get("streams") or []
    if not streams:
        msg = "ffprobe reported no streams"
        raise ValueError(msg)

    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
    if video is None and audio is None:
        msg = "no audio or video stream found"
        raise ValueError(msg)

    format_info = data.get("format") or {}
    duration = float(format_info.get("duration") or (video or audio or {}).get("duration") or 0.0)

    return MediaInfo(
        duration=max(0.0, duration),
        width=int((video or {}).get("width") or 0),
        height=int((video or {}).get("height") or 0),
        fps=_parse_fraction(
            (video or {}).get("avg_frame_rate") or (video or {}).get("r_frame_rate")
        ),
        video_codec=(video or {}).get("codec_name"),
        audio_codec=(audio or {}).get("codec_name"),
        bit_rate=int(float(format_info.get("bit_rate") or 0)),
        has_audio=audio is not None,
        rotation=_rotation_of(video or {}),
        sample_rate=int((audio or {}).get("sample_rate") or 0),
        channels=int((audio or {}).get("channels") or 0),
        raw=data,
    )
