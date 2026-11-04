"""Pydantic schemas for media assets and background jobs."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Role = Literal["source", "reference", "music", "broll", "voiceover"]


class AssetCreate(BaseModel):
    """Import a file that already exists on disk (no uploads, no network)."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    role: Role = "source"


class AssetRead(BaseModel):
    """Media asset as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    name: str = ""
    size_bytes: int = 0
    available: bool = True
    path: str
    role: str
    kind: str
    duration: float
    fps: float
    width: int
    height: int
    #: Derived from the cached ffprobe JSON so the UI can show codec/audio chips.
    video_codec: str | None = None
    audio_codec: str | None = None
    has_audio: bool = False
    created_at: datetime
    updated_at: datetime


class JobRead(BaseModel):
    """Background job state, polled by the progress UI."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: str
    state: str
    percent: float
    message: str
    error: str | None
    created_at: datetime
    updated_at: datetime


class EncoderProbe(BaseModel):
    """Result of asking FFmpeg which H.264 encoder is available."""

    encoder: str | None
    hardware: bool
    note: str
