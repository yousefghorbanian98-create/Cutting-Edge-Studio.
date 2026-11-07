"""Caption rendering: Whisper segments to SRT/ASS with RTL support."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

#: Characters per caption line before wrapping (safe for 9:16 with 44 px text).
LINE_WIDTH = 34
#: Reading-speed ceiling in characters per second (Netflix-style guideline).
MAX_CPS = 20.0
RTL_LANGUAGES = ("fa", "ar", "he", "ur", "ps")


@dataclass(frozen=True)
class CaptionStyle:
    """Styling derived from the reference DNA (or user overrides)."""

    font_name: str = "Vazirmatn"
    font_size: int = 44
    primary_color: str = "&H00FFFFFF"
    outline_color: str = "&H00000000"
    outline: int = 3
    alignment: int = 2
    margin_v: int = 140


def wrap_text(text: str, width: int = LINE_WIDTH) -> list[str]:
    """Greedy word wrap that never splits a word."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if len(candidate) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def _timestamp_srt(seconds: float) -> str:
    seconds = max(0.0, seconds)
    hours, rest = divmod(int(seconds), 3600)
    minutes, secs = divmod(rest, 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _timestamp_ass(seconds: float) -> str:
    seconds = max(0.0, seconds)
    hours, rest = divmod(int(seconds), 3600)
    minutes, secs = divmod(rest, 60)
    centis = int(round((seconds - int(seconds)) * 100))
    return f"{hours:d}:{minutes:02d}:{secs:02d}.{centis:02d}"


def segments_to_srt(segments: list[dict[str, Any]], *, max_cps: float = MAX_CPS) -> str:
    """Convert Whisper segments to SRT, re-timing lines that would be unreadable."""
    blocks: list[str] = []
    index = 1
    for segment in segments:
        start = float(segment.get("start", 0.0))
        end = float(segment.get("end", start + 1.0))
        text = " ".join(str(segment.get("text", "")).split())
        if not text:
            continue
        duration = max(0.4, end - start)
        minimum = len(text) / max_cps + 0.2
        if duration < minimum:
            end = start + minimum
        lines = wrap_text(text)
        blocks.append(
            f"{index}\n{_timestamp_srt(start)} --> {_timestamp_srt(end)}\n"
            + "\n".join(lines)
            + "\n"
        )
        index += 1
    return "\n".join(blocks)


def segments_to_ass(
    segments: list[dict[str, Any]],
    *,
    style: CaptionStyle | None = None,
    language: str = "en",
    play_res: tuple[int, int] = (1080, 1920),
) -> str:
    """Convert segments to ASS, using ``RTL``/``rtl`` hints for right-to-left languages."""
    style = style or CaptionStyle()
    rtl = language.split("-")[0].lower() in RTL_LANGUAGES
    alignment = 2 if not rtl else style.alignment
    header = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {play_res[0]}",
        f"PlayResY: {play_res[1]}",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, "
        "Bold, Italic, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{style.font_name},{style.font_size},{style.primary_color},"
        f"{style.outline_color},&H80000000,0,0,1,{style.outline},0,{alignment},60,60,"
        f"{style.margin_v},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    events: list[str] = []
    for segment in segments:
        text = " ".join(str(segment.get("text", "")).split())
        if not text:
            continue
        start = _timestamp_ass(float(segment.get("start", 0.0)))
        end = _timestamp_ass(float(segment.get("end", 0.0)))
        body = r"\N".join(wrap_text(text))
        if rtl:
            # ASS has no bidi engine: mark the line so libass applies the RTL override.
            body = "\u202b" + body + "\u202c"
        events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{body}")
    return "\n".join([*header, *events]) + "\n"


def caption_style_from_dna(dna: dict[str, Any]) -> CaptionStyle:
    """Infer caption size/colour from the reference: big text for fast, punchy edits."""
    cuts_per_minute = float(dna.get("shots_per_minute", 0.0))
    if cuts_per_minute >= 30:
        size = 52
    elif cuts_per_minute >= 15:
        size = 46
    else:
        size = 40
    color = dna.get("color") or {}
    primary = "&H00FFFFFF" if float(color.get("contrast", 0.5)) >= 0.45 else "&H0000E5FF"
    return CaptionStyle(font_size=size, primary_color=primary)
