"""Thumbnail candidate scoring (sharpness x brightness x face size, no ML required)."""

from __future__ import annotations

from typing import Any

import numpy as np

#: Minimum Laplacian variance considered "sharp" (tuned on 1080p frames).
SHARPNESS_REFERENCE = 500.0
#: Frames darker/brighter than these are penalised.
DARK_LIMIT = 40.0
BRIGHT_LIMIT = 225.0


def sharpness(frame: np.ndarray) -> float:
    """Variance of the Laplacian (the classic OSS blur metric)."""
    if frame.ndim == 3:
        frame = frame.mean(axis=2)
    kernel = np.asarray([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=float)
    height, width = frame.shape
    if height < 3 or width < 3:
        return 0.0
    accum = np.zeros((height - 2, width - 2), dtype=float)
    for dy in range(3):
        for dx in range(3):
            weight = kernel[dy, dx]
            if weight:
                accum += weight * frame[dy : dy + height - 2, dx : dx + width - 2]
    return float(accum.var())


def brightness_score(frame: np.ndarray) -> float:
    """1.0 for well-exposed frames, tapering to 0 for clipped blacks/whites."""
    mean = float(np.asarray(frame, dtype=float).mean())
    if mean < DARK_LIMIT:
        return max(0.0, mean / DARK_LIMIT)
    if mean > BRIGHT_LIMIT:
        return max(0.0, (255.0 - mean) / (255.0 - BRIGHT_LIMIT))
    return 1.0


def face_score(box: dict[str, float] | None, frame_area: float) -> float:
    """Face area share, normalised so a 10 % face fills the score."""
    if not box or frame_area <= 0:
        return 0.0
    width = float(box.get("w", 0.0))
    height = float(box.get("h", 0.0))
    return float(min(1.0, (width * height) / frame_area / 0.10))


def score_frame(
    frame: np.ndarray, *, face: dict[str, float] | None = None, weight_face: float = 0.35
) -> dict[str, float]:
    """Composite thumbnail score in 0-1 with its components."""
    height, width = frame.shape[:2]
    sharp = min(1.0, sharpness(frame) / SHARPNESS_REFERENCE)
    bright = brightness_score(frame)
    face_value = face_score(face, float(width * height))
    composite = (1 - weight_face) * (0.65 * sharp + 0.35 * bright) + weight_face * face_value
    return {
        "score": round(composite, 4),
        "sharpness": round(sharp, 4),
        "brightness": round(bright, 4),
        "face": round(face_value, 4),
    }


def rank_thumbnails(candidates: list[dict[str, Any]], *, top: int = 3) -> list[dict[str, Any]]:
    """Sort scored candidates and return the best ``top`` (stable by timestamp)."""
    ordered = sorted(
        candidates, key=lambda item: (-float(item.get("score", 0.0)), float(item.get("time", 0.0)))
    )
    return ordered[: max(1, top)]
