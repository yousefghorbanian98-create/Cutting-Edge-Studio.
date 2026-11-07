"""Hype score = weighted sum of scores that already exist (no new model, LOCK-00)."""

from __future__ import annotations

from dataclasses import dataclass

#: Weights from the protocol's "viral edit" heuristics; they sum to 1.0.
HYPE_WEIGHTS: dict[str, float] = {
    "motion": 0.3,
    "audio": 0.25,
    "face": 0.2,
    "action": 0.15,
    "novelty": 0.1,
}


@dataclass(frozen=True)
class HypeBreakdown:
    """Score plus the per-signal contribution, so the UI can explain itself."""

    score: float
    contributions: dict[str, float]


def clamp01(value: float) -> float:
    """Clamp a score into [0, 1]."""
    return max(0.0, min(1.0, float(value)))


def compute_hype(signals: dict[str, float]) -> HypeBreakdown:
    """Weighted sum of normalized signals; unknown signals contribute nothing."""
    total = 0.0
    contributions: dict[str, float] = {}
    for name, weight in HYPE_WEIGHTS.items():
        value = clamp01(signals.get(name, 0.0))
        contribution = round(value * weight, 4)
        contributions[name] = contribution
        total += contribution
    return HypeBreakdown(score=round(clamp01(total), 4), contributions=contributions)
