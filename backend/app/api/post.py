"""Post-production endpoints (P7): replay, comparison, captions, b-roll, presets, templates."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.config import get_settings
from app.logging import get_logger
from app.services.post.broll import plan_broll_inserts, rank_broll
from app.services.post.captions import caption_style_from_dna, segments_to_ass, segments_to_srt
from app.services.post.loudness import TARGETS, parse_loudnorm_block, plan_loudness
from app.services.post.presets import PRESETS, get_preset, preset_options, trim_to_preset
from app.services.post.replay import LAYOUTS, comparison_filters, plan_replay
from app.services.post.templates import (
    Template,
    apply_overrides,
    list_templates,
    load_template,
    save_template,
)

router = APIRouter(prefix="/post", tags=["post-production"])
LOG = get_logger(__name__)


class ReplayPayload(BaseModel):
    """Replay request: the peak moment plus optional window padding."""

    model_config = ConfigDict(extra="forbid")

    moment: dict[str, Any]
    lead: float = 0.8
    tail: float = 0.4


class ComparisonPayload(BaseModel):
    """Comparison request: layout, canvas size and optional overlay labels."""

    model_config = ConfigDict(extra="forbid")

    layout: str = Field(default="side_by_side")
    width: int = 1080
    height: int = 1920
    labels: list[str] | None = None


class CaptionPayload(BaseModel):
    """Caption request: Whisper segments plus the caption format."""

    model_config = ConfigDict(extra="forbid")

    segments: list[dict[str, Any]]
    language: str = "en"
    dna: dict[str, Any] = Field(default_factory=dict)
    format: str = "srt"


class BrollPayload(BaseModel):
    """B-roll request: the CLIP prompt embedding and candidate clips."""

    model_config = ConfigDict(extra="forbid")

    prompt_embedding: list[float]
    candidates: list[dict[str, Any]]
    timeline_duration: float = 60.0
    every_seconds: float = 12.0


class TemplatePayload(BaseModel):
    """Template request: a name, the DNA snapshot and optional overrides."""

    model_config = ConfigDict(extra="forbid")

    name: str
    dna: dict[str, Any]
    overrides: dict[str, Any] = Field(default_factory=dict)


@router.get("/presets", summary="Platform presets")
def presets() -> list[dict[str, Any]]:
    return [
        {
            "name": preset.name,
            "label": preset.label,
            "width": preset.width,
            "height": preset.height,
            "fps": preset.fps,
            "bitrate_kbps": preset.bitrate_kbps,
            "max_seconds": preset.max_seconds,
            "options": preset_options(preset),
        }
        for preset in PRESETS.values()
    ]


@router.get("/layouts", summary="Comparison layouts")
def layouts() -> list[str]:
    return list(LAYOUTS)


@router.post("/replay", summary="Plan an instant replay")
def replay(payload: ReplayPayload) -> dict[str, Any]:
    plan = plan_replay(payload.moment, lead=payload.lead, tail=payload.tail)
    return {"start": plan.start, "end": plan.end, "speed": plan.speed, "filters": plan.filters}


@router.post("/comparison", summary="Comparison filter graph")
def comparison(payload: ComparisonPayload) -> dict[str, Any]:
    labels = tuple(payload.labels) if payload.labels and len(payload.labels) == 2 else None
    try:
        graph = comparison_filters(
            payload.layout,
            width=payload.width,
            height=payload.height,
            labels=labels,  # type: ignore[arg-type]
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    return {"layout": payload.layout, "filter_graph": graph}


@router.post("/captions", summary="Render captions (SRT or ASS)")
def captions(payload: CaptionPayload) -> dict[str, Any]:
    if payload.format == "ass":
        style = caption_style_from_dna(payload.dna)
        return {
            "format": "ass",
            "content": segments_to_ass(payload.segments, style=style, language=payload.language),
        }
    if payload.format == "srt":
        return {"format": "srt", "content": segments_to_srt(payload.segments)}
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="format must be srt or ass"
    )


@router.post("/broll", summary="Rank b-roll and place inserts")
def broll(payload: BrollPayload) -> dict[str, Any]:
    ranked = rank_broll(payload.prompt_embedding, payload.candidates)
    inserts = plan_broll_inserts(
        ranked, timeline_duration=payload.timeline_duration, every_seconds=payload.every_seconds
    )
    return {"ranked": ranked, "inserts": inserts}


@router.post("/loudness", summary="Parse an FFmpeg loudnorm log into a second-pass plan")
def loudness(stderr: str, platform: str = "tiktok") -> dict[str, Any]:
    measurement = parse_loudnorm_block(stderr)
    if measurement is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="no loudnorm block found"
        )
    plan = plan_loudness(measurement, platform=platform if platform in TARGETS else "tiktok")
    return {
        "filter_chain": plan.filter_chain,
        "mode": plan.mode,
        "gain_db": plan.gain_db,
        "target": plan.target,
        "measured": {"i": plan.measured_i, "tp": plan.measured_tp, "lra": plan.measured_lra},
    }


@router.get("/templates", summary="List user templates")
def templates() -> list[dict[str, Any]]:
    return list_templates(get_settings().data_dir)


@router.post("/templates", status_code=status.HTTP_201_CREATED, summary="Save a template")
def create_template(payload: TemplatePayload) -> dict[str, Any]:
    root = get_settings().data_dir
    path = save_template(
        root, Template(name=payload.name, dna=payload.dna, overrides=payload.overrides)
    )
    LOG.info("post.template.saved", name=payload.name, path=str(path))
    return {"id": path.stem, "name": payload.name}


@router.get("/templates/{name}", summary="Load a template")
def read_template(name: str) -> dict[str, Any]:
    try:
        template = load_template(get_settings().data_dir, name)
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="template not found"
        ) from error
    return template.to_dict()


@router.post("/templates/{name}/apply", summary="Apply a template's overrides to a DNA")
def apply_template(name: str, dna: dict[str, Any]) -> dict[str, Any]:
    try:
        template = load_template(get_settings().data_dir, name)
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="template not found"
        ) from error
    return apply_overrides(dna, template.overrides)


@router.get("/presets/{name}", summary="Single preset with its trim limit")
def preset(name: str, duration: float = 60.0) -> dict[str, Any]:
    try:
        found = get_preset(name)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return {
        "name": found.name,
        "label": found.label,
        "options": preset_options(found),
        "trimmed_duration": trim_to_preset(duration, found),
    }
