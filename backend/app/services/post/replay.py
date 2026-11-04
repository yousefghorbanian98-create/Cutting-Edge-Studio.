"""Instant replay, comparison and speed-ramp plans built from pure rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

#: Replay window around a peak moment (seconds before / after).
REPLAY_LEAD = 0.8
REPLAY_TAIL = 0.4
#: Slow-motion factor applied to every replay (protocol: 0.5x, no frame interpolation).
SLOW_FACTOR = 0.5
#: Comparison layouts available to the UI.
LAYOUTS = ("side_by_side", "stacked", "picture_in_picture")


@dataclass(frozen=True)
class ReplayPlan:
    """Trim window plus the FFmpeg filters that realise the replay."""

    start: float
    end: float
    speed: float
    filters: str


def plan_replay(
    moment: dict[str, Any], *, lead: float = REPLAY_LEAD, tail: float = REPLAY_TAIL
) -> ReplayPlan:
    """Pick a window around a peak moment and reverse it at half speed.

    ``reverse`` + ``setpts`` are FFmpeg's own filters, so no frame copying happens in Python.
    """
    centre = float(moment.get("start", 0.0))
    end_of_moment = float(moment.get("end", centre))
    start = max(0.0, centre - lead)
    end = max(start + 0.2, end_of_moment + tail)
    filters = f"reverse,setpts=PTS/{SLOW_FACTOR},fps=30"
    return ReplayPlan(start=round(start, 3), end=round(end, 3), speed=SLOW_FACTOR, filters=filters)


def comparison_filters(
    layout: str,
    *,
    width: int = 1080,
    height: int = 1920,
    gap: int = 12,
    labels: tuple[str, str] | None = None,
) -> str:
    """Build the filter graph for a two-input comparison layout."""
    if layout not in LAYOUTS:
        msg = f"unknown comparison layout '{layout}' (expected one of {LAYOUTS})"
        raise ValueError(msg)

    half_h = (height - gap) // 2
    half_w = (width - gap) // 2
    if layout == "side_by_side":
        scale_a = f"scale={half_w}:{height}"
        scale_b = f"scale={half_w}:{height}"
        stack = "hstack=inputs=2:fill=black"
    elif layout == "stacked":
        scale_a = f"scale={width}:{half_h}"
        scale_b = f"scale={width}:{half_h}"
        stack = "vstack=inputs=2:fill=black"
    else:
        scale_a = f"scale={width}:{height}"
        scale_b = f"scale={int(width * 0.4)}:{int(height * 0.4)}"
        stack = f"overlay=W-w-{gap * 2}:H-h-{gap * 2}"

    parts = [f"[0:v]{scale_a}[a]", f"[1:v]{scale_b}[b]"]
    parts.append(f"[a][b]{stack},pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black[v]")

    if labels:
        text_a = labels[0].replace(":", r"\:").replace("'", "")
        text_b = labels[1].replace(":", r"\:").replace("'", "")
        box = "box=1:boxcolor=black@0.45:boxborderw=14"
        parts.append(
            f"[v]drawtext=text='{text_a}':x=40:y=40:fontsize=38:fontcolor=white:{box},"
            f"drawtext=text='{text_b}':x=w-tw-40:y=h-th-40:fontsize=38:fontcolor=white:{box}[vout]"
        )

    return ";".join(parts)
