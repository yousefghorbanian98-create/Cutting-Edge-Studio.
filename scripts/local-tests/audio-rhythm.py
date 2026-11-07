"""Real OSS rhythm evidence from owned synthetic clicks; no API/job/UI claim.

Run from backend with its audited analysis environment:
CE_ANALYSIS_TESTS=1 PYTHONPATH=. .venv/bin/python ../scripts/local-tests/audio-rhythm.py
Temporary WAVs are not committed. Library estimation, not a hand-written detector.
"""

import hashlib
import json
import socket
import tempfile
import wave
from dataclasses import asdict
from pathlib import Path

import librosa
import numpy as np
from app.services.audio.rhythm import SAMPLE_RATE, analyze_pcm_wav

OUT = Path(__file__).resolve().parents[2] / "docs/evidence/recovery-r2b1"


def offline(*_args: object, **_kwargs: object) -> None:
    raise RuntimeError("Unexpected network connection during local rhythm estimation")


socket.socket.connect = offline
reports = []
with tempfile.TemporaryDirectory(prefix="ce-rhythm-") as directory:
    for bpm in (90, 120, None):
        signal = (
            librosa.clicks(times=np.arange(0.5, 11.5, 60 / bpm), sr=SAMPLE_RATE, length=SAMPLE_RATE * 12)
            if bpm else np.zeros(SAMPLE_RATE * 12)
        )
        path = Path(directory) / f"owned-clicks-{bpm}.wav"
        with wave.open(str(path), "wb") as target:
            target.setnchannels(1)
            target.setsampwidth(2)
            target.setframerate(SAMPLE_RATE)
            target.writeframes((signal * 30000).astype("<i2").tobytes())
        report = analyze_pcm_wav(path)
        assert report.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
        if bpm is None:
            assert report.tempo_bpm is None and report.beat_times_seconds == ()
        else:
            assert abs(report.tempo_bpm - bpm) < 5
            assert len(report.beat_times_seconds) > 10
        reports.append({"expected_fixture_bpm": bpm, "measurement": asdict(report)})
        print(f"PASS owned fixture {bpm}: estimated={report.tempo_bpm}, beats={len(report.beat_times_seconds)}")
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "real-rhythm-results.json").write_text(json.dumps(reports, indent=2) + "\n")
