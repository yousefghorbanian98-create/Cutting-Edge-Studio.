"""Stage 2 — extract editing DNA from analysed reference footage.

Pure functions over JSON-native dicts: no IO, no models. The CLIP/optical-flow/librosa
outputs arrive as analysis records (produced by the adapters), and this module turns them
into the numbers the EDL builder reasons about.
"""

from __future__ import annotations

import itertools
import statistics
from typing import Any

from app.services.stylematch.types import StyleDNA

#: Shot types CLIP zero-shot is prompted with (kept here so prompts and stats agree).
SHOT_TYPES: tuple[str, ...] = ("closeup", "medium", "wide", "detail", "unknown")
SHOT_PROMPTS: dict[str, str] = {
    "closeup": "a close-up shot of a bodybuilder's muscles",
    "medium": "a medium shot of an athlete from the waist up",
    "wide": "a wide shot of a gym or volleyball court",
    "detail": "a detail shot of equipment, weights or a ball",
    "unknown": "an unclear or transitional shot",
}
TRANSITION_LABELS: tuple[str, ...] = ("cut", "fade", "dissolve", "whip", "zoom")


def _quantile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def cut_lengths(shots: list[dict[str, Any]]) -> list[float]:
    """Durations of every shot, rounded to milliseconds."""
    lengths: list[float] = []
    for shot in shots:
        start = float(shot.get("start", 0.0))
        end = float(shot.get("end", 0.0))
        if end > start:
            lengths.append(round(end - start, 3))
    return lengths


def cut_stats(lengths: list[float]) -> dict[str, float]:
    """Mean/median/spread of cut lengths plus the 10th/90th percentiles."""
    if not lengths:
        return {"count": 0.0, "mean": 0.0, "median": 0.0, "stdev": 0.0, "p10": 0.0, "p90": 0.0}
    return {
        "count": float(len(lengths)),
        "mean": round(statistics.fmean(lengths), 3),
        "median": round(statistics.median(lengths), 3),
        "stdev": round(statistics.pstdev(lengths), 3) if len(lengths) > 1 else 0.0,
        "p10": round(_quantile(lengths, 0.1), 3),
        "p90": round(_quantile(lengths, 0.9), 3),
    }


def shot_type_counts(shots: list[dict[str, Any]]) -> dict[str, int]:
    """Count shots per type, keeping the canonical order."""
    counts = dict.fromkeys(SHOT_TYPES, 0)
    for shot in shots:
        label = str(shot.get("type", "unknown"))
        counts[label if label in counts else "unknown"] += 1
    return counts


def dominant_transition(shots: list[dict[str, Any]]) -> dict[str, Any]:
    """Most used transition plus the full distribution (rules over classifier output)."""
    counts = dict.fromkeys(TRANSITION_LABELS, 0)
    for shot in shots:
        label = str(shot.get("transition_out", "cut"))
        counts[label if label in counts else "cut"] += 1
    dominant = max(TRANSITION_LABELS, key=lambda name: counts[name])
    total = sum(counts.values()) or 1
    return {
        "dominant": dominant,
        "counts": counts,
        "share": round(counts[dominant] / total, 3),
        "cut_share": round(counts["cut"] / total, 3),
    }


def camera_motion_counts(shots: list[dict[str, Any]]) -> dict[str, int]:
    """Distribution of camera motion labels (OpenCV optical-flow thresholds)."""
    counts: dict[str, int] = {}
    for shot in shots:
        label = str(shot.get("motion", "static"))
        counts[label] = counts.get(label, 0) + 1
    return counts


def average_color(shots: list[dict[str, Any]]) -> dict[str, float]:
    """Duration-weighted average colour of the reference."""
    total = 0.0
    accum = {"r": 0.0, "g": 0.0, "b": 0.0, "contrast": 0.0, "saturation": 0.0}
    for shot in shots:
        weight = max(0.0, float(shot.get("end", 0.0)) - float(shot.get("start", 0.0)))
        if weight <= 0:
            continue
        color = shot.get("color") or {}
        accum["r"] += float(color.get("r", 128.0)) * weight
        accum["g"] += float(color.get("g", 128.0)) * weight
        accum["b"] += float(color.get("b", 128.0)) * weight
        accum["contrast"] += float(color.get("contrast", 0.5)) * weight
        accum["saturation"] += float(color.get("saturation", 0.5)) * weight
        total += weight
    if total == 0:
        return {"r": 128.0, "g": 128.0, "b": 128.0, "contrast": 0.5, "saturation": 0.5}
    return {key: round(value / total, 2) for key, value in accum.items()}


