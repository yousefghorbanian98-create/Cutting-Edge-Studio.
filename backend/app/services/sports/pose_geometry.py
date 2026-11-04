"""Bodybuilding rules on top of MediaPipe pose landmarks (no custom model, LOCK-00).

All functions are pure: landmarks in, numbers out. The thresholds come from the protocol
(§9) and are exposed as constants so they can be calibrated later without touching logic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy.signal import find_peaks

# MediaPipe BlazePose 33-landmark indices (subset we use).
LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_ELBOW = 13
RIGHT_ELBOW = 14
LEFT_WRIST = 15
RIGHT_WRIST = 16
LEFT_HIP = 23
RIGHT_HIP = 24
LEFT_KNEE = 25
RIGHT_KNEE = 26
LEFT_ANKLE = 27
RIGHT_ANKLE = 28

#: Protocol thresholds (§9 bodybuilding).
PEAK_CONTRACTION_ELBOW_DEG = 35.0
LATERAL_SHOULDER_DEG = 160.0
FLEXED_ELBOW_DEG = 80.0
EXTENDED_ELBOW_DEG = 150.0

PoseType = Literal[
    "front_double_bicep",
    "back_double_bicep",
    "side_chest",
    "lateral_spread",
    "front_lat_spread",
    "relaxed",
    "unknown",
]


@dataclass(frozen=True)
class Landmark:
    """One pose landmark in normalized image coordinates."""

    x: float
    y: float
    z: float = 0.0
    visibility: float = 1.0


Landmarks = list[Landmark]


def _point(landmarks: Landmarks, index: int) -> Landmark | None:
    if 0 <= index < len(landmarks):
        return landmarks[index]
    return None


def angle_deg(a: Landmark | None, b: Landmark | None, c: Landmark | None) -> float | None:
    """Angle ABC in degrees using xy only (z is noisy on a single camera)."""
    if a is None or b is None or c is None:
        return None
    vector_ba = (a.x - b.x, a.y - b.y)
    vector_bc = (c.x - b.x, c.y - b.y)
    norm_ba = math.hypot(*vector_ba)
    norm_bc = math.hypot(*vector_bc)
    if norm_ba == 0 or norm_bc == 0:
        return None
    cosine = (vector_ba[0] * vector_bc[0] + vector_ba[1] * vector_bc[1]) / (norm_ba * norm_bc)
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def elbow_angle(landmarks: Landmarks, side: Literal["left", "right"]) -> float | None:
    """Shoulder-elbow-wrist angle for one side."""
    shoulder, elbow, wrist = (
        (LEFT_SHOULDER, LEFT_ELBOW, LEFT_WRIST)
        if side == "left"
        else (
            RIGHT_SHOULDER,
            RIGHT_ELBOW,
            RIGHT_WRIST,
        )
    )
    return angle_deg(
        _point(landmarks, shoulder), _point(landmarks, elbow), _point(landmarks, wrist)
    )


def shoulder_abduction(landmarks: Landmarks, side: Literal["left", "right"]) -> float | None:
    """Hip-shoulder-elbow angle: ~0 arms down, ~180 arms straight overhead."""
    hip, shoulder, elbow = (
        (LEFT_HIP, LEFT_SHOULDER, LEFT_ELBOW)
        if side == "left"
        else (
            RIGHT_HIP,
            RIGHT_SHOULDER,
            RIGHT_ELBOW,
        )
    )
    return angle_deg(_point(landmarks, hip), _point(landmarks, shoulder), _point(landmarks, elbow))


def knee_angle(landmarks: Landmarks, side: Literal["left", "right"]) -> float | None:
    """Hip-knee-ankle angle for one side."""
    hip, knee, ankle = (
        (LEFT_HIP, LEFT_KNEE, LEFT_ANKLE)
        if side == "left"
        else (
            RIGHT_HIP,
            RIGHT_KNEE,
            RIGHT_ANKLE,
        )
    )
    return angle_deg(_point(landmarks, hip), _point(landmarks, knee), _point(landmarks, ankle))


def joint_summary(landmarks: Landmarks) -> dict[str, float | None]:
    """All angles the rule engine needs, in one dict."""
    return {
        "left_elbow": elbow_angle(landmarks, "left"),
        "right_elbow": elbow_angle(landmarks, "right"),
        "left_shoulder": shoulder_abduction(landmarks, "left"),
        "right_shoulder": shoulder_abduction(landmarks, "right"),
        "left_knee": knee_angle(landmarks, "left"),
        "right_knee": knee_angle(landmarks, "right"),
    }


def mean_visibility(landmarks: Landmarks) -> float:
    """Average visibility of the landmarks we depend on (confidence gate)."""
    used = [LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_ELBOW, RIGHT_ELBOW, LEFT_HIP, RIGHT_HIP]
    values = [landmarks[index].visibility for index in used if index < len(landmarks)]
    return float(np.mean(values)) if values else 0.0


def is_peak_contraction(
    landmarks: Landmarks, *, exercise: Literal["curl", "lateral", "auto"] = "auto"
) -> bool:
    """Return True when the pose is at peak contraction (protocol §9)."""
    left_elbow = elbow_angle(landmarks, "left")
    right_elbow = elbow_angle(landmarks, "right")
    left_shoulder = shoulder_abduction(landmarks, "left")
    right_shoulder = shoulder_abduction(landmarks, "right")

    curl = any(
        angle is not None and angle < PEAK_CONTRACTION_ELBOW_DEG
        for angle in (left_elbow, right_elbow)
    )
    lateral = any(
        angle is not None and angle > LATERAL_SHOULDER_DEG
        for angle in (left_shoulder, right_shoulder)
    )
    if exercise == "curl":
        return curl
    if exercise == "lateral":
        return lateral
    return curl or lateral


def detect_pose_type(landmarks: Landmarks) -> PoseType:  # noqa: PLR0911 - rule table reads best as early returns
    """Classify a bodybuilding pose from joint geometry (rule-based, no training)."""
    if len(landmarks) <= RIGHT_HIP or mean_visibility(landmarks) < 0.5:
        return "unknown"

    left_elbow, right_elbow = elbow_angle(landmarks, "left"), elbow_angle(landmarks, "right")
    left_shoulder, right_shoulder = (
        shoulder_abduction(landmarks, "left"),
        shoulder_abduction(landmarks, "right"),
    )
    left_wrist, right_wrist = _point(landmarks, LEFT_WRIST), _point(landmarks, RIGHT_WRIST)
    left_shoulder_pt, right_shoulder_pt = (
        _point(landmarks, LEFT_SHOULDER),
        _point(landmarks, RIGHT_SHOULDER),
    )
    left_hip_pt, right_hip_pt = _point(landmarks, LEFT_HIP), _point(landmarks, RIGHT_HIP)
    if None in (left_elbow, right_elbow, left_shoulder, right_shoulder, left_wrist, right_wrist):
        return "unknown"
    assert left_elbow is not None
    assert right_elbow is not None
    assert left_shoulder is not None
    assert right_shoulder is not None
    assert left_wrist is not None
    assert right_wrist is not None
    assert left_shoulder_pt is not None
    assert right_shoulder_pt is not None
    assert left_hip_pt is not None
    assert right_hip_pt is not None

    both_flexed = left_elbow < FLEXED_ELBOW_DEG and right_elbow < FLEXED_ELBOW_DEG
    both_high = left_wrist.y < left_shoulder_pt.y and right_wrist.y < right_shoulder_pt.y
    arms_wide = left_shoulder > 120.0 and right_shoulder > 120.0

    if both_flexed and both_high and arms_wide:
        wrists_behind = (left_wrist.z + right_wrist.z) / 2 > (
            left_shoulder_pt.z + right_shoulder_pt.z
        ) / 2
        return "back_double_bicep" if wrists_behind else "front_double_bicep"

    # Hands on hips / lat spread: flexed arms flared out at a moderate angle.
    moderate_flare = min(left_shoulder, right_shoulder) > 60.0
    moderate_flare = moderate_flare and max(left_shoulder, right_shoulder) < 120.0
    if both_flexed and moderate_flare:
        return "front_lat_spread"

    if (
        left_shoulder > LATERAL_SHOULDER_DEG
        and right_shoulder > LATERAL_SHOULDER_DEG
        and left_elbow > EXTENDED_ELBOW_DEG
        and right_elbow > EXTENDED_ELBOW_DEG
    ):
        return "lateral_spread"

    shoulder_width = abs(left_shoulder_pt.x - right_shoulder_pt.x)
    hip_width = abs(left_hip_pt.x - right_hip_pt.x)
    narrow_shoulders = shoulder_width < hip_width * 1.15
    one_flexed = min(left_elbow, right_elbow) < FLEXED_ELBOW_DEG < max(left_elbow, right_elbow)
    if narrow_shoulders and one_flexed:
        return "side_chest"

    if left_elbow > EXTENDED_ELBOW_DEG and right_elbow > EXTENDED_ELBOW_DEG and not arms_wide:
        return "relaxed"

    return "unknown"


def symmetry_score(landmarks: Landmarks) -> float | None:
    """1.0 = perfectly symmetric, 0.0 = maximally asymmetric (left vs right angles)."""
    pairs = [
        (elbow_angle(landmarks, "left"), elbow_angle(landmarks, "right")),
        (shoulder_abduction(landmarks, "left"), shoulder_abduction(landmarks, "right")),
    ]
    diffs = [abs(left - right) for left, right in pairs if left is not None and right is not None]
    if not diffs:
        return None
    return max(0.0, 1.0 - (float(np.mean(diffs)) / 180.0))


def count_reps(
    angle_series: list[float],
    fps: float,
    *,
    min_prominence_deg: float = 20.0,
    min_gap_seconds: float = 0.8,
    top_fraction: float = 0.35,
) -> list[int]:
    """Rep boundaries from a joint-angle series (``scipy.signal.find_peaks``, OSS only).

    Contractions are the minima of the angle signal; each detected trough is one rep.
    Returns the indices of the troughs.
    """
    if fps <= 0 or len(angle_series) < 3:
        return []
    signal = -np.asarray(angle_series, dtype=float)
    distance = max(1, int(round(min_gap_seconds * fps)))
    peaks, _ = find_peaks(signal, prominence=min_prominence_deg, distance=distance)
    if peaks.size == 0:
        return []
    threshold = float(np.min(signal) + (np.max(signal) - np.min(signal)) * top_fraction)
    return [int(index) for index in peaks if signal[index] >= threshold]


def time_under_tension(reps: list[int], fps: float) -> dict[str, float]:
    """Rep tempo summary: total seconds under tension and mean seconds per rep."""
    if not reps or fps <= 0:
        return {"total_seconds": 0.0, "seconds_per_rep": 0.0, "rep_count": 0.0}
    span = (reps[-1] - reps[0]) / fps
    count = len(reps)
    return {
        "total_seconds": round(span, 2),
        "seconds_per_rep": round(span / count, 2) if count else 0.0,
        "rep_count": float(count),
    }
