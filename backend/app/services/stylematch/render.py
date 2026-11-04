"""Stages 7-11 — virtual camera, colour transfer and render plans (FFmpeg filters only)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.services.media.ffmpeg import FFmpegBinaries, export_command
from app.services.stylematch.types import EDL

#: Zoom range of the virtual camera (protocol: gentle push-in, never a hard punch).
ZOOM_MIN = 1.0
ZOOM_MAX = 1.18


@dataclass(frozen=True)
class RenderPlan:
    """Everything the renderer needs, without executing anything."""

    command: list[str]
    filter_chain: str
    output: Path


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def zoompan_filter(
    face_center: tuple[float, float] | None, *, fps: int, duration: float, zoom_to: float = ZOOM_MAX
) -> str:
    """FFmpeg ``zoompan`` push-in centred on the face (falls back to the frame centre)."""
    frames = max(1, int(round(fps * max(0.1, duration))))
    target = _clamp(zoom_to, ZOOM_MIN, ZOOM_MAX)
    centre_x, centre_y = face_center or (0.5, 0.5)
    # zoompan works in pixels: keep the anchor inside the frame so `x`/`y` never go negative.
    anchor_x = _clamp(centre_x, 0.0, 1.0) * 1920
    anchor_y = _clamp(centre_y, 0.0, 1.0) * 1080
    return (
        f"zoompan=z='min({target},{ZOOM_MIN}+0.0008*on)':"
        f"x='{anchor_x:.1f}-(iw/zoom/2)':y='{anchor_y:.1f}-(ih/zoom/2)':"
        f"d={frames}:s=1920x1080:fps={fps}"
    )


def color_grade_filter(target: dict[str, float], source: dict[str, float]) -> str:
    """Colour transfer as an ``eq``/``colorbalance`` pair from mean-colour deltas.

    This is the OSS ``color-matcher`` approach reduced to the two parameters FFmpeg can
    apply natively, so no custom pixel loop is needed.
    """
    target_sat = _clamp(float(target.get("saturation", 0.5)), 0.0, 2.0)
    source_sat = _clamp(float(source.get("saturation", 0.5)), 0.05, 2.0)
    target_contrast = _clamp(float(target.get("contrast", 0.5)), 0.0, 2.0)
    source_contrast = _clamp(float(source.get("contrast", 0.5)), 0.05, 2.0)

    saturation = _clamp(target_sat / source_sat, 0.5, 1.6)
    contrast = _clamp(target_contrast / source_contrast, 0.6, 1.5)
    warmth = (float(target.get("r", 128)) - float(target.get("b", 128))) / 255.0
    eq = f"eq=contrast={contrast:.3f}:saturation={saturation:.3f}"
    balance = f"colorbalance=rs={_clamp(warmth, -0.2, 0.2):.3f}:bs={_clamp(-warmth, -0.2, 0.2):.3f}"
    return f"{eq},{balance}"


def build_filter_chain(
    edl: EDL,
    *,
    face_center: tuple[float, float] | None = None,
    source_color: dict[str, float] | None = None,
    watermark: Path | None = None,
) -> str:
    """Compose the per-segment filter chain (scale → zoom → colour → watermark)."""
    width = int(edl.get("width", 1080))
    height = int(edl.get("height", 1920))
    fps = int(edl.get("fps", 30))
    duration = float(edl.get("total_duration", 0.0))

    parts = [
        f"scale={width}:{height}:force_original_aspect_ratio=decrease",
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
        zoompan_filter(face_center, fps=fps, duration=max(0.5, duration)),
        color_grade_filter(edl.get("color") or {}, source_color or {"r": 128, "g": 128, "b": 128}),
        f"fps={fps}",
    ]
    if watermark is not None:
        parts.append("drawbox=x=iw-260:y=ih-90:w=240:h=60:color=black@0.35:t=fill")
    return ",".join(parts)


def build_render_plan(
    binaries: FFmpegBinaries,
    source: Path,
    output: Path,
    edl: EDL,
    *,
    bitrate_kbps: int = 12000,
    encoder: str = "h264_nvenc",
    face_center: tuple[float, float] | None = None,
    source_color: dict[str, float] | None = None,
    watermark: Path | None = None,
) -> RenderPlan:
    """Full-quality render command (NVENC H.264 by default)."""
    chain = build_filter_chain(
        edl, face_center=face_center, source_color=source_color, watermark=watermark
    )
    command = export_command(
        binaries,
        source,
        output,
        encoder=encoder,
        width=int(edl.get("width", 1080)),
        height=int(edl.get("height", 1920)),
        fps=int(edl.get("fps", 30)),
        bitrate_kbps=bitrate_kbps,
    )
    # Replace the default -vf argument with the composed chain (kept last-wins for FFmpeg).
    if "-vf" in command:
        index = command.index("-vf")
        command[index + 1] = f"{chain},{command[index + 1]}"
    return RenderPlan(command=command, filter_chain=chain, output=output)


def build_preview_plan(
    binaries: FFmpegBinaries,
    source: Path,
    output: Path,
    edl: EDL,
    *,
    face_center: tuple[float, float] | None = None,
) -> RenderPlan:
    """480p / 24 fps watermarked preview shown at Stage 9."""
    preview_edl: EDL = {**edl, "width": 480, "height": 854, "fps": 24}
    plan = build_render_plan(
        binaries,
        source,
        output,
        preview_edl,
        bitrate_kbps=1200,
        encoder="libopenh264",
        face_center=face_center,
        watermark=output,
    )
    command = list(plan.command)
    if "-profile:v" in command:
        command.remove("-profile:v")
        command.remove("high")
    return RenderPlan(command=command, filter_chain=plan.filter_chain, output=output)


def concat_list_file(segments: list[dict[str, Any]], directory: Path) -> Path:
    """Write the ``concat`` demuxer list for the EDL segments."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "segments.txt"
    lines = [f"file '{segment['source']}'" for segment in segments if segment.get("source")]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