def bpm_from_beats(beat_times: list[float]) -> float:
    """Beats per minute from a beat grid (librosa``.beat.beat_track`` output)."""
    if len(beat_times) < 2:
        return 0.0
    intervals = [b - a for a, b in itertools.pairwise(beat_times) if b > a]
    if not intervals:
        return 0.0
    median_interval = statistics.median(intervals)
    if median_interval <= 0:
        return 0.0
    return round(60.0 / median_interval, 2)


def extend_beat_grid(beats: list[float], until: float, *, max_beats: int = 20_000) -> list[float]:
    """Repeat the reference tempo past its end so long edits still snap to a beat.

    A 20 s reference at 120 BPM gives beats up to 19.5 s; an edit of 40 s would otherwise
    have no grid for its second half, which is exactly when alignment silently degrades.
    """
    if not beats or until <= beats[-1]:
        return list(beats)
    ordered = sorted(beats)
    intervals = [b - a for a, b in itertools.pairwise(ordered) if b > a]
    if not intervals:
        return ordered
    step = statistics.median(intervals)
    if step <= 0:
        return ordered
    extended = list(ordered)
    cursor = ordered[-1]
    while cursor < until and len(extended) < max_beats:
        cursor += step
        extended.append(round(cursor, 3))
    return extended


def pacing_curve(shots: list[dict[str, Any]], buckets: int = 12) -> list[float]:
    """Energy per timeline bucket: cuts plus motion, normalized to 0-1."""
    if not shots:
        return []
    end = max(float(shot.get("end", 0.0)) for shot in shots) or 1.0
    width = end / buckets
    energy = [0.0] * buckets
    for shot in shots:
        start = float(shot.get("start", 0.0))
        bucket = min(buckets - 1, int(start / width)) if width > 0 else 0
        motion_bonus = 1.0 if str(shot.get("motion", "static")) != "static" else 0.4
        energy[bucket] += motion_bonus
    peak = max(energy) or 1.0
    return [round(value / peak, 3) for value in energy]


def extract_style_dna(reference: dict[str, Any], *, version: str = "1.0") -> StyleDNA:
    """Turn a reference analysis into the DNA the editor reasons about."""
    shots: list[dict[str, Any]] = list(reference.get("shots") or [])
    lengths = cut_lengths(shots)
    duration = float(reference.get("duration") or 0.0)
    beat_times = [float(value) for value in (reference.get("beats") or [])]

    dna: StyleDNA = {
        "version": version,
        "reference": {
            "duration": round(duration, 3),
            "fps": float(reference.get("fps") or 0.0),
            "width": int(reference.get("width") or 0),
            "height": int(reference.get("height") or 0),
            "shot_count": len(shots),
        },
        "cut_lengths": lengths,
        "cut_stats": cut_stats(lengths),
        "shot_type_counts": shot_type_counts(shots),
        "shots_per_minute": round(len(shots) / (duration / 60), 2) if duration > 0 else 0.0,
        "bpm": bpm_from_beats(beat_times),
        "beat_times": beat_times,
        "color": average_color(shots),
        "camera_motion": camera_motion_counts(shots),
        "transition": dominant_transition(shots),
        "audio": {
            "has_music": bool(reference.get("has_music", False)),
            "loudness_lufs": float(reference.get("loudness_lufs") or -16.0),
        },
        "pacing_curve": pacing_curve(shots),
    }
    return dna


def target_cut_length(dna: StyleDNA, *, percentile: float = 0.5) -> float:
    """Preferred cut length from the DNA (median by default)."""
    lengths = list(dna.get("cut_lengths") or [])
    if not lengths:
        return 2.0
    return round(max(0.4, _quantile(lengths, percentile)), 3)
