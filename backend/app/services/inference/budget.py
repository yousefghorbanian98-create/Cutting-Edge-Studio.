"""VRAM / memory budget planner (D4: one heavy model resident at a time)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

#: Default headroom kept free on the GPU (Windows display compositor + driver).
VRAM_RESERVE_MB = 700
#: Weights are loaded then executed; peak is roughly weights * this factor.
PEAK_FACTOR = 1.25
#: Model priority from the protocol: pose > CLIP > YOLOX > rest.
PRIORITY: tuple[str, ...] = (
    "mediapipe-pose",
    "clip-vit-b32",
    "yolox-s",
    "faster-whisper-base",
    "transnet-v2",
    "real-esrgan",
)


@dataclass(frozen=True)
class ModelFootprint:
    """Approximate resident memory of one model."""

    name: str
    weights_mb: float
    peak_mb: float


def footprint(name: str, weights_mb: float) -> ModelFootprint:
    """Peak resident memory estimate for a model with the given weight size."""
    return ModelFootprint(
        name=name, weights_mb=float(weights_mb), peak_mb=round(weights_mb * PEAK_FACTOR, 1)
    )


def priority_index(name: str) -> int:
    """Lower is more important; unknown models sit last but stay usable."""
    return PRIORITY.index(name) if name in PRIORITY else len(PRIORITY)


def fits_in_budget(
    models: list[ModelFootprint], budget_mb: float, *, reserve_mb: float = VRAM_RESERVE_MB
) -> bool:
    """Whether all models can stay resident at once (they are not supposed to)."""
    available = max(0.0, budget_mb - reserve_mb)
    return sum(model.peak_mb for model in models) <= available


def plan_sequence(
    models: list[ModelFootprint], budget_mb: float, *, reserve_mb: float = VRAM_RESERVE_MB
) -> list[dict[str, Any]]:
    """Ordered load/unload plan that never exceeds the budget.

    Highest priority is scheduled first; a model that cannot fit even alone is
    reported as ``fits=False`` so the caller can fall back to CPU.
    """
    available = max(0.0, budget_mb - reserve_mb)
    ordered = sorted(models, key=lambda model: (priority_index(model.name), model.peak_mb))
    plan: list[dict[str, Any]] = []
    for model in ordered:
        fits = model.peak_mb <= available
        plan.append(
            {
                "name": model.name,
                "peak_mb": model.peak_mb,
                "fits": fits,
                "device": "gpu" if fits else "cpu",
                "evicts": [] if not plan else [entry["name"] for entry in plan],
            }
        )
    return plan


def choose_device(
    vram_mb: float | None, required_mb: float, *, reserve_mb: float = VRAM_RESERVE_MB
) -> str:
    """GPU when there is room, CPU otherwise (logged by the caller, never silent)."""
    if vram_mb is None or vram_mb <= 0:
        return "cpu"
    return "gpu" if vram_mb - reserve_mb >= required_mb else "cpu"
