"""Sequential model loading for a 4 GB VRAM budget (protocol D4).

Only one heavy model is resident at a time. When a higher-priority model is requested,
lower-priority residents are unloaded first. Everything is injectable so the policy can
be unit-tested without any real model.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.logging import get_logger

LOG = get_logger(__name__)


class ModelUnavailableError(RuntimeError):
    """Raised when a model's OSS dependency is not installed locally."""


@dataclass(frozen=True)
class ModelSpec:
    """Declarative description of a bundled model."""

    name: str
    #: Lower number = higher priority (MediaPipe > CLIP > YOLOX > the rest).
    priority: int
    approx_mb: int
    dependency: str
    loader: Callable[[], Any] = field(repr=False, default=lambda: None)


@dataclass
class _Resident:
    spec: ModelSpec
    handle: Any


def default_specs() -> list[ModelSpec]:
    """Priority table from the protocol (D4) — adapters fill in the loaders lazily."""
    return [
        ModelSpec("mediapipe-pose", 10, 15, "mediapipe"),
        ModelSpec("clip-vit-b32", 20, 350, "onnxruntime"),
        ModelSpec("yolox-s", 30, 35, "onnxruntime"),
        ModelSpec("faster-whisper-base", 40, 150, "faster_whisper"),
        ModelSpec("transnet-v2", 50, 15, "onnxruntime"),
        ModelSpec("real-esrgan", 60, 65, "onnxruntime"),
    ]


class InferenceRegistry:
    """Keeps at most ``max_resident`` heavy models in memory."""

    def __init__(self, specs: list[ModelSpec] | None = None, max_resident: int = 1) -> None:
        self._specs = {spec.name: spec for spec in (specs or default_specs())}
        self._order = sorted(self._specs.values(), key=lambda spec: spec.priority)
        self._resident: dict[str, _Resident] = {}
        self._max_resident = max(1, max_resident)

    @property
    def order(self) -> list[str]:
        """Model names in priority order."""
        return [spec.name for spec in self._order]

    def specs(self) -> list[ModelSpec]:
        return list(self._specs.values())

    def resident(self) -> list[str]:
        return list(self._resident)

    def slot_for(self, name: str) -> ModelSpec:
        spec = self._specs.get(name)
        if spec is None:
            msg = f"unknown model '{name}'; known: {', '.join(self.order)}"
            raise KeyError(msg)
        return spec

    def load(self, name: str) -> Any:
        """Return the loaded handle, loading it and evicting lower-priority models."""
        spec = self.slot_for(name)
        existing = self._resident.get(name)
        if existing is not None:
            return existing.handle

        if len(self._resident) >= self._max_resident:
            self._evict_for(spec)

        try:
            handle = spec.loader()
        except ImportError as error:
            msg = (
                f"model '{name}' needs the OSS extra '{spec.dependency}', which is not installed. "
                f"Install it on the build machine (bundled at packaging time)."
            )
            raise ModelUnavailableError(msg) from error

        self._resident[name] = _Resident(spec=spec, handle=handle)
        LOG.info("inference.loaded", model=name, approx_mb=spec.approx_mb)
        return handle

    def _evict_for(self, incoming: ModelSpec) -> None:
        candidates = sorted(
            self._resident.values(), key=lambda item: item.spec.priority, reverse=True
        )
        while self._resident and len(self._resident) >= self._max_resident:
            victim = candidates.pop(0) if candidates else None
            if victim is None:
                break
            if victim.spec.priority < incoming.priority:
                LOG.info(
                    "inference.keep", model=victim.spec.name, reason="higher priority than request"
                )
                continue
            self._resident.pop(victim.spec.name, None)
            LOG.info("inference.evicted", model=victim.spec.name, for_model=incoming.name)

    def unload(self, name: str) -> bool:
        removed = self._resident.pop(name, None)
        if removed is not None:
            LOG.info("inference.unloaded", model=name)
        return removed is not None

    def unload_all(self) -> None:
        for name in list(self._resident):
            self.unload(name)
