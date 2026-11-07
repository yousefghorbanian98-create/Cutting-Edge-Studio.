"""Bodybuilding geometry rules on synthetic landmarks."""

from __future__ import annotations

import math

import pytest
from app.services.sports.pose_geometry import (
    Landmark,
    angle_deg,
    count_reps,
    detect_pose_type,
    elbow_angle,
    is_peak_contraction,
    joint_summary,
    knee_angle,
    mean_visibility,
    shoulder_abduction,
    symmetry_score,
    time_under_tension,
)


def skeleton(overrides: dict[int, Landmark] | None = None) -> list[Landmark]:
    """Neutral standing pose; overrides use landmark indices as keys."""
    landmarks = [Landmark(0.5, 0.5) for _ in range(33)]
    landmarks[11] = Landmark(0.42, 0.30)  # left shoulder
    landmarks[12] = Landmark(0.58, 0.30)  # right shoulder
    landmarks[13] = Landmark(0.40, 0.42)  # left elbow
    landmarks[14] = Landmark(0.60, 0.42)  # right elbow
    landmarks[15] = Landmark(0.40, 0.55)  # left wrist
    landmarks[16] = Landmark(0.60, 0.55)  # right wrist
    landmarks[23] = Landmark(0.45, 0.60)  # left hip
    landmarks[24] = Landmark(0.55, 0.60)  # right hip
    landmarks[25] = Landmark(0.45, 0.75)  # left knee
    landmarks[26] = Landmark(0.55, 0.75)  # right knee
    landmarks[27] = Landmark(0.45, 0.90)  # left ankle
    landmarks[28] = Landmark(0.55, 0.90)  # right ankle
    for index, landmark in (overrides or {}).items():
        landmarks[index] = landmark
    return landmarks


def test_angle_math_and_guards() -> None:
    a, b, c = Landmark(0, 1), Landmark(0, 0), Landmark(1, 0)
    assert angle_deg(a, b, c) == pytest.approx(90.0)
    assert angle_deg(a, None, c) is None
    assert angle_deg(Landmark(0, 0), Landmark(0, 0), Landmark(1, 1)) is None


def test_straight_arm_is_180_degrees() -> None:
    landmarks = skeleton({13: Landmark(0.42, 0.45), 15: Landmark(0.42, 0.60)})
    assert elbow_angle(landmarks, "left") == pytest.approx(180.0, abs=1.0)


def test_joint_summary_and_knees() -> None:
    summary = joint_summary(skeleton())
    assert set(summary) == {
        "left_elbow",
        "right_elbow",
        "left_shoulder",
        "right_shoulder",
        "left_knee",
        "right_knee",
    }
    assert knee_angle(skeleton(), "left") == pytest.approx(180.0, abs=1.0)
    assert mean_visibility(skeleton()) == pytest.approx(1.0)


def test_peak_contraction_detects_curl_and_lateral() -> None:
    assert is_peak_contraction(build_pose(20, 30), exercise="curl") is True
    assert is_peak_contraction(build_pose(165, 170), exercise="lateral") is True
    assert is_peak_contraction(build_pose(20, 170), exercise="auto") is False


