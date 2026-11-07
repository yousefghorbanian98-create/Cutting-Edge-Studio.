"""Two-pass loudness normalisation (FFmpeg ``loudnorm``) and ducking rules."""

from __future__ import annotations

import re
from dataclasses import dataclass

#: Platform targets (LUFS integrated).
TARGETS: dict[str, float] = {
    "tiktok": -14.0,
    "instagram": -14.0,
    "youtube": -14.0,
    "broadcast": -23.0,
}
DEFAULT_TARGET = -14.0
#: True-peak ceiling used by the platform targets.
TP_TARGET = -1.5
#: ``loudnorm`` only honours ``linear=true`` when the measured LRA is non-zero; flat
#: material (tones, drones, a single mic) would silently fall back to dynamic mode and
#: miss the target by several dB, so those get an exact static gain instead.
FLAT_LRA = 0.1
_PAIR_PARSER = re.compile(
    r"input_i[^\d-]+(-?\d+\.?\d*)[^\d-]+input_tp[^\d-]+(-?\d+\.?\d*)[^\d-]+input_lra[^\d-]+(-?\d+\.?\d*)",
    re.DOTALL,
)
_HUMAN_PARSER = re.compile(
    r"Input Integrated:\s*(-?\d+\.?\d*).*?"
    r"Input True Peak:\s*(-?\d+\.?\d*).*?"
    r"Input LRA:\s*(-?\d+\.?\d*)",
    re.DOTALL,
)


@dataclass(frozen=True)
class LoudnessPlan:
    """Measured loudness plus the second-pass filter string."""

    filter_chain: str
    measured_i: float
    measured_tp: float
    measured_lra: float
    target: float
    mode: str = "linear"
    gain_db: float | None = None


def parse_loudnorm_block(stderr: str) -> dict[str, float] | None:
    """Extract ``input_i``/``input_tp``/``input_lra`` from FFmpeg's loudnorm output.

    Handles all three shapes FFmpeg emits: ``print_format=json`` (``"input_i" : "-19.42"``),
    ``print_format=summary`` in key=value form, and the human-readable summary block.
    """
    for parser in (_PAIR_PARSER, _HUMAN_PARSER):
        match = parser.search(stderr)
        if match is not None:
            integrated, true_peak, lra = match.groups()
            return {"i": float(integrated), "tp": float(true_peak), "lra": float(lra)}
    return None


def plan_loudness(
    measurement: dict[str, float], *, platform: str = "tiktok", offset: float = 0.0
) -> LoudnessPlan:
    """Second pass: linear normalisation with the measured values baked in."""
    target = TARGETS.get(platform, DEFAULT_TARGET)
    measured_i = float(measurement.get("i", target))
    measured_tp = float(measurement.get("tp", -1.5))
    measured_lra = float(measurement.get("lra", 11.0))
    if measured_lra <= FLAT_LRA:
        gain = target - measured_i
        gain = min(gain, TP_TARGET - measured_tp)  # never push the true peak over -1.5 dBTP
        chain = f"volume={gain:.2f}dB"
        if offset:
            chain = f"volume={offset:.2f}dB,{chain}"
        return LoudnessPlan(
            filter_chain=chain,
            measured_i=measured_i,
            measured_tp=measured_tp,
            measured_lra=measured_lra,
            target=target,
            mode="gain",
            gain_db=round(gain, 2),
        )
    chain = (
        f"loudnorm=I={target}:TP={TP_TARGET}:LRA=11:"
        f"measured_I={measured_i}:measured_TP={measured_tp}:measured_LRA={measured_lra}:"
        f"linear=true:print_format=summary"
    )
    if offset:
        chain = f"volume={offset:.2f}dB,{chain}"
    return LoudnessPlan(
        filter_chain=chain,
        measured_i=measured_i,
        measured_tp=measured_tp,
        measured_lra=measured_lra,
        target=target,
    )


def ducking_filter(music_volume: float = 0.35, voiced_volume: float = 1.0) -> str:
    """Sidechain-style ducking using ``amix`` weights (no compressor state to manage)."""
    music = max(0.0, min(1.0, music_volume))
    voice = max(0.0, min(1.0, voiced_volume))
    return (
        f"[0:a]volume={music:.2f}[music];[1:a]volume={voice:.2f}[voice];"
        "[music][voice]amix=inputs=2:duration=longest"
    )
