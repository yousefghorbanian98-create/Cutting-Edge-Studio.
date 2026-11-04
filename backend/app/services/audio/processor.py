"""Reuse the inspection worker with FFmpeg PCM extraction and an isolated librosa child."""

from __future__ import annotations

import os
import sys
import tempfile
import threading
import wave
from collections.abc import Callable
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import psutil

from app.config import Settings
from app.logging import get_logger
from app.schemas_media import AssetRead
from app.schemas_rhythm import RhythmEstimate, RhythmFile
from app.services.media.ffmpeg import FFmpegBinaries, probe_command, resolve_binaries
from app.services.media.inspection import hash_input, require_unchanged
from app.services.media.probe import parse_probe
from app.services.media.progress import ProgressEvent
from app.services.media.runner import run_command

LOG = get_logger(__name__)


def rhythm_unavailable(settings: Settings) -> str | None:
    """Explicit experimental build gate, not an implicit licence/distribution certificate."""
    if not settings.audio_rhythm_enabled:
        return (
            "Experimental audio rhythm jobs are not enabled in this build. Provision audited "
            "analysis dependencies and dynamic native libraries on the build machine; "
            "no runtime installation or download is performed."
        )
    try:
        installed = version("librosa")
    except PackageNotFoundError as error:
        LOG.error("audio.rhythm.unavailable", error=str(error))
        return (
            "librosa 0.11.0 is missing; provision the audited analysis environment at build time."
        )
    if installed != "0.11.0":
        return "This rhythm adapter requires the reviewed librosa 0.11.0 build."
    return None


def pcm_command(binaries: FFmpegBinaries, source: Path, target: Path) -> list[str]:
    """Decode only the first audio stream into bounded mono PCM, never H.264 export."""
    return [
        str(binaries.ffmpeg),
        "-hide_banner",
        "-nostdin",
        "-nostats",
        "-v",
        "error",
        "-xerror",
        "-y",
        "-progress",
        "pipe:1",
        "-threads",
        "1",
        "-i",
        str(source),
        "-map",
        "0:a:0",
        "-vn",
        "-sn",
        "-dn",
        "-ac",
        "1",
        "-ar",
        "22050",
        # 601 s is a hard disk/output guard, NOT an accepted truncated analysis.
        # The adapter rejects anything over 600 s, including this guard's output.
        "-t",
        "601",
        "-c:a",
        "pcm_s16le",
        "-f",
        "wav",
        str(target),
    ]


def worker_command(wav: Path, result: Path) -> list[str]:
    """Use the sidecar entry point when packaged, or its Python module in development."""
    entry = (
        [sys.executable, "--audio-rhythm-worker"]
        if getattr(sys, "frozen", False)
        else [
            sys.executable,
            "-m",
            "app.services.audio.worker",
        ]
    )
    return [*entry, str(wav), str(result)]


class FFmpegRhythmInspector:
    """Original media provenance + first-audio-stream measurement, never video analysis."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def estimate_pcm(
        self,
        binaries: FFmpegBinaries,
        path: Path,
        duration: float,
        cancel: threading.Event,
        progress: Callable[[float], None],
    ) -> RhythmEstimate:
        with tempfile.TemporaryDirectory(prefix="rhythm-", dir=self.settings.cache_dir) as folder:
            wav, result = Path(folder) / "audio.wav", Path(folder) / "result.json"

            def measured(event: ProgressEvent) -> None:
                progress(min(49, (event.percent or 0) / 2))

            run_command(
                pcm_command(binaries, path, wav),
                timeout=120,
                cancel_event=cancel,
                on_progress=measured,
                total_seconds=duration,
            )
            progress(50)  # Extraction completed; no percentage invented during librosa/JIT.
            env = dict(
                os.environ,
                NUMBA_NUM_THREADS="1",
                OMP_NUM_THREADS="1",
                OPENBLAS_NUM_THREADS="1",
                MKL_NUM_THREADS="1",
                CE_RHYTHM_PARENT_PID=str(os.getpid()),
                CE_RHYTHM_PARENT_CREATED=str(psutil.Process().create_time()),
            )
            cwd = None if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[3]
            run_command(
                worker_command(wav, result), timeout=180, cancel_event=cancel, cwd=cwd, env=env
            )
            if result.stat().st_size > 2 * 1024 * 1024:
                raise ValueError("Rhythm worker output exceeded its safety limit")
            measured_result = RhythmEstimate.model_validate_json(result.read_text())
            if measured_result.sha256 != hash_input(wav, cancel):
                raise ValueError("Worker result does not match extracted PCM")
            with wave.open(str(wav), "rb") as pcm:
                if pcm.getnframes() != measured_result.samples_analyzed:
                    raise ValueError("Worker sample count does not match extracted PCM")
            if measured_result.duration_seconds > duration + 0.25:
                raise ValueError("Extracted PCM duration does not match source metadata")
            return measured_result

    def inspect(
        self,
        asset: AssetRead,
        cancel: threading.Event,
        progress: Callable[[float], None],
    ) -> RhythmFile:
        """No-audio is an explicit skip; silence is measured, not a fabricated tempo."""
        reason = rhythm_unavailable(self.settings)
        if reason is not None:
            raise RuntimeError(reason)
        binaries = resolve_binaries(self.settings, allow_path_fallback=False)
        path = Path(asset.path)
        before = path.stat()
        digest = hash_input(path, cancel)
        info = parse_probe(
            run_command(probe_command(binaries, path), timeout=60, cancel_event=cancel).stdout
        )
        if info.duration <= 0 or (info.has_audio and not 1 <= info.duration <= 600):
            raise ValueError("Rhythm analysis accepts audio durations from 1 to 600 seconds")
        estimate = (
            self.estimate_pcm(binaries, path, info.duration, cancel, progress)
            if info.has_audio
            else None
        )
        after = require_unchanged(path, before, asset.name)
        return RhythmFile(
            asset_id=asset.id,
            role=asset.role,
            name=asset.name,
            sha256=digest,
            size_bytes=after.st_size,
            mtime_ns=str(after.st_mtime_ns),
            duration=info.duration,
            has_audio=info.has_audio,
            estimate=estimate,
            status="no-audio"
            if estimate is None
            else "estimated"
            if estimate.beat_times_seconds
            else "no-beats",
        )
