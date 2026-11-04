"""Typed contracts for the Style Match artifacts (JSON-native dicts)."""

from __future__ import annotations

from typing import Any, TypedDict


class ShotTypeCounts(TypedDict, total=False):
    """Counts per shot type (CLIP zero-shot labels)."""

    closeup: int
    medium: int
    wide: int
    detail: int
    unknown: int


class ColorStats(TypedDict):
    """Average colour of a clip/edit, in sRGB 0-255."""

    r: float
    g: float
    b: float
    contrast: float
    saturation: float


class ShotRecord(TypedDict, total=False):
    """One detected shot from the reference or a source clip."""

    start: float
    end: float
    type: str
    motion: str
    transition_out: str
    color: dict[str, float]
    has_face: bool
    hype: float


class StyleDNA(TypedDict, total=False):
    """Editing DNA extracted from a reference video (Stage 2 output)."""

    version: str
    reference: dict[str, Any]
    cut_lengths: list[float]
    cut_stats: dict[str, float]
    shot_type_counts: ShotTypeCounts
    shots_per_minute: float
    bpm: float
    beat_times: list[float]
    color: ColorStats
    camera_motion: dict[str, int]
    transition: dict[str, Any]
    audio: dict[str, Any]
    pacing_curve: list[float]


class EDLSegment(TypedDict, total=False):
    """One cut in the edit decision list."""

    source: str
    in_point: float
    out_point: float
    timeline_start: float
    duration: float
    shot_type: str
    speed: float
    transition_in: str
    transition_duration: float
    zoom: dict[str, float]


class EDL(TypedDict, total=False):
    """Stage 5/6 output consumed by the renderer."""

    version: str
    fps: int
    width: int
    height: int
    total_duration: float
    segments: list[EDLSegment]
    color: dict[str, Any]
    audio: dict[str, Any]
    notes: list[str]
