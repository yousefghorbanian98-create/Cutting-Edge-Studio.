"""Pydantic v2 schemas for the local REST API."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Sport = Literal["bodybuilding", "volleyball", "generic"]
Mode = Literal["style-match", "highlights", "manual"]
Language = Literal["fa", "en"]
Theme = Literal["pro", "glass", "minimal"]

Name = Annotated[str, Field(min_length=1, max_length=200)]


class ORMModel(BaseModel):
    """Base model reading attributes from ORM rows."""

    model_config = ConfigDict(from_attributes=True)


class HealthResponse(BaseModel):
    """Liveness/readiness payload used by the Tauri shell and smoke tests."""

    status: Literal["ok"] = "ok"
    version: str
    app_name: str
    offline: bool
    database: str
    models_dir: str


class ProjectCreate(BaseModel):
    """Payload for creating a project."""

    model_config = ConfigDict(extra="forbid")

    name: Name = "Untitled"
    mode: Mode = "style-match"
    sport: Sport = "generic"
    language: Language = "fa"
    width: int = Field(default=1080, ge=16, le=7680)
    height: int = Field(default=1920, ge=16, le=7680)
    fps: int = Field(default=30, ge=1, le=240)
    state_json: str = "{}"


class ProjectUpdate(BaseModel):
    """Partial update payload; unset fields are left untouched."""

    model_config = ConfigDict(extra="forbid")

    name: Name | None = None
    mode: Mode | None = None
    sport: Sport | None = None
    language: Language | None = None
    width: int | None = Field(default=None, ge=16, le=7680)
    height: int | None = Field(default=None, ge=16, le=7680)
    fps: int | None = Field(default=None, ge=1, le=240)
    state_json: str | None = None


class ProjectRead(ORMModel):
    """Project representation returned by the API."""

    id: str
    name: str
    mode: str
    sport: str
    language: str
    width: int
    height: int
    fps: int
    state_json: str
    created_at: datetime
    updated_at: datetime


class SettingsRead(BaseModel):
    """Client-visible settings subset (never exposes filesystem internals)."""

    version: str
    language: Language
    theme: Theme
    offline: bool
    data_dir: str
    home_dir: str
