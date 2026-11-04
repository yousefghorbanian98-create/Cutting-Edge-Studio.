"""Stages 5-6 — build the edit decision list and snap it to the music grid."""

from __future__ import annotations

from typing import Any

from app.services.stylematch.dna import target_cut_length
from app.services.stylematch.types import EDL, EDLSegment, StyleDNA

#: Preferred source ordering: peak-contraction shots first (sports narrative).
SHOT_PRIORITY: tuple[str, ...] = ("closeup", "detail", "medium", "wide", "unknown")
#: Beat snap tolerance in seconds (protocol target: cuts within 100 ms of a beat).
BEAT_TOLERANCE = 0.12


def _segments_from_clips(
    source: dict[str, Any], cut_length: float, dna: StyleDNA
) -> list[EDLSegment]:
    """Turn analysed source clips into candidate segments (peak moments first)."""
    candidates: list[dict[str, Any]] = [
        {
            "source": str(clip.get("path") or clip.get("name") or "clip"),
            "in_point": float(moment.get("start", 0.0)),
            "score": float(moment.get("score", 0.0)),
            "shot_type": str(moment.get("shot_type", "unknown")),
        }
        for clip in source.get("clips") or []
        for moment in clip.get("moments") or []
    ]

    priority = {name: index for index, name in enumerate(SHOT_PRIORITY)}
    candidates.sort(
        key=lambda item: (-item["score"], priority.get(item["shot_type"], len(priority)))
    )

    transition = str(dna.get("transition", {}).get("dominant", "cut"))
    segments: list[EDLSegment] = []
    timeline = 0.0
    for candidate in candidates:
        segments.append(
            {
                "source": candidate["source"],
                "in_point": round(candidate["in_point"], 3),
                "out_point": round(candidate["in_point"] + cut_length, 3),
                "timeline_start": round(timeline, 3),
                "duration": round(cut_length, 3),
                "shot_type": candidate["shot_type"],
                "speed": 1.0,
                "transition_in": transition,
                "transition_duration": 0.0 if transition == "cut" else 0.2,
            }
        )
        timeline += cut_length
    return segments


def build_edl(
    dna: StyleDNA,
    source: dict[str, Any],
    *,
    fps: int = 30,
    width: int = 1080,
    height: int = 1920,
    max_duration: float | None = None,
) -> EDL:
    """Stage 5: assemble segments into an EDL using the reference's cut rhythm."""
    cut_length = target_cut_length(dna, percentile=0.5)
    segments = _segments_from_clips(source, cut_length, dna)
    notes: list[str] = []

    if max_duration is not None:
        kept: list[EDLSegment] = []
        timeline = 0.0
        for segment in segments:
            if timeline + segment["duration"] > max_duration:
                break
            kept.append(segment)
            timeline += segment["duration"]
        if len(kept) != len(segments):
            notes.append(f"trimmed {len(segments) - len(kept)} segments to respect max_duration")
        segments = kept

    if not segments:
        notes.append("no peak moments found in the source analysis")

    total = round(sum(segment["duration"] for segment in segments), 3)
    return {
        "version": "1.0",
        "fps": fps,
        "width": width,
        "height": height,
        "total_duration": total,
        "segments": segments,
        "color": dict(dna.get("color") or {}),
        "audio": dict(dna.get("audio") or {}),
        "notes": notes,
    }


def snap_to_beats(edl: EDL, beats: list[float], *, tolerance: float = BEAT_TOLERANCE) -> EDL:
    """Stage 6: re-time each cut onto the closest beat when it is within tolerance."""
    if not beats:
        return {**edl, "notes": [*edl.get("notes", []), "no beats: EDL left unsnapped"]}

    ordered = sorted(beats)
    snapped: list[EDLSegment] = []
    timeline = 0.0
    adjustments = 0
    for segment in edl.get("segments", []):
        candidate = min(ordered, key=lambda beat: abs(beat - timeline))
        start = candidate if abs(candidate - timeline) <= tolerance else timeline
        if abs(start - timeline) > 1e-6:
            adjustments += 1
        intended_end = start + segment["duration"]
        nearest_end = min(ordered, key=lambda beat: abs(beat - intended_end))
        duration = (
            nearest_end - start
            if abs(nearest_end - intended_end) <= tolerance
            else segment["duration"]
        )
        if duration <= 0.2:
            duration = segment["duration"]
        snapped.append(
            {
                **segment,
                "timeline_start": round(start, 3),
                "duration": round(duration, 3),
                "out_point": round(segment["in_point"] + duration, 3),
            }
        )
        timeline = start + duration

    total = round(sum(segment["duration"] for segment in snapped), 3)
    notes = [*edl.get("notes", []), f"snapped {adjustments} cuts to the beat grid"]
    return {**edl, "version": "1.1", "segments": snapped, "total_duration": total, "notes": notes}


def cut_times(edl: EDL) -> list[float]:
    """Timeline positions (s) where a cut happens, including the final end."""
    times = [segment["timeline_start"] for segment in edl.get("segments", [])]
    if edl.get("segments"):
        times.append(round(edl.get("total_duration", 0.0), 3))
    return times


def validate_edl(edl: EDL) -> list[str]:
    """Structural validation: returns a list of problems (empty = valid)."""
    problems: list[str] = []
    previous_end = -1.0
    for index, segment in enumerate(edl.get("segments", [])):
        if segment["duration"] <= 0:
            problems.append(f"segment {index}: non-positive duration")
        if segment["out_point"] <= segment["in_point"]:
            problems.append(f"segment {index}: out_point must be after in_point")
        if segment["timeline_start"] < previous_end - 1e-6:
            problems.append(f"segment {index}: overlaps the previous segment")
        previous_end = segment["timeline_start"] + segment["duration"]
    if edl.get("segments") and abs(previous_end - edl.get("total_duration", 0.0)) > 0.01:
        problems.append("total_duration does not match the segments")
    return problems
