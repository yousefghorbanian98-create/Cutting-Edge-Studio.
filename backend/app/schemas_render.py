"""Render job schemas — real EDL-to-file, no GPL encoder."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RenderState = Literal["queued", "running", "done", "failed", "cancelled", "interrupted"]
RenderQuality = Literal["preview", "final"]


class RenderRequest(BaseModel):
    """EDL payload plus quality. EDL must be the validated output of /stylematch/edl."""

    model_config = ConfigDict(extra="forbid")
    edl: dict = Field(..., description="Validated EDL dict from stylematch pipeline")
    quality: RenderQuality = "preview"


class RenderReport(BaseModel):
    """Terminal result — real file, probed, not faked."""

    version: Literal[1] = 1
    method: Literal["ffmpeg-edl-render"] = "ffmpeg-edl-render"
    scope: Literal["render-only"] = "render-only"
    output_path: str
    duration: float
    width: int
    height: int
    fps: int
    encoder: str
    size_bytes: int


class RenderRead(BaseModel):
    """Durable job + live progress."""

    id: str
    project_id: str
    state: RenderState
    percent: float = 0
    message: str = ""
    error: str | None = None
    stale: bool = False
    quality: RenderQuality = "preview"
    report: RenderReport | None = None

    model_config = ConfigDict(extra="allow")
