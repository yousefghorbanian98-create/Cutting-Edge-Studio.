"""Media service: probe files and build proxy/thumbnail/export plans."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from app.config import Settings
from app.services.media.ffmpeg import (
    FFmpegBinaries,
    available_h264_encoder,
    export_command,
    parse_encoders,
    probe_command,
    proxy_command,
    resolve_binaries,
    thumbnail_command,
)
from app.services.media.probe import MediaInfo, parse_probe
from app.services.media.runner import run_command


class Prober(Protocol):
    """Anything that can turn a path into :class:`MediaInfo` (fakeable in tests)."""

    def probe(self, path: Path) -> MediaInfo:
        """Return media metadata for ``path``."""


class FFmpegProber:
    """Real prober: shells out to the bundled ffprobe."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def probe(self, path: Path) -> MediaInfo:
        binaries = resolve_binaries(self._settings)
        result = run_command(probe_command(binaries, path), timeout=60)
        return parse_probe(result.stdout)


class MediaService:
    """High-level media operations used by the HTTP layer and the pipelines."""

    def __init__(self, settings: Settings, prober: Prober | None = None) -> None:
        self._settings = settings
        self._prober: Prober = prober or FFmpegProber(settings)

    def probe(self, path: Path) -> MediaInfo:
        if not path.is_file():
            msg = f"file not found: {path}"
            raise FileNotFoundError(msg)
        return self._prober.probe(path)

    def binaries(self) -> FFmpegBinaries:
        return resolve_binaries(self._settings)

    def detect_h264_encoder(self) -> str | None:
        """Ask FFmpeg which allowed H.264 encoder is present (NVENC first)."""
        try:
            binaries = self.binaries()
        except Exception:
            return None
        try:
            result = run_command([str(binaries.ffmpeg), "-hide_banner", "-encoders"], timeout=30)
        except Exception:
            return None
        return available_h264_encoder(parse_encoders(result.stdout))

    def proxy_plan(self, source: Path, info: MediaInfo, out_dir: Path) -> list[str]:
        """Command list for a 960x540/30fps proxy."""
        binaries = self.binaries()
        target = out_dir / f"{source.stem}-proxy.mp4"
        return proxy_command(
            binaries,
            source,
            target,
            width=min(960, max(320, info.width or 960)),
            height=min(540, max(180, info.height or 540)),
        )

    def thumbnail_plan(self, source: Path, out_dir: Path, count: int = 12) -> list[str]:
        return thumbnail_command(self.binaries(), source, out_dir, count=count)

    def export_plan(
        self,
        source: Path,
        target: Path,
        *,
        width: int,
        height: int,
        fps: int,
        platform_bitrate_kbps: int,
    ) -> list[str]:
        encoder = self.detect_h264_encoder() or "libopenh264"
        binaries = self.binaries()
        return export_command(
            binaries,
            source,
            target,
            encoder=encoder,
            width=width,
            height=height,
            fps=fps,
            bitrate_kbps=platform_bitrate_kbps,
        )


def needs_proxy(info: MediaInfo, *, max_pixels: int = 1920 * 1080) -> bool:
    """Proxy is worth it for big or long-GOP sources (>1080p or >25 Mbps)."""
    return info.pixels > max_pixels or info.bit_rate > 25_000_000
