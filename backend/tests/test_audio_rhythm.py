"""Validation fixtures plus opt-in real librosa tests; no synthetic inference claims."""

from __future__ import annotations

import hashlib
import os
import socket
import wave

import numpy as np
import pytest
from app.services.audio import rhythm
from app.services.inference.registry import ModelUnavailableError


@pytest.fixture
def pcm(tmp_path):
    def create(samples=None, *, channels=1, rate=22050, width=2):
        path = tmp_path / "input.wav"
        data = np.zeros(rate * 3, dtype="<i2") if samples is None else samples
        with wave.open(str(path), "wb") as target:
            target.setnchannels(channels)
            target.setsampwidth(width)
            target.setframerate(rate)
            target.writeframes(data.tobytes())
        return path

    return create


@pytest.mark.parametrize("format_args", [{"channels": 2}, {"rate": 44100}, {"width": 1}])
def test_incompatible_wav_rejected_not_resampled_by_custom_code(pcm, format_args, caplog):
    with pytest.raises(ValueError, match="mono 16-bit PCM"):
        rhythm.analyze_pcm_wav(pcm(**format_args))
    assert "audio.rhythm.failed" in caplog.text


def test_input_too_short_is_not_given_an_invented_tempo(pcm):
    with pytest.raises(ValueError, match="1 to 600 seconds"):
        rhythm.analyze_pcm_wav(pcm(np.zeros(100, dtype="<i2")))


def test_oversized_declared_duration_rejected_before_read(monkeypatch, pcm):
    path = pcm()
    monkeypatch.setattr(wave.Wave_read, "getnframes", lambda _self: 22050 * 601)

    def forbidden(*_args: object):
        pytest.fail("Oversized PCM input must not be loaded into memory")

    monkeypatch.setattr(wave.Wave_read, "readframes", forbidden)
    with pytest.raises(ValueError, match="no silent truncation"):
        rhythm.analyze_pcm_wav(path)


def test_truncated_pcm_never_produces_rhythm(pcm):
    path = pcm()
    path.write_bytes(path.read_bytes()[:-4])
    with pytest.raises(ValueError, match="truncated"):
        rhythm.analyze_pcm_wav(path)


def test_missing_file_logs_and_raises(tmp_path, caplog):
    with pytest.raises(FileNotFoundError):
        rhythm.analyze_pcm_wav(tmp_path / "absent.wav")
    assert "audio.rhythm.failed" in caplog.text


def test_missing_optional_library_is_actionable_without_installing(monkeypatch, pcm, caplog):
    import builtins

    original = builtins.__import__

    def missing(name, *args: object, **kwargs: object):
        if name == "librosa":
            raise ImportError("Missing optional library")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing)
    with pytest.raises(ModelUnavailableError, match="build machine"):
        rhythm.analyze_pcm_wav(pcm())
    assert "audio.rhythm.dependency.unavailable" in caplog.text


def test_changed_input_rejected_even_after_an_estimator_returns(monkeypatch, pcm):
    path = pcm()

    def changed(_samples):
        path.write_bytes(b"changed while computing")
        return None, ()

    monkeypatch.setattr(rhythm, "_estimate", changed)
    with pytest.raises(ValueError, match="changed during analysis"):
        rhythm.analyze_pcm_wav(path)


def test_estimator_failure_is_not_replaced_with_default_beats(monkeypatch, pcm, caplog):
    def broken(_samples):
        raise RuntimeError("Estimator failed")

    monkeypatch.setattr(rhythm, "_estimate", broken)
    with pytest.raises(RuntimeError, match="Estimator failed"):
        rhythm.analyze_pcm_wav(pcm())
    assert "audio.rhythm.failed" in caplog.text


real_analysis = pytest.mark.skipif(
    os.environ.get("CE_ANALYSIS_TESTS") != "1",
    reason="Opt-in audited librosa environment; not a default packaged dependency",
)


@real_analysis
@pytest.mark.parametrize("bpm", [90, 120])
def test_real_librosa_estimates_owned_click_tracks_offline(pcm, monkeypatch, bpm):
    import librosa

    def blocked(*_args: object, **_kwargs: object):
        pytest.fail("Rhythm estimation must not connect to a network")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    times = np.arange(0.5, 11.5, 60 / bpm)
    samples = librosa.clicks(times=times, sr=22050, length=22050 * 12)
    path = pcm((samples * 30000).astype("<i2"))
    report = rhythm.analyze_pcm_wav(path)
    assert report.method == "librosa.beat.beat_track"
    assert report.scope == "audio-rhythm-only"
    assert report.library_version == "0.11.0"
    assert report.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert report.samples_analyzed == 22050 * 12
    assert report.duration_seconds == 12
    assert report.tempo_bpm == pytest.approx(bpm, abs=5)
    assert len(report.beat_times_seconds) > 10
    assert np.median(np.diff(report.beat_times_seconds)) == pytest.approx(60 / bpm, abs=0.04)


@real_analysis
def test_real_silence_returns_no_beats_and_no_fabricated_bpm(pcm):
    report = rhythm.analyze_pcm_wav(pcm())
    assert report.tempo_bpm is None
    assert report.beat_times_seconds == ()


@pytest.mark.parametrize(
    ("tempo", "beats"),
    [(float("nan"), [0.5]), (0, [0.5]), (120, [float("inf")]), (120, [-1]), (120, [5])],
)
def test_invalid_library_measurements_are_rejected(monkeypatch, pcm, tempo, beats):
    import sys
    from types import SimpleNamespace

    def fixture(**_kwargs: object):
        return np.array([tempo]), np.array(beats)

    monkeypatch.setitem(
        sys.modules, "librosa", SimpleNamespace(beat=SimpleNamespace(beat_track=fixture))
    )
    with pytest.raises(ValueError, match="invalid"):
        rhythm.analyze_pcm_wav(pcm())
