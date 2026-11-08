"""Media service: probe files and build proxy/thumbnail/export plans."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from app.config import Settings
from app.logging import get_logger
from app.services.media.ffmpeg import (
    FFmpegBinaries,
    candidate_h264_encoders,
    encoder_smoke_command,
    export_command,
    parse_encoders,
    probe_command,
    proxy_command,
    resolve_binaries,
    thumbnail_command,
)
from app.services.media.probe import MediaInfo, parse_probe
from app.services.media.runner import run_command

LOG = get_logger(__name__)


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
        self._h264_encoder: str | None = None
        self._h264_probed = False

    def probe(self, path: Path) -> MediaInfo:
        if not path.is_file():
            msg = f"file not found: {path}"
            raise FileNotFoundError(msg)
        return self._prober.probe(path)

    def binaries(self) -> FFmpegBinaries:
        return resolve_binaries(self._settings)

    def detect_h264_encoder(self) -> str | None:
        """Return the first allowed H.264 encoder that actually opens on this machine.

        Listing is not availability: a build compiled with NVENC lists ``h264_nvenc``
        even with no NVIDIA device present, so each candidate is opened once before
        it is advertised. The answer is cached for the process lifetime because the
        probe costs an FFmpeg spawn and the hardware cannot change under us.
        A cached ``None`` is honoured, so an unusable build is not re-probed.
        """
        if self._h264_probed:
            return self._h264_encoder
        self._h264_encoder = self._detect_h264_encoder_uncached()
        self._h264_probed = True
        return self._h264_encoder

    def _detect_h264_encoder_uncached(self) -> str | None:
        try:
            binaries = self.binaries()
        except Exception as error:
            LOG.warning("media.encoder.probe_unavailable", reason=str(error))
            return None
        try:
            result = run_command([str(binaries.ffmpeg), "-hide_banner", "-encoders"], timeout=30)
        except Exception as error:
            LOG.warning("media.encoder.probe_failed", reason=str(error))
            return None

        candidates = candidate_h264_encoders(parse_encoders(result.stdout))
        for name in candidates:
            if self._encoder_opens(binaries, name):
                LOG.info("media.encoder.selected", encoder=name)
                return name
            LOG.warning("media.encoder.listed_but_unusable", encoder=name)
        if candidates:
            LOG.error("media.encoder.none_usable", listed=candidates)
        return None

    def _encoder_opens(self, binaries: FFmpegBinaries, encoder: str) -> bool:
        """Report whether FFmpeg can actually open ``encoder`` on this machine."""
        try:
            result = run_command(encoder_smoke_command(binaries, encoder), timeout=30)
        except Exception as error:
            LOG.warning("media.encoder.smoke_failed", encoder=encoder, reason=str(error))
            return False
        return result.returncode == 0

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
