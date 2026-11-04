"""PCM/worker boundary and resource guards using explicitly simulated commands."""

from __future__ import annotations

import hashlib
import sys
import threading
import wave
from importlib.metadata import PackageNotFoundError
from pathlib import Path

import pytest
from app.services.audio.processor import (
    FFmpegRhythmInspector,
    pcm_command,
    rhythm_unavailable,
    worker_command,
)
from app.services.media.ffmpeg import FFmpegBinaries
from app.services.media.runner import CommandCancelledError, CommandResult
from tests.test_rhythm_jobs import estimate


def test_pcm_command_and_frozen_dispatch_do_not_invoke_encoders_or_server(tmp_path, monkeypatch):
    binaries = FFmpegBinaries(Path("ffmpeg"), Path("ffprobe"))
    wav, result = tmp_path / "audio.wav", tmp_path / "result.json"
    command = pcm_command(binaries, tmp_path / "space name.mp4", wav)
    assert command[command.index("-map") + 1] == "0:a:0"
    assert command[command.index("-t") + 1] == "601"
    assert command[command.index("-c:a") + 1] == "pcm_s16le"
    assert "264" not in " ".join(command)
    assert worker_command(wav, result)[1:3] == ["-m", "app.services.audio.worker"]
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert worker_command(wav, result) == [
        sys.executable,
        "--audio-rhythm-worker",
        str(wav),
        str(result),
    ]


@pytest.mark.parametrize("installed", ["missing", "0.12.0"])
def test_dependency_gate_has_actionable_no_download_reason(settings, monkeypatch, installed):
    settings.audio_rhythm_enabled = True

    def version(_):
        if installed == "missing":
            raise PackageNotFoundError("librosa")
        return installed

    monkeypatch.setattr("app.services.audio.processor.version", version)
    assert rhythm_unavailable(settings)
    settings.audio_rhythm_enabled = False
    assert "no runtime installation or download" in rhythm_unavailable(settings)


@pytest.mark.parametrize(
    "fault", [None, "digest", "samples", "json", "oversize", "cancel", "timeout", "duration"]
)
def test_extraction_worker_validation_and_temporary_cleanup(settings, monkeypatch, fault):
    settings.cache_dir.mkdir(parents=True)
    binaries = FFmpegBinaries(Path("ffmpeg"), Path("ffprobe"))
    calls = []
    progress = []

    def command(args, **kwargs: object):
        calls.append((args, kwargs))
        if args[0] == "ffmpeg":
            with wave.open(str(args[-1]), "wb") as pcm:
                pcm.setnchannels(1)
                pcm.setsampwidth(2)
                pcm.setframerate(22050)
                pcm.writeframes(b"\0\0" * 44100)
        else:
            if fault == "cancel":
                raise CommandCancelledError("Fixture cancellation")
            if fault == "timeout":
                raise TimeoutError("Fixture timeout")
            wav, result = Path(args[-2]), Path(args[-1])
            changes = {"sha256": hashlib.sha256(wav.read_bytes()).hexdigest()}
            if fault == "digest":
                changes["sha256"] = "b" * 64
            if fault == "samples":
                changes.update(samples_analyzed=66150, duration_seconds=3)
            payload = estimate(**changes).model_dump_json()
            if fault == "json":
                payload = "{}"
            if fault == "oversize":
                payload = " " * (2 * 1024 * 1024 + 1)
            result.write_text(payload)
        return CommandResult(0, "", "")

    monkeypatch.setattr("app.services.audio.processor.run_command", command)
    inspector = FFmpegRhythmInspector(settings)

    def run():
        return inspector.estimate_pcm(
            binaries,
            Path("owned-fixture.mp4"),
            1 if fault == "duration" else 2,
            threading.Event(),
            progress.append,
        )

    if fault:
        with pytest.raises((ValueError, CommandCancelledError, TimeoutError)):
            run()
    else:
        measured = run()
        assert measured.samples_analyzed == 44100
        assert measured.tempo_bpm == 120  # injected fixture, not a real algorithm assertion
    assert list(settings.cache_dir.iterdir()) == []
    assert progress == [50]  # no fabricated percentage during library work
    assert calls[0][1]["timeout"] == 120
    assert calls[1][1]["timeout"] == 180
    assert calls[1][1]["env"]["NUMBA_NUM_THREADS"] == "1"
    assert calls[1][1]["env"]["OPENBLAS_NUM_THREADS"] == "1"


def test_worker_error_does_not_create_success_file(tmp_path, monkeypatch, caplog):
    from app.services.audio.worker import worker_main

    def fail(_):
        raise ValueError("Fixture invalid PCM")

    monkeypatch.setattr("app.services.audio.worker.analyze_pcm_wav", fail)
    result = tmp_path / "result.json"
    with pytest.raises(ValueError, match="invalid PCM"):
        worker_main([str(tmp_path / "missing.wav"), str(result)])
    assert not result.exists()
    assert "audio.worker.failed" in caplog.text


def test_packaged_entry_dispatch_rejects_bad_pcm_without_starting_server(tmp_path):
    import subprocess

    result = tmp_path / "result.json"
    child = subprocess.run(
        [
            sys.executable,
            "-m",
            "app",
            "--audio-rhythm-worker",
            str(tmp_path / "missing.wav"),
            str(result),
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert child.returncode != 0
    assert "audio.worker.failed" in child.stdout
    assert "Uvicorn running" not in child.stderr
    assert not result.exists()


@pytest.mark.parametrize("broken_log", [False, True])
def test_independent_worker_lifetime_guard_terminates_its_own_subprocess(broken_log):
    import subprocess

    source = """
import os, time, psutil
from app.services.audio import worker
os.environ['CE_RHYTHM_PARENT_PID'] = str(os.getppid())
os.environ['CE_RHYTHM_PARENT_CREATED'] = str(psutil.Process(os.getppid()).create_time())
worker.LIFETIME_SECONDS = 0.05
with worker.parent_lifetime():
    time.sleep(30)
"""
    if broken_log:
        source = source.replace(
            "with worker.parent_lifetime():",
            "worker.LOG.error = lambda *a, **k: (_ for _ in ()).throw(BrokenPipeError())\nwith worker.parent_lifetime():",
        )
    child = subprocess.run(
        [sys.executable, "-c", source], capture_output=True, text=True, timeout=10, check=False
    )
    assert child.returncode != 0
    if not broken_log:
        assert "audio.worker.lifetime_ended" in child.stdout


def test_hashing_deadline_is_checked_between_reads(tmp_path, monkeypatch):
    from app.services.media.inspection import hash_input

    path = tmp_path / "owned.bin"
    path.write_bytes(b"owned fixture")
    from types import SimpleNamespace

    clock = iter([0, 61])
    monkeypatch.setattr(
        "app.services.media.inspection.time", SimpleNamespace(monotonic=lambda: next(clock))
    )
    with pytest.raises(TimeoutError, match="60 second"):
        hash_input(path, threading.Event())