def build_pose(
    abduction_left: float,
    elbow_left: float,
    abduction_right: float | None = None,
    elbow_right: float | None = None,
    *,
    shoulders: tuple[float, float] = (0.42, 0.58),
    hips: tuple[float, float] = (0.45, 0.55),
) -> list[Landmark]:
    """Build a skeleton from *angles* so the tests assert semantics, not coordinates."""
    landmarks = [Landmark(0.5, 0.5) for _ in range(33)]
    landmarks[11] = Landmark(shoulders[0], 0.30)
    landmarks[12] = Landmark(shoulders[1], 0.30)
    landmarks[23] = Landmark(hips[0], 0.60)
    landmarks[24] = Landmark(hips[1], 0.60)
    landmarks[25] = Landmark(0.45, 0.75)
    landmarks[26] = Landmark(0.55, 0.75)
    landmarks[27] = Landmark(0.45, 0.90)
    landmarks[28] = Landmark(0.55, 0.90)

    def place(side: str, abduction: float, elbow: float) -> None:
        mirror = -1.0 if side == "left" else 1.0
        hip_index, shoulder_index, elbow_index, wrist_index = (
            (23, 11, 13, 15) if side == "left" else (24, 12, 14, 16)
        )
        hip, shoulder = landmarks[hip_index], landmarks[shoulder_index]
        down = _unit((hip.x - shoulder.x, hip.y - shoulder.y))
        elbow_dir = _rotate(down, mirror * abduction)
        elbow_point = Landmark(shoulder.x + 0.16 * elbow_dir[0], shoulder.y + 0.16 * elbow_dir[1])
        back = _unit((shoulder.x - elbow_point.x, shoulder.y - elbow_point.y))
        wrist_dir = _rotate(back, -mirror * elbow)
        landmarks[elbow_index] = elbow_point
        landmarks[wrist_index] = Landmark(
            elbow_point.x + 0.14 * wrist_dir[0],
            elbow_point.y + 0.14 * wrist_dir[1],
        )

    place("left", abduction_left, elbow_left)
    place("right", abduction_right or abduction_left, elbow_right or elbow_left)
    return landmarks


def _rotate(vector: tuple[float, float], degrees: float) -> tuple[float, float]:
    radians = math.radians(degrees)
    x, y = vector
    return (
        x * math.cos(radians) - y * math.sin(radians),
        x * math.sin(radians) + y * math.cos(radians),
    )


def _unit(vector: tuple[float, float]) -> tuple[float, float]:
    norm = math.hypot(*vector) or 1.0
    return (vector[0] / norm, vector[1] / norm)


def test_pose_detection_rules() -> None:
    assert detect_pose_type(build_pose(20, 170)) == "relaxed"
    assert detect_pose_type(build_pose(165, 170)) == "lateral_spread"
    assert detect_pose_type(build_pose(130, 55)) == "front_double_bicep"
    assert detect_pose_type(build_pose(75, 70)) == "front_lat_spread"
    assert (
        detect_pose_type(build_pose(45, 40, 120, 120, shoulders=(0.47, 0.53), hips=(0.40, 0.60)))
        == "side_chest"
    )
    assert detect_pose_type(build_pose(20, 30)) in {"unknown", "relaxed"}

    low_visibility = [Landmark(0.5, 0.5, 0.0, 0.1) for _ in range(33)]
    assert detect_pose_type(low_visibility) == "unknown"
    assert detect_pose_type([Landmark(0.5, 0.5)]) == "unknown"


def test_symmetry_score() -> None:
    assert symmetry_score(skeleton()) == pytest.approx(1.0)
    asymmetric = skeleton({13: Landmark(0.48, 0.20), 15: Landmark(0.50, 0.10)})
    assert symmetry_score(asymmetric) < 0.99
    assert symmetry_score([Landmark(0.5, 0.5)]) is None


def test_rep_counting_and_tempo() -> None:
    first_rep = [160, 150, 120, 80, 45, 30, 60, 110, 155, 150]
    second_rep = [130, 90, 40, 35, 70, 120, 158, 160, 160, 160]
    series = first_rep + second_rep
    reps = count_reps(series, fps=10)
    assert len(reps) == 2
    assert reps[0] < reps[1]

    assert count_reps([], fps=10) == []
    assert count_reps([90, 90, 90], fps=10) == []
    assert count_reps(series, fps=0) == []

    tempo = time_under_tension(reps, fps=10)
    assert tempo["rep_count"] == 2.0
    assert tempo["total_seconds"] > 0
    assert time_under_tension([], fps=30)["total_seconds"] == 0.0


def test_shoulder_abduction_increases_with_raised_arm() -> None:
    down = shoulder_abduction(skeleton(), "left")
    up = shoulder_abduction(skeleton({13: Landmark(0.40, 0.16), 15: Landmark(0.40, 0.02)}), "left")
    assert down is not None
    assert up is not None
    assert up > down
