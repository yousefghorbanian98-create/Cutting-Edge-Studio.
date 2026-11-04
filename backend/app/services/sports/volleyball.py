"""Volleyball action rules: MMAction2 (Kinetics) labels mapped through geometry rules.

The classifier is deliberately *rule-based on top of OSS scores* (LOCK-00/LOCK-09):
no custom model, only a mapping table plus MediaPipe pose confirmation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.services.sports.pose_geometry import (
    Landmarks,
    elbow_angle,
    knee_angle,
    mean_visibility,
)

VolleyAction = Literal["spike", "block", "serve", "dig", "set", "pass", "unknown"]

#: Kinetics class name -> volleyball action hypothesis.
KINETICS_MAP: dict[str, VolleyAction] = {
    "jumping": "spike",
    "spiking a volleyball": "spike",
    "playing volleyball": "pass",
    "throwing": "serve",
    "serving a volleyball": "serve",
    "diving": "dig",
    "crouching": "set",
    "setting a volleyball": "set",
    "blocking": "block",
    "high jump": "block",
}

#: Minimum pose visibility before geometry is allowed to veto a model prediction.
MIN_VISIBILITY = 0.4
#: Confirmation threshold for the fused decision.
CONFIRM_THRESHOLD = 0.5


@dataclass(frozen=True)
class ActionDecision:
    """Fused decision with the evidence that produced it."""

    action: VolleyAction
    confidence: float
    evidence: tuple[str, ...]
    model_action: VolleyAction | None = None


def map_kinetics(scores: dict[str, float], *, top_k: int = 3) -> list[tuple[VolleyAction, float]]:
    """Aggregate Kinetics-400 scores into volleyball actions (best per action)."""
    aggregated: dict[VolleyAction, float] = {}
    for label, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)[
        : max(1, top_k)
    ]:
        action = KINETICS_MAP.get(label.lower())
        if action is None:
            continue
        aggregated[action] = max(aggregated.get(action, 0.0), float(score))
    return sorted(aggregated.items(), key=lambda item: item[1], reverse=True)


def _arms_forward(landmarks: Landmarks) -> bool:
    left = elbow_angle(landmarks, "left")
    right = elbow_angle(landmarks, "right")
    return (left is not None and right is not None) and max(left, right) > 120.0


def _hands_together(landmarks: Landmarks) -> bool:
    if len(landmarks) <= 16:
        return False
    left_wrist, right_wrist = landmarks[15], landmarks[16]
    left_shoulder = landmarks[11]
    span = abs(left_shoulder.x - landmarks[12].x) or 1e-6
    return abs(left_wrist.x - right_wrist.x) < span * 0.45


def _arms_overhead(landmarks: Landmarks) -> bool:
    if len(landmarks) <= 16:
        return False
    left_wrist, right_wrist = landmarks[15], landmarks[16]
    shoulders_y = (landmarks[11].y + landmarks[12].y) / 2
    return left_wrist.y < shoulders_y and right_wrist.y < shoulders_y


def _jumping(landmarks: Landmarks) -> bool:
    left = knee_angle(landmarks, "left")
    right = knee_angle(landmarks, "right")
    return (left is not None and right is not None) and max(left, right) > 150.0


def classify_action(scores: dict[str, float], landmarks: Landmarks | None = None) -> ActionDecision:
    """Fuse model scores with pose confirmation; ambiguous cases stay ``unknown``."""
    ranked = map_kinetics(scores)
    if not ranked:
        return ActionDecision(
            action="unknown", confidence=0.0, evidence=("no mapped kinetics label",)
        )

    evidence: list[str] = [f"model:{action}={score:.2f}" for action, score in ranked[:2]]
    model_action, model_score = ranked[0]

    if landmarks is None or len(landmarks) < 29 or mean_visibility(landmarks) < MIN_VISIBILITY:
        evidence.append("pose unavailable: using model score alone")
        return ActionDecision(
            action=model_action if model_score >= CONFIRM_THRESHOLD else "unknown",
            confidence=round(model_score, 3),
            evidence=tuple(evidence),
            model_action=model_action,
        )

    confirmations: dict[VolleyAction, bool] = {
        "spike": _jumping(landmarks) and _arms_overhead(landmarks),
        "block": _jumping(landmarks) and _arms_overhead(landmarks),
        "serve": _arms_overhead(landmarks),
        "dig": _arms_forward(landmarks),
        "set": _hands_together(landmarks),
        "pass": _arms_forward(landmarks),
        "unknown": False,
    }
    confirmed = confirmations.get(model_action, False)
    evidence.append(f"pose:{'confirms' if confirmed else 'contradicts'} {model_action}")

    if confirmed:
        confidence = min(1.0, model_score * 1.25)
        return ActionDecision(
            action=model_action,
            confidence=round(confidence, 3),
            evidence=tuple(evidence),
            model_action=model_action,
        )

    fallback = next(
        ((action, score) for action, score in ranked if confirmations.get(action)), None
    )
    if fallback is not None:
        action, score = fallback
        evidence.append(f"pose-priority fallback -> {action}")
        return ActionDecision(
            action=action,
            confidence=round(min(1.0, score * 0.9), 3),
            evidence=tuple(evidence),
            model_action=model_action,
        )

    return ActionDecision(
        action="unknown",
        confidence=round(model_score * 0.5, 3),
        evidence=tuple(evidence),
        model_action=model_action,
    )


@dataclass(frozen=True)
class Rally:
    """A continuous rally between serves."""

    start: float
    end: float
    touches: int

    @property
    def duration(self) -> float:
        return round(self.end - self.start, 3)


def detect_rallies(
    actions: list[tuple[float, VolleyAction]],
    *,
    gap_seconds: float = 6.0,
    min_touches: int = 2,
) -> list[Rally]:
    """Split an action timeline into rallies (a serve always starts a new one)."""
    rallies: list[Rally] = []
    current: list[tuple[float, VolleyAction]] = []

    def flush() -> None:
        if len(current) >= min_touches:
            rallies.append(Rally(start=current[0][0], end=current[-1][0], touches=len(current)))
        current.clear()

    for time, action in sorted(actions, key=lambda item: item[0]):
        if action == "serve" and current:
            flush()
        if current and time - current[-1][0] > gap_seconds:
            flush()
        current.append((time, action))

    flush()
    return rallies


def court_quad_from_lines(
    lines: list[tuple[tuple[float, float], tuple[float, float]]],
) -> list[tuple[float, float]]:
    """Approximate the court quad by intersecting the 4 longest detected lines.

    OpenCV's HoughLines supplies the segments; the intersection math stays here so it is
    unit-testable without a video frame.
    """
    if len(lines) < 4:
        msg = "at least 4 lines are required to build a court quad"
        raise ValueError(msg)

    def length(line: tuple[tuple[float, float], tuple[float, float]]) -> float:
        (x1, y1), (x2, y2) = line
        return float(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5)

    def intersect(
        first: tuple[tuple[float, float], tuple[float, float]],
        second: tuple[tuple[float, float], tuple[float, float]],
    ) -> tuple[float, float] | None:
        (x1, y1), (x2, y2) = first
        (x3, y3), (x4, y4) = second
        denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denominator) < 1e-9:
            return None
        a = x1 * y2 - y1 * x2
        b = x3 * y4 - y3 * x4
        px = (a * (x3 - x4) - (x1 - x2) * b) / denominator
        py = (a * (y3 - y4) - (y1 - y2) * b) / denominator
        return (round(px, 2), round(py, 2))

    strongest = sorted(lines, key=length, reverse=True)[:4]
    corners: list[tuple[float, float]] = []
    for index, line in enumerate(strongest):
        for other in strongest[index + 1 :]:
            point = intersect(line, other)
            if point is not None and point not in corners:
                corners.append(point)
    return corners[:4]
