"""Platform export presets (resolution/fps/bitrate) derived from the protocol."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Preset:
    """One export target shown in the UI."""

    name: str
    label: str
    width: int
    height: int
    fps: int
    bitrate_kbps: int
    max_seconds: int | None = None


PRESETS: dict[str, Preset] = {
    "tiktok": Preset("tiktok", "TikTok / Reels (9:16)", 1080, 1920, 30, 10000, 180),
    "youtube": Preset("youtube", "YouTube (16:9)", 1920, 1080, 30, 12000, None),
    "shorts": Preset("shorts", "YouTube Shorts (9:16)", 1080, 1920, 30, 10000, 60),
    "instagram_feed": Preset("instagram_feed", "Instagram Feed (4:5)", 1080, 1350, 30, 8000, 60),
    "archive": Preset("archive", "Archive master (4K 16:9)", 3840, 2160, 30, 45000, None),
}


def get_preset(name: str) -> Preset:
    """Look up a preset, falling back to TikTok with an explicit error for unknown names."""
    try:
        return PRESETS[name]
    except KeyError as error:
        msg = f"unknown preset '{name}' (available: {', '.join(PRESETS)})"
        raise ValueError(msg) from error


def preset_options(preset: Preset) -> list[str]:
    """FFmpeg arguments for the preset (encoder is added by the caller)."""
    return [
        "-s",
        f"{preset.width}x{preset.height}",
        "-r",
        str(preset.fps),
        "-b:v",
        f"{preset.bitrate_kbps}k",
    ]


def trim_to_preset(duration: float, preset: Preset) -> float:
    """Clamp an edit to the platform's maximum length."""
    if preset.max_seconds is None:
        return duration
    return min(duration, float(preset.max_seconds))
