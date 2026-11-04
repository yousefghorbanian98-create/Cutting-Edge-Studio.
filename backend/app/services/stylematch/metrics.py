"""The five acceptance metrics from G12 (Golden Set evaluation for P6)."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy import stats


def _as_array(values: list[float]) -> np.ndarray:
    return np.asarray(values, dtype=float) if values else np.asarray([], dtype=float)


def cut_length_ks(generated: list[float], reference: list[float]) -> dict[str, Any]:
    """Metric 1 — KS-test between cut-length distributions (pass: p > 0.05)."""
    if len(generated) < 2 or len(reference) < 2:
        return {"metric": "cut_length_ks", "passed": False, "value": 0.0, "note": "not enough cuts"}
    result = stats.ks_2samp(_as_array(generated), _as_array(reference))
    return {
        "metric": "cut_length_ks",
        "passed": bool(result.pvalue > 0.05),
        "value": round(float(result.pvalue), 4),
        "statistic": round(float(result.statistic), 4),
        "note": "p > 0.05 means the distributions are statistically similar",
    }


def shot_type_f1(confusion: dict[str, dict[str, int]]) -> dict[str, Any]:
    """Metric 2 — macro F1 of predicted vs ground-truth shot types."""
    labels = sorted({*confusion, *{pred for row in confusion.values() for pred in row}})
    if not labels:
        return {"metric": "shot_type_f1", "passed": False, "value": 0.0, "note": "no labels"}
    per_label: dict[str, float] = {}
    for label in labels:
        true_positive = float(confusion.get(label, {}).get(label, 0))
        predicted = sum(confusion.get(truth, {}).get(label, 0) for truth in labels)
        actual = sum(confusion.get(label, {}).values())
        precision = true_positive / predicted if predicted else 0.0
        recall = true_positive / actual if actual else 0.0
        per_label[label] = (
            2 * precision * recall / (precision + recall) if precision + recall else 0.0
        )
    macro = float(np.mean(list(per_label.values())))
    return {
        "metric": "shot_type_f1",
        "passed": macro >= 0.6,
        "value": round(macro, 4),
        "per_label": {label: round(score, 3) for label, score in per_label.items()},
        "note": "macro F1 over CLIP zero-shot shot types",
    }


def beat_alignment(cuts: list[float], beats: list[float]) -> dict[str, Any]:
    """Metric 3 — mean distance (ms) from each cut to the nearest beat (pass: < 100 ms)."""
    if not cuts or not beats:
        return {
            "metric": "beat_alignment",
            "passed": False,
            "value": None,
            "note": "missing cuts or beats",
        }
    ordered = sorted(beats)
    distances = []
    for cut in cuts:
        nearest = min(ordered, key=lambda beat: abs(beat - cut))
        distances.append(abs(nearest - cut))
    mean_ms = float(np.mean(distances)) * 1000.0
    return {
        "metric": "beat_alignment",
        "passed": bool(mean_ms < 100.0),
        "value": round(mean_ms, 2),
        "unit": "ms",
        "note": "mean distance from cut to the closest beat",
    }


def pacing_similarity(generated: list[float], reference: list[float]) -> dict[str, Any]:
    """Metric 4 — Pearson correlation of the two pacing curves (pass: r > 0.7)."""
    if len(generated) < 2 or len(reference) < 2:
        return {
            "metric": "pacing_similarity",
            "passed": False,
            "value": 0.0,
            "note": "curve too short",
        }
    length = min(len(generated), len(reference))
    left = _as_array(generated[:length])
    right = _as_array(reference[:length])
    if float(np.std(left)) == 0.0 or float(np.std(right)) == 0.0:
        return {"metric": "pacing_similarity", "passed": False, "value": 0.0, "note": "flat curve"}
    correlation = float(np.corrcoef(left, right)[0, 1])
    return {
        "metric": "pacing_similarity",
        "passed": bool(correlation > 0.7),
        "value": round(correlation, 4),
        "note": "Pearson correlation of energy over time",
    }


def _srgb_to_lab(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    def linearize(channel: float) -> float:
        value = channel / 255.0
        return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4

    red, green, blue = (linearize(channel) for channel in rgb)
    x = red * 0.4124 + green * 0.3576 + blue * 0.1805
    y = red * 0.2126 + green * 0.7152 + blue * 0.0722
    z = red * 0.0193 + green * 0.1192 + blue * 0.9505

    def f(value: float) -> float:
        return value ** (1 / 3) if value > 0.008856 else 7.787 * value + 16 / 116

    fx, fy, fz = f(x / 0.95047), f(y / 1.0), f(z / 1.08883)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def color_delta_e(generated: dict[str, float], reference: dict[str, float]) -> dict[str, Any]:
    """Metric 5 — CIE76 ΔE between the average colours (pass: ΔE < 10)."""
    try:
        left = _srgb_to_lab((generated["r"], generated["g"], generated["b"]))
        right = _srgb_to_lab((reference["r"], reference["g"], reference["b"]))
    except KeyError:
        return {"metric": "color_delta_e", "passed": False, "value": None, "note": "missing rgb"}
    delta = math.dist(left, right)
    return {
        "metric": "color_delta_e",
        "passed": bool(delta < 10.0),
        "value": round(delta, 2),
        "note": "CIE76 ΔE of the duration-weighted average colour",
    }


def evaluate_match(results: dict[str, dict[str, Any]], *, required: int = 3) -> dict[str, Any]:
    """Aggregate the five metrics: the match passes when at least ``required`` pass."""
    passed = [name for name, result in results.items() if result.get("passed")]
    return {
        "passed": len(passed) >= required,
        "passed_count": len(passed),
        "required": required,
        "metrics": results,
    }
