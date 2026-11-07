"""Volleyball action mapping, pose fusion, rallies and court geometry."""

from __future__ import annotations

import pytest
from app.services.sports.hype import HYPE_WEIGHTS, clamp01, compute_hype
from app.services.sports.pose_geometry import Landmark
from app.services.sports.volleyball import (
    KINETICS_MAP,
    classify_action,
    court_quad_from_lines,
    detect_rallies,
    map_kinetics,
)


def pose(overrides: dict[int, Landmark] | None = None) -> list[Landmark]:
    landmarks = [Landmark(0.5, 0.5) for _ in range(33)]
    landmarks[11] = Landmark(0.42, 0.30)
    landmarks[12] = Landmark(0.58, 0.30)
    landmarks[13] = Landmark(0.40, 0.42)
    landmarks[14] = Landmark(0.60, 0.42)
    landmarks[15] = Landmark(0.40, 0.55)
    landmarks[16] = Landmark(0.60, 0.55)
    landmarks[25] = Landmark(0.45, 0.70)
    landmarks[26] = Landmark(0.55, 0.70)
    landmarks[27] = Landmark(0.45, 0.90)
    landmarks[28] = Landmark(0.55, 0.90)
    for index, landmark in (overrides or {}).items():
        landmarks[index] = landmark
    return landmarks


JUMPING_POSE = pose(
    {
        15: Landmark(0.40, 0.05),
        16: Landmark(0.60, 0.05),
        25: Landmark(0.45, 0.72),
        26: Landmark(0.55, 0.72),
        27: Landmark(0.45, 0.95),
        28: Landmark(0.55, 0.95),
    }
)


def test_map_kinetics_aggregates_and_ignores_unknown_labels() -> None:
    ranked = map_kinetics({"jumping": 0.6, "spiking a volleyball": 0.5, "eating": 0.9})
    assert ranked[0][0] == "spike"
    assert dict(ranked)["spike"] == pytest.approx(0.6)
    assert map_kinetics({"eating": 1.0}) == []
    assert KINETICS_MAP["diving"] == "dig"


def test_model_only_when_pose_missing() -> None:
    decision = classify_action({"jumping": 0.8})
    assert decision.action == "spike"
    assert decision.confidence == pytest.approx(0.8)
    assert any("pose unavailable" in item for item in decision.evidence)

    weak = classify_action({"jumping": 0.2})
    assert weak.action == "unknown"


def test_pose_confirms_model_prediction() -> None:
    decision = classify_action({"jumping": 0.7}, JUMPING_POSE)
    assert decision.action in {"spike", "block"}
    assert "pose:confirms spike" in decision.evidence
    assert decision.confidence > 0.7


def test_pose_contradiction_falls_back_or_unknown() -> None:
    decision = classify_action({"jumping": 0.7}, pose())
    assert decision.model_action == "spike"
    assert decision.action in {"dig", "pass", "unknown"}
    assert any("contradicts" in item for item in decision.evidence)


def test_no_mapped_label_is_unknown() -> None:
    decision = classify_action({"eating": 0.99})
    assert decision.action == "unknown"
    assert decision.confidence == 0.0


def test_rally_detection_splits_on_serve_and_gaps() -> None:
    actions = [
        (0.0, "serve"),
        (2.0, "pass"),
        (4.0, "spike"),
        (20.0, "serve"),
        (21.0, "dig"),
        (22.0, "set"),
    ]
    rallies = detect_rallies(actions, gap_seconds=5.0, min_touches=2)
    assert len(rallies) == 2
    assert rallies[0].start == 0.0
    assert rallies[0].touches == 3
    assert rallies[1].touches == 3
    assert rallies[0].duration == pytest.approx(4.0)


def test_single_touch_rallies_are_dropped() -> None:
    assert detect_rallies([(0.0, "serve")], min_touches=2) == []


def test_court_quad_requires_lines_and_intersects() -> None:
    with pytest.raises(ValueError, match="at least 4 lines"):
        court_quad_from_lines([((0, 0), (1, 1))])

    lines = [
        ((0.0, 0.0), (100.0, 0.0)),
        ((100.0, 0.0), (100.0, 60.0)),
        ((100.0, 60.0), (0.0, 60.0)),
        ((0.0, 60.0), (0.0, 0.0)),
    ]
    corners = court_quad_from_lines(lines)
    assert len(corners) == 4
    assert (0.0, 0.0) in corners


def test_hype_score_is_weighted_sum_and_clamped() -> None:
    assert sum(HYPE_WEIGHTS.values()) == pytest.approx(1.0)
    assert clamp01(2.5) == 1.0
    assert clamp01(-1) == 0.0

    full = compute_hype({name: 1.0 for name in HYPE_WEIGHTS})
    assert full.score == pytest.approx(1.0)
    assert compute_hype({}).score == 0.0

    partial = compute_hype({"motion": 0.5, "audio": 0.5})
    assert partial.score == pytest.approx(0.5 * 0.3 + 0.5 * 0.25)
    assert partial.contributions["face"] == 0.0
