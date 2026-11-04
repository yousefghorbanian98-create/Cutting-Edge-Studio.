"""The 11-stage Style Match pipeline, expressed as composable OSS-backed steps.

Only pure, testable steps live here: manifest → DNA → source analysis → compatibility →
EDL → beat alignment → render plan. Model inference and FFmpeg execution are injected,
which keeps the orchestrator free of GPU/IO concerns (and unit-testable in CI).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any

from app.services.stylematch.compat import check_compatibility
from app.services.stylematch.dna import extract_style_dna
from app.services.stylematch.edl import build_edl, snap_to_beats, validate_edl
from app.services.stylematch.metrics import (
    beat_alignment,
    color_delta_e,
    cut_length_ks,
    evaluate_match,
    pacing_similarity,
    shot_type_f1,
)
from app.services.stylematch.types import EDL, StyleDNA

PIPELINE_VERSION = "1.0"


@dataclass
class PipelineResult:
    """All artifacts produced by one run, ready to be persisted."""

    manifest: dict[str, Any]
    dna: StyleDNA
    source: dict[str, Any]
    compatibility: dict[str, Any]
    edl: EDL
    edl_v2: EDL
    problems: list[str] = field(default_factory=list)


def build_reference_manifest(
    paths: list[Path], *, metadata: dict[str, dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Stage 1: record the reference files with a content hash (no file is modified)."""
    files: list[dict[str, Any]] = []
    for path in paths:
        digest = sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
        info = (metadata or {}).get(str(path), {})
        files.append(
            {
                "path": str(path),
                "sha256": digest,
                "duration": float(info.get("duration", 0.0)),
                "width": int(info.get("width", 0)),
                "height": int(info.get("height", 0)),
                "fps": float(info.get("fps", 0.0)),
            }
        )
    return {"version": PIPELINE_VERSION, "files": files}


def summarize_source(analysis: dict[str, Any]) -> dict[str, Any]:
    """Stage 3 normalisation: keep only what later stages rely on."""
    clips = []
    for clip in analysis.get("clips") or []:
        moments = [
            {
                "start": float(moment.get("start", 0.0)),
                "end": float(moment.get("end", moment.get("start", 0.0))),
                "score": float(moment.get("score", 0.0)),
                "shot_type": str(moment.get("shot_type", "unknown")),
                "kind": str(moment.get("kind", "generic")),
            }
            for moment in clip.get("moments") or []
        ]
        clips.append(
            {
                "path": str(clip.get("path", "")),
                "name": str(clip.get("name", Path(str(clip.get("path", ""))).name)),
                "duration": float(clip.get("duration", 0.0)),
                "width": int(clip.get("width", 0)),
                "height": int(clip.get("height", 0)),
                "fps": float(clip.get("fps", 0.0)),
                "faces": bool(clip.get("faces", False)),
                "moments": sorted(moments, key=lambda item: item["score"], reverse=True),
            }
        )
    return {"clips": clips, "has_audio": bool(analysis.get("has_audio", True))}


def run_pipeline(
    reference_analysis: dict[str, Any],
    source_analysis: dict[str, Any],
    *,
    fps: int = 30,
    width: int = 1080,
    height: int = 1920,
    max_duration: float | None = None,
) -> PipelineResult:
    """Run stages 2-8 without touching the GPU or the filesystem."""
    manifest = {
        "version": PIPELINE_VERSION,
        "files": [
            {
                "path": str(reference_analysis.get("path", "reference")),
                "duration": float(reference_analysis.get("duration", 0.0)),
                "width": int(reference_analysis.get("width", 0)),
                "height": int(reference_analysis.get("height", 0)),
                "fps": float(reference_analysis.get("fps", 0.0)),
            }
        ],
    }
    dna = extract_style_dna(reference_analysis)
    source = summarize_source(source_analysis)
    compatibility = check_compatibility(dna, source)
    edl = build_edl(dna, source, fps=fps, width=width, height=height, max_duration=max_duration)
    edl_v2 = snap_to_beats(edl, list(dna.get("beat_times") or []))
    problems = validate_edl(edl_v2)
    if not compatibility.get("ready", False):
        problems.append("compatibility check blocks rendering")
    return PipelineResult(
        manifest=manifest,
        dna=dna,
        source=source,
        compatibility=compatibility,
        edl=edl,
        edl_v2=edl_v2,
        problems=problems,
    )


def score_against_reference(
    edl: EDL,
    dna: StyleDNA,
    *,
    shot_confusion: dict[str, dict[str, int]] | None = None,
    generated_color: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Evaluate the G12 acceptance metrics for a produced edit against its DNA."""
    generated_lengths = [segment["duration"] for segment in edl.get("segments", [])]
    cuts = [segment["timeline_start"] for segment in edl.get("segments", [])]
    pacing_generated = [segment["duration"] for segment in edl.get("segments", [])]
    results = {
        "cut_length_ks": cut_length_ks(generated_lengths, list(dna.get("cut_lengths") or [])),
        "shot_type_f1": shot_type_f1(shot_confusion or {}),
        "beat_alignment": beat_alignment(cuts, list(dna.get("beat_times") or [])),
        "pacing_similarity": pacing_similarity(
            pacing_generated, list(dna.get("pacing_curve") or [])
        ),
        "color_delta_e": color_delta_e(
            generated_color or dict(dna.get("color") or {}), dict(dna.get("color") or {})
        ),
    }
    return evaluate_match(results)
