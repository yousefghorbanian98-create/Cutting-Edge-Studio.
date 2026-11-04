"""Thin FFmpeg scdet/ffprobe JSON adapter; no hand-written cut detector or text parser."""

from __future__ import annotations

import os
import threading
from collections.abc import Callable
from itertools import pairwise
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.config import Settings
from app.logging import get_logger
from app.schemas_media import AssetRead
from app.schemas_scenes import CutCandidate, SceneEstimate, SceneFile
from app.services.media.ffmpeg import FFmpegBinaries, probe_command, resolve_binaries
from app.services.media.inspection import hash_input, require_unchanged
from app.services.media.probe import parse_probe
from app.services.media.runner import CommandCancelledError, CommandResult, run_command
from app.services.media.workspaces import ScratchWorkspace

LOG = get_logger(__name__)


class ObservedFrame(BaseModel):
    """Only existing JSON fields produced by ffprobe; Pydantic handles parsing."""

    model_config = ConfigDict(allow_inf_nan=False)
    pts_time: float
    tags: dict[str, str] = Field(default_factory=dict)


class ObservedFrames(BaseModel):
    """Bound the native JSON result; an empty decoder result cannot succeed."""

    frames: list[ObservedFrame] = Field(min_length=1, max_length=36000)


def scenes_unavailable(settings: Settings) -> str | None:
    """Gate the experiment without implying native distribution/licence certification."""
    if not settings.shot_candidates_enabled:
        return (
            "Experimental shot candidates are disabled in this build. Provision the reviewed "
            "LGPL shared FFmpeg filters at build time; no runtime download is performed."
        )
    return None


def scene_command(binaries: FFmpegBinaries, video_index: int) -> list[str]:
    """Keep all user paths OUT of the filter graph: a fixed relative hardlink is used.

    The first video stream index comes from real ffprobe JSON, not a supplied label.
    Native movie/scdet/scale do all decoding and detection. No shell is involved.
    """
    if type(video_index) is not int or not 0 <= video_index <= 1024:
        raise ValueError("Unsupported video stream index")
    return [
        str(binaries.ffprobe),
        "-v",
        "error",
        "-threads",
        "1",
        "-f",
        "lavfi",
        "-i",
        (
            f"movie=filename=input:stream_index={video_index}:dec_threads=1:"
            "format_opts=protocol_whitelist=file,scale=320:-2,scdet=threshold=10"
        ),
        "-show_frames",
        "-show_entries",
        "frame=pts_time:frame_tags=lavfi.scd.score,lavfi.scd.time",
        "-of",
        "json=compact=1",
    ]


def native_payload(result: CommandResult) -> str:
    """Reject native error diagnostics even when ffprobe returns exit status zero."""
    if result.stderr.strip():
        LOG.error("scenes.native.errors", stderr=result.stderr[-2000:])
        raise RuntimeError(
            "Native media reported errors; candidate results were discarded. "
            "Run decode verification or re-import a supported local clip."
        )
    return result.stdout


def measured_candidates(payload: str, duration: float) -> SceneEstimate:
    """Validate native observations and normalize PTS; never invent candidate scores."""
    frames = ObservedFrames.model_validate_json(payload).frames
    first = frames[0].pts_time
    if any(a.pts_time >= b.pts_time for a, b in pairwise(frames)):
        raise ValueError("Decoded video timestamps are not strictly increasing")
    span = frames[-1].pts_time - first
    if span > duration + 0.25:
        raise ValueError("Decoded video exceeds its probed duration")
    candidates = []
    for index, frame in enumerate(frames):
        if "lavfi.scd.score" not in frame.tags:
            raise ValueError("Native scdet frame score is missing")
        # Validate even non-crossing scores; do not accept corrupt/NaN native output.
        score = float(frame.tags["lavfi.scd.score"])
        if not 0 <= score <= 100:
            raise ValueError("Native scdet score is not finite/in range")
        if "lavfi.scd.time" in frame.tags:
            native_time = float(frame.tags["lavfi.scd.time"])
            if abs(native_time - frame.pts_time) > 0.001:
                raise ValueError("Native candidate time disagrees with its observed frame")
            candidates.append(
                CutCandidate(
                    frame_index=index, time_seconds=native_time - first, score_percent=score
                )
            )
        elif score > 10.001:
            raise ValueError("Native threshold crossing has no candidate timestamp")
    return SceneEstimate(
        frames_analyzed=len(frames),
        first_frame_pts_seconds=first,
        decoded_span_seconds=span,
        candidates=candidates,
    )


class FFmpegSceneInspector:
    """One cancellable native process, original provenance, no semantic/model claims."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def inspect(
        self, asset: AssetRead, cancel: threading.Event, progress: Callable[[float], None]
    ) -> SceneFile:
        reason = scenes_unavailable(self.settings)
        if reason:
            raise RuntimeError(reason)
        if cancel.is_set():
            raise CommandCancelledError("Shot candidate job cancelled")
        binaries = resolve_binaries(self.settings, allow_path_fallback=False)
        path = Path(asset.path)
        with ScratchWorkspace(self.settings.cache_dir, "scenes") as workspace:
            folder = workspace.path
            try:
                os.link(path, Path(folder) / "input")
            except OSError as error:
                LOG.error("scenes.stage.failed", error=str(error))
                raise RuntimeError(
                    "Cannot stage a local hardlink. Import via the Media panel onto the "
                    "same local volume as the cache; no input was copied or analysed."
                ) from error
            # Creating/deleting a hardlink changes ctime, so take this baseline AFTER linking.
            before = path.stat()
            staged = Path(folder) / "input"
            linked = staged.stat()
            if staged.is_symlink() or (before.st_dev, before.st_ino) != (
                linked.st_dev,
                linked.st_ino,
            ):
                raise ValueError("Input changed or is a symbolic link while staging; re-import it")
            digest = hash_input(path, cancel)
            probe = probe_command(binaries, path)
            probe[1:1] = ["-protocol_whitelist", "file"]
            info = parse_probe(
                native_payload(
                    run_command(probe, timeout=60, cancel_event=cancel, lifecycle=workspace)
                )
            )
            video = next(
                (s for s in info.raw.get("streams", []) if s.get("codec_type") == "video"), None
            )
            if info.duration <= 0:
                raise ValueError("A usable positive media duration is required")
            estimate = None
            if video is not None:
                if not (
                    info.duration <= 600
                    and 0 < info.fps <= 60
                    and 0 < info.width <= 8192
                    and 0 < info.height <= 8192
                    and info.pixels <= 33177600
                ):
                    raise ValueError(
                        "Experimental scene input requires at most 600 seconds, 60 fps and "
                        "33 megapixels (each dimension <=8192)"
                    )
                progress(10)  # Hash/probe completed, not invented detector-iteration progress.
                result = run_command(
                    scene_command(binaries, video["index"]),
                    cwd=Path(folder),
                    timeout=180,
                    cancel_event=cancel,
                    lifecycle=workspace,
                )
                estimate = measured_candidates(native_payload(result), info.duration)
            after = require_unchanged(path, before, asset.name)
            return SceneFile(
                asset_id=asset.id,
                role=asset.role,
                name=asset.name,
                sha256=digest,
                size_bytes=after.st_size,
                mtime_ns=str(after.st_mtime_ns),
                duration=info.duration,
                has_audio=info.has_audio,
                has_video=video is not None,
                estimate=estimate,
                status="no-video"
                if estimate is None
                else "candidates"
                if estimate.candidates
                else "no-candidates",
            )
