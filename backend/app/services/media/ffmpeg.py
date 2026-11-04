"""FFmpeg binary resolution and command construction.

The binary is the **LGPL shared** build only (never a GPL build, no libx264).
H.264 is produced by NVENC with an openh264 fallback — see protocol v2.5.1 / G5.

Commands are returned as argument lists and unit-tested; execution is delegated to
:mod:`app.services.media.runner` so nothing here shells out.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from app.config import Settings

#: Encoder preference for H.264 output. libx264 (GPL) is deliberately absent.
H264_ENCODERS: tuple[str, ...] = ("h264_nvenc", "libopenh264")
#: Encoders that must never appear in a shipped build.
FORBIDDEN_ENCODERS: tuple[str, ...] = ("libx264", "libx265", "libx262")


class FFmpegNotFoundError(RuntimeError):
    """Raised when no usable FFmpeg binary can be located."""


@dataclass(frozen=True)
class FFmpegBinaries:
    """Resolved paths of the bundled FFmpeg tools."""

    ffmpeg: Path
    ffprobe: Path

    def as_dict(self) -> dict[str, str]:
        return {"ffmpeg": str(self.ffmpeg), "ffprobe": str(self.ffprobe)}


def _candidates(settings: Settings, executable: str) -> list[Path]:
    exe = f"{executable}.exe" if os.name == "nt" else executable
    bundled = settings.binaries_dir / "ffmpeg" / "bin" / exe
    flat = settings.binaries_dir / exe
    return [bundled, flat]


def resolve_binaries(settings: Settings, *, allow_path_fallback: bool = True) -> FFmpegBinaries:
    """Locate ffmpeg/ffprobe: bundled install directory first, then ``PATH``."""
    resolved: dict[str, Path] = {}
    for name in ("ffmpeg", "ffprobe"):
        found = next((path for path in _candidates(settings, name) if path.is_file()), None)
        if found is None and allow_path_fallback:
            located = shutil.which(name)
            if located:
                found = Path(located)
        if found is None:
            msg = (
                f"{name} not found. Bundle the LGPL shared build under "
                f"{settings.binaries_dir / 'ffmpeg'} or add it to PATH."
            )
            raise FFmpegNotFoundError(msg)
        resolved[name] = found
    return FFmpegBinaries(ffmpeg=resolved["ffmpeg"], ffprobe=resolved["ffprobe"])


def parse_encoders(output: str) -> set[str]:
    """Extract encoder names from ``ffmpeg -encoders`` output."""
    names: set[str] = set()
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 2 and len(parts[0]) == 6 and parts[0][0] in "VAS":
            names.add(parts[1])
    return names


def available_h264_encoder(encoders: set[str]) -> str | None:
    """Pick the first allowed H.264 encoder that the build actually ships."""
    return next((name for name in H264_ENCODERS if name in encoders), None)


def forbidden_encoders_present(encoders: set[str]) -> set[str]:
    """Return GPL encoders found in the build (should be empty for the LGPL build)."""
    return {name for name in FORBIDDEN_ENCODERS if name in encoders}


def probe_command(binaries: FFmpegBinaries, path: Path) -> list[str]:
    """Ffprobe JSON command for a media file."""
    return [
        str(binaries.ffprobe),
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]


def thumbnail_command(
    binaries: FFmpegBinaries,
    source: Path,
    out_dir: Path,
    *,
    count: int = 12,
    width: int = 240,
) -> list[str]:
    """Tile-filter contact sheet (single JPEG) for the media panel strip."""
    return [
        str(binaries.ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-vf",
        f"fps={max(1, count)}/1,scale={width}:-1,tile={max(1, count)}x1",
        "-frames:v",
        "1",
        "-q:v",
        "3",
        str(out_dir / f"{source.stem}-strip.jpg"),
    ]


def proxy_command(
    binaries: FFmpegBinaries,
    source: Path,
    target: Path,
    *,
    width: int = 960,
    height: int = 540,
    fps: int = 30,
    encoder: str = "libopenh264",
) -> list[str]:
    """Fast, low-bitrate editing proxy (ProRes-free so it stays small)."""
    if encoder in FORBIDDEN_ENCODERS:
        msg = f"encoder '{encoder}' is not allowed (GPL)"
        raise ValueError(msg)
    return [
        str(binaries.ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
        "-vf",
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,fps={fps}",
        "-c:v",
        encoder,
        "-b:v",
        "2500k",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(target),
    ]


def export_command(
    binaries: FFmpegBinaries,
    source: Path,
    target: Path,
    *,
    encoder: str,
    width: int,
    height: int,
    fps: int,
    bitrate_kbps: int,
    audio_bitrate_kbps: int = 192,
) -> list[str]:
    """Build the final export command (NVENC uses ``-preset p5 -tune hq``)."""
    if encoder in FORBIDDEN_ENCODERS:
        msg = f"encoder '{encoder}' is not allowed (GPL)"
        raise ValueError(msg)
    video_args = ["-c:v", encoder, "-b:v", f"{bitrate_kbps}k"]
    if encoder == "h264_nvenc":
        video_args += ["-preset", "p5", "-tune", "hq", "-rc", "vbr"]
    else:
        video_args += ["-maxrate", f"{bitrate_kbps}k", "-bufsize", f"{bitrate_kbps * 2}k"]
    return [
        str(binaries.ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
        "-vf",
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fps={fps}",
        *video_args,
        "-pix_fmt",
        "yuv420p",
        "-profile:v",
        "high",
        "-c:a",
        "aac",
        "-b:a",
        f"{audio_bitrate_kbps}k",
        "-movflags",
        "+faststart",
        str(target),
    ]
