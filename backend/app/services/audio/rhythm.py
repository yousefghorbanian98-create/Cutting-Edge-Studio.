"""WAV-to-librosa glue, not a new beat detector or a pretrained sports model.

Experimental adapter only: not mounted as an API, job, or completed wizard stage.
Provision and audit optional analysis dependencies at build time; never download here.
"""

from __future__ import annotations

import hashlib
import math
import wave
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path

import numpy as np

from app.logging import get_logger
from app.services.inference.registry import ModelUnavailableError

LOG = get_logger(__name__)
SAMPLE_RATE = 22050
MAX_SECONDS = 600


@dataclass(frozen=True)
class RhythmMeasurement:
    """Estimated rhythm from one PCM WAV, not verified musical ground truth or EDL."""

    sha256: str
    samples_analyzed: int
    duration_seconds: float
    tempo_bpm: float | None
    beat_times_seconds: tuple[float, ...]
    library_version: str
    method: str = "librosa.beat.beat_track"
    scope: str = "audio-rhythm-only"


def _read_pcm(path: Path) -> np.ndarray:
    """Use the standard WAV reader; conversion/resampling belongs to approved FFmpeg."""
    with wave.open(str(path), "rb") as source:
        if (source.getnchannels(), source.getsampwidth(), source.getframerate()) != (
            1,
            2,
            SAMPLE_RATE,
        ) or source.getcomptype() != "NONE":
            raise ValueError("Expected uncompressed mono 16-bit PCM WAV at 22050 Hz")
        frames = source.getnframes()
        if not SAMPLE_RATE <= frames <= MAX_SECONDS * SAMPLE_RATE:
            raise ValueError("Audio rhythm analysis accepts 1 to 600 seconds; no silent truncation")
        raw = source.readframes(frames)
        if len(raw) != frames * 2:
            raise ValueError("PCM WAV is truncated; no rhythm result was produced")
    return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0


def _estimate(samples: np.ndarray) -> tuple[float | None, tuple[float, ...]]:
    try:
        import librosa
    except ImportError as error:
        LOG.error("audio.rhythm.dependency.unavailable", error=str(error))
        raise ModelUnavailableError(
            "Audio rhythm requires the audited librosa 0.11.0 analysis environment. "
            "Provision it on the build machine; no runtime installation is performed."
        ) from error
    tempo, beats = librosa.beat.beat_track(y=samples, sr=SAMPLE_RATE, units="time")
    times = tuple(float(value) for value in beats)
    if not times:
        return None, ()
    bpm = float(np.asarray(tempo).item())
    if not math.isfinite(bpm) or bpm <= 0:
        raise ValueError("Beat estimator returned an invalid tempo")
    if any(not math.isfinite(t) or not 0 <= t <= len(samples) / SAMPLE_RATE for t in times):
        raise ValueError("Beat estimator returned invalid timestamps")
    return bpm, times


def _measure(path: Path) -> RhythmMeasurement:
    before = path.stat()
    samples = _read_pcm(path)
    with path.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    tempo, beats = _estimate(samples)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        raise ValueError("Audio changed during analysis; run again")
    return RhythmMeasurement(
        sha256=digest,
        samples_analyzed=len(samples),
        duration_seconds=len(samples) / SAMPLE_RATE,
        tempo_bpm=tempo,
        beat_times_seconds=beats,
        library_version=version("librosa"),
    )


def analyze_pcm_wav(path: Path) -> RhythmMeasurement:
    """Delegate rhythm estimation to librosa, with bounded PCM input and file provenance.

    This synchronous library adapter must not run on an API thread. Experimental
    project jobs invoke it through the cancellable/deadlined worker process.
    """
    try:
        result = _measure(path)
    except Exception as error:
        LOG.error("audio.rhythm.failed", path=str(path), error=str(error))
        raise
    LOG.info(
        "audio.rhythm.measured",
        samples=result.samples_analyzed,
        beats=len(result.beat_times_seconds),
        tempo_bpm=result.tempo_bpm,
    )
    return result
