"""Parse FFmpeg ``-progress`` output into typed progress events."""

from __future__ import annotations

from dataclasses import dataclass

from app.logging import get_logger

LOG = get_logger(__name__)


@dataclass(frozen=True)
class ProgressEvent:
    """One progress sample. ``percent`` is None when the total is unknown."""

    out_time_seconds: float
    speed: float
    percent: float | None
    frame: int
    done: bool


def _to_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        LOG.debug("progress.value.unparsable", value=value)
        return 0.0


def _to_timecode_seconds(value: str) -> float:
    """Parse ``00:01:02.500000`` (FFmpeg out_time)."""
    parts = value.strip().split(":")
    if len(parts) != 3:
        return 0.0
    hours, minutes, seconds = parts
    return _to_float(hours) * 3600 + _to_float(minutes) * 60 + _to_float(seconds)


def parse_progress_block(block: str, total_seconds: float | None = None) -> ProgressEvent | None:
    """Parse one ``key=value`` block; returns None when the block carries no timing."""
    fields: dict[str, str] = {}
    for line in block.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            fields[key.strip()] = value.strip()
    if not fields:
        return None

    out_time = _to_timecode_seconds(fields.get("out_time", "0:0:0"))
    speed = _to_float(fields.get("speed", "0").replace("x", ""))
    frame = int(_to_float(fields.get("frame", "0")))
    done = fields.get("progress") == "end"
    percent = None
    if total_seconds and total_seconds > 0:
        percent = max(0.0, min(100.0, (out_time / total_seconds) * 100))
    if done and percent is not None:
        percent = 100.0
    return ProgressEvent(
        out_time_seconds=out_time,
        speed=speed,
        percent=percent,
        frame=frame,
        done=done,
    )
