"""Sequential model registry and CLIP/NMS math."""

from __future__ import annotations

import pytest
from app.services.inference.adapters import (
    best_prompt,
    clip_onnx_spec,
    cosine_similarity,
    iou,
    l2_normalize,
    local_model_path,
    non_max_suppression,
    rank_prompts,
    softmax,
)
from app.services.inference.registry import (
    InferenceRegistry,
    ModelSpec,
    ModelUnavailableError,
)


def spec(name: str, priority: int, loader) -> ModelSpec:
    return ModelSpec(name=name, priority=priority, approx_mb=10, dependency="fake", loader=loader)


def test_registry_keeps_one_model_and_evicts_lower_priority() -> None:
    loaded: list[str] = []
    registry = InferenceRegistry(
        specs=[
            spec("heavy-low", 90, lambda: loaded.append("low") or "low"),
            spec("pose", 10, lambda: "pose"),
        ],
        max_resident=1,
    )
    registry.load("heavy-low")
    assert registry.resident() == ["heavy-low"]

    registry.load("pose")
    assert registry.resident() == ["pose"]

    assert registry.order == ["pose", "heavy-low"]
    assert registry.unload("pose") is True
    assert registry.unload("pose") is False
    assert loaded == ["low"]


def test_registry_reuses_resident_handle_and_validates_names() -> None:
    calls: list[int] = []
    registry = InferenceRegistry(specs=[spec("a", 10, lambda: calls.append(1) or object())])
    first = registry.load("a")
    second = registry.load("a")
    assert first is second
    assert len(calls) == 1
    with pytest.raises(KeyError, match="unknown model"):
        registry.load("nope")


def test_missing_dependency_becomes_actionable_error() -> None:
    def broken() -> None:
        raise ImportError("no module named mediapipe")

    registry = InferenceRegistry(specs=[spec("pose", 10, broken)])
    with pytest.raises(ModelUnavailableError, match="fake"):
        registry.load("pose")


def test_unload_all_clears_registry() -> None:
    registry = InferenceRegistry(specs=[spec("a", 10, lambda: 1)], max_resident=2)
    registry.load("a")
    registry.unload_all()
    assert registry.resident() == []


def test_priority_order_is_sorted() -> None:
    names = InferenceRegistry().order
    assert names[0] == "mediapipe-pose"
    assert names.index("clip-vit-b32") < names.index("yolox-s")


def test_cosine_and_normalization() -> None:
    assert l2_normalize([3.0, 4.0]) == [0.6, 0.8]
    assert l2_normalize([0.0, 0.0]) == [0.0, 0.0]
    assert cosine_similarity([1, 0], [1, 0]) == pytest.approx(1.0)
    assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)
    assert cosine_similarity([1, 0], [1]) == 0.0
    assert cosine_similarity([], []) == 0.0
    assert cosine_similarity([0, 0], [1, 1]) == 0.0


def test_softmax_and_ranking() -> None:
    assert softmax([]) == []
    weights = softmax([1.0, 1.0])
    assert weights == pytest.approx([0.5, 0.5])

    ranked = rank_prompts([1.0, 0.0], {"gym": [1.0, 0.0], "beach": [0.0, 1.0], "court": [0.0, 0.9]})
    assert ranked[0].label == "gym"
    assert ranked[0].score > ranked[1].score
    assert sum(item.score for item in ranked) == pytest.approx(1.0)
    assert best_prompt([1.0, 0.0], {}) is None


def test_iou_and_nms() -> None:
    assert iou((0, 0, 10, 10), (0, 0, 10, 10)) == pytest.approx(1.0)
    assert iou((0, 0, 10, 10), (20, 20, 30, 30)) == 0.0
    assert iou((0, 0, 0, 0), (0, 0, 0, 0)) == 0.0

    kept = non_max_suppression(
        boxes=[(0, 0, 10, 10), (1, 1, 11, 11), (50, 50, 60, 60)],
        scores=[0.9, 0.8, 0.7],
    )
    assert kept == [0, 2]
    with pytest.raises(ValueError, match="same length"):
        non_max_suppression([(0, 0, 1, 1)], [0.5, 0.6])


def test_local_model_path_never_silently_downloads(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="never"):
        local_model_path(tmp_path, "clip", "model.onnx")
    model = tmp_path / "clip" / "model.onnx"
    model.parent.mkdir(parents=True)
    model.write_bytes(b"onnx")
    assert local_model_path(tmp_path, "clip", "model.onnx") == model


def test_model_specs_are_wired_to_local_paths(tmp_path) -> None:
    pose = __import__(
        "app.services.inference.adapters", fromlist=["mediapipe_pose_spec"]
    ).mediapipe_pose_spec(tmp_path / "pose.task")
    clip = clip_onnx_spec(tmp_path / "clip.onnx")
    assert (pose.name, pose.priority) == ("mediapipe-pose", 10)
    assert clip.dependency == "onnxruntime"
