"""Stage 4 — compatibility check between the reference DNA and the user's clips."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.stylematch.types import StyleDNA

#: Minimum source clips for a credible edit (protocol: 10 clips + 1 reference).
MIN_SOURCE_CLIPS = 3
#: Aspect/ratio tolerance before the UI warns about framing.
ASPECT_TOLERANCE = 0.05


@dataclass(frozen=True)
class Finding:
    """One compatibility finding."""

    code: str
    severity: str  # "info" | "warn" | "block"
    message: str


def _aspect(width: float, height: float) -> float:
    return width / height if height else 0.0


def check_compatibility(dna: StyleDNA, source: dict[str, Any]) -> dict[str, Any]:
    """Compare DNA expectations with the available source material."""
    findings: list[Finding] = []
    clips = list(source.get("clips") or [])
    total_duration = sum(float(clip.get("duration") or 0.0) for clip in clips)
    reference = dna.get("reference") or {}

    if len(clips) < MIN_SOURCE_CLIPS:
        findings.append(
            Finding(
                code="source.too_few_clips",
                severity="block",
                message=f"need at least {MIN_SOURCE_CLIPS} clips, got {len(clips)}",
            )
        )

    needed = float(dna.get("cut_stats", {}).get("mean", 2.0)) * max(
        1, int(reference.get("shot_count") or 1)
    )
    if total_duration < needed * 0.5:
        findings.append(
            Finding(
                code="source.insufficient_footage",
                severity="warn",
                message=(
                    f"footage {total_duration:.1f}s is short for a {needed:.1f}s edit;"
                    " expect reused shots"
                ),
            )
        )

    ref_aspect = _aspect(float(reference.get("width") or 0), float(reference.get("height") or 0))
    for clip in clips:
        clip_aspect = _aspect(float(clip.get("width") or 0), float(clip.get("height") or 0))
        if (
            ref_aspect
            and clip_aspect
            and abs(ref_aspect - clip_aspect) / ref_aspect > ASPECT_TOLERANCE
        ):
            name = clip.get("name", "clip")
            findings.append(
                Finding(
                    code="aspect.mismatch",
                    severity="warn",
                    message=f"{name} has a different aspect ratio; auto-reframe will crop",
                )
            )
            break

    if not dna.get("beat_times"):
        findings.append(
            Finding(
                code="audio.no_beats",
                severity="info",
                message="no beat grid detected; cuts follow shot stats",
            )
        )

    if not source.get("has_audio", True):
        findings.append(
            Finding(
                code="audio.silent_source",
                severity="info",
                message="source clips are silent; music drives rhythm",
            )
        )

    if not any(clip.get("faces") for clip in clips):
        findings.append(
            Finding(
                code="faces.none",
                severity="info",
                message="no faces found; virtual camera stays static",
            )
        )

    blocking = [finding for finding in findings if finding.severity == "block"]
    return {
        "ready": not blocking,
        "score": round(
            max(
                0.0,
                1.0
                - 0.2 * len([f for f in findings if f.severity == "warn"])
                - 0.5 * len(blocking),
            ),
            3,
        ),
        "findings": [finding.__dict__ for finding in findings],
        "source": {
            "clip_count": len(clips),
            "total_duration": round(total_duration, 3),
        },
    }
