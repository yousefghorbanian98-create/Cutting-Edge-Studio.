"""Thin adapters over pre-trained OSS models.

Every adapter imports its heavy dependency **lazily** and only from a local file path:
no library may download weights at runtime (Auto-Failure #5). The numeric helpers in this
module are pure and fully unit-tested.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.services.inference.registry import ModelSpec


@dataclass(frozen=True)
class ZeroShotResult:
    """A ranked zero-shot label."""

    label: str
    score: float


def l2_normalize(vector: list[float]) -> list[float]:
    """Unit-length copy of ``vector`` (all-zero vectors are returned unchanged)."""
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return list(vector)
    return [value / norm for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """Cosine similarity in [-1, 1]; mismatched or empty inputs give 0."""
    if not left or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    norm_left = math.sqrt(sum(value * value for value in left))
    norm_right = math.sqrt(sum(value * value for value in right))
    if norm_left == 0 or norm_right == 0:
        return 0.0
    return dot / (norm_left * norm_right)


def softmax(scores: list[float], temperature: float = 1.0) -> list[float]:
    """Numerically stable softmax; returns uniform weights for an empty list."""
    if not scores:
        return []
    scale = max(temperature, 1e-6)
    peak = max(scores)
    exponents = [math.exp((score - peak) / scale) for score in scores]
    total = sum(exponents)
    return [value / total for value in exponents]


def rank_prompts(
    image_embedding: list[float],
    prompt_embeddings: dict[str, list[float]],
    *,
    temperature: float = 0.01,
) -> list[ZeroShotResult]:
    """Rank CLIP text prompts against one image embedding (zero-shot classification)."""
    labels = list(prompt_embeddings)
    similarities = [
        cosine_similarity(image_embedding, prompt_embeddings[label]) for label in labels
    ]
    weights = softmax(similarities, temperature=temperature)
    ranked = [
        ZeroShotResult(label=label, score=weight)
        for label, weight in zip(labels, weights, strict=True)
    ]
    return sorted(ranked, key=lambda item: item.score, reverse=True)


def best_prompt(
    image_embedding: list[float], prompt_embeddings: dict[str, list[float]]
) -> ZeroShotResult | None:
    """Top label, or None when there are no prompts."""
    ranked = rank_prompts(image_embedding, prompt_embeddings)
    return ranked[0] if ranked else None


def iou(
    box_a: tuple[float, float, float, float], box_b: tuple[float, float, float, float]
) -> float:
    """Intersection over union for ``(x1, y1, x2, y2)`` boxes."""
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    inter_x1, inter_y1 = max(ax1, bx1), max(ay1, by1)
    inter_x2, inter_y2 = min(ax2, bx2), min(ay2, by2)
    inter_w, inter_h = max(0.0, inter_x2 - inter_x1), max(0.0, inter_y2 - inter_y1)
    intersection = inter_w * inter_h
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - intersection
    return 0.0 if union <= 0 else intersection / union


def non_max_suppression(
    boxes: list[tuple[float, float, float, float]],
    scores: list[float],
    iou_threshold: float = 0.45,
) -> list[int]:
    """Greedy NMS returning kept indices (used for YOLOX ball/player detections)."""
    if len(boxes) != len(scores):
        msg = "boxes and scores must have the same length"
        raise ValueError(msg)
    order = sorted(range(len(boxes)), key=lambda index: scores[index], reverse=True)
    kept: list[int] = []
    while order:
        current = order.pop(0)
        kept.append(current)
        order = [index for index in order if iou(boxes[current], boxes[index]) <= iou_threshold]
    return kept


def local_model_path(root: Path, *parts: str) -> Path:
    """Resolve a bundled model path and fail loudly when it is missing.

    Guards Auto-Failure #5: adapters never fall back to a download URL.
    """
    path = root.joinpath(*parts)
    if not path.exists():
        msg = (
            f"model file missing: {path}. Models are bundled at build time and never "
            f"downloaded at runtime — run scripts/build-installer.ps1 on the build machine."
        )
        raise FileNotFoundError(msg)
    return path


def mediapipe_pose_spec(model_path: Path) -> ModelSpec:
    """MediaPipe pose spec wired to a local ``.task`` bundle."""
    return ModelSpec(
        name="mediapipe-pose",
        priority=10,
        approx_mb=15,
        dependency="mediapipe",
        loader=lambda: _load_mediapipe(model_path),
    )


def _load_mediapipe(model_path: Path) -> Any:
    import mediapipe as mp

    base_options = mp.tasks.BaseOptions(model_asset_path=str(model_path))
    return mp.tasks.vision.PoseLandmarker.create_from_options(
        mp.tasks.vision.PoseLandmarkerOptions(base_options=base_options),
    )


def clip_onnx_spec(model_path: Path) -> ModelSpec:
    """CLIP image encoder spec (onnxruntime, CPU by default)."""
    return ModelSpec(
        name="clip-vit-b32",
        priority=20,
        approx_mb=350,
        dependency="onnxruntime",
        loader=lambda: _load_onnx(model_path),
    )


def _load_onnx(model_path: Path) -> Any:
    import onnxruntime as ort

    options = ort.SessionOptions()
    options.intra_op_num_threads = 0
    providers = ["CPUExecutionProvider"]
    return ort.InferenceSession(str(model_path), sess_options=options, providers=providers)
