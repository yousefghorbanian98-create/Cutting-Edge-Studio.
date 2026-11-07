"""SQLAlchemy ORM models for local project storage."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


class TimestampMixin:
    """Created/updated bookkeeping columns."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
    )


class Project(TimestampMixin, Base):
    """A single editing project (one output video)."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    #: "style-match" | "highlights" | "manual"
    mode: Mapped[str] = mapped_column(String(32), default="style-match")
    #: "bodybuilding" | "volleyball" | "generic"
    sport: Mapped[str] = mapped_column(String(32), default="generic")
    language: Mapped[str] = mapped_column(String(8), default="fa")
    width: Mapped[int] = mapped_column(Integer, default=1080)
    height: Mapped[int] = mapped_column(Integer, default=1920)
    fps: Mapped[int] = mapped_column(Integer, default=30)
    #: Serialized editor state (timeline, wizard answers, learned preferences).
    state_json: Mapped[str] = mapped_column(Text, default="{}")

    assets: Mapped[list[MediaAsset]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    bookmarks: Mapped[list[Bookmark]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    artifacts: Mapped[list[Artifact]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class MediaAsset(TimestampMixin, Base):
    """An imported source file or a reference video."""

    __tablename__ = "media_assets"
    __table_args__ = (UniqueConstraint("project_id", "path", name="uq_asset_project_path"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
    )
    path: Mapped[str] = mapped_column(Text, nullable=False)
    #: "source" | "reference" | "music" | "broll" | "voiceover"
    role: Mapped[str] = mapped_column(String(16), default="source")
    #: "video" | "audio" | "image"
    kind: Mapped[str] = mapped_column(String(16), default="video")
    duration: Mapped[float] = mapped_column(Float, default=0.0)
    fps: Mapped[float] = mapped_column(Float, default=0.0)
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    #: Cached ffprobe JSON so re-imports never re-shell out.
    probe_json: Mapped[str] = mapped_column(Text, default="{}")

    project: Mapped[Project] = relationship(back_populates="assets")


class Bookmark(TimestampMixin, Base):
    """Timeline scene bookmark (hotkey M in the UI)."""

    __tablename__ = "bookmarks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
    )
    timecode: Mapped[float] = mapped_column(Float, default=0.0)
    label: Mapped[str] = mapped_column(String(200), default="")
    color: Mapped[str] = mapped_column(String(16), default="#FF6B35")

    project: Mapped[Project] = relationship(back_populates="bookmarks")


class Artifact(TimestampMixin, Base):
    """A pipeline artifact (StyleDNA.json, EDL.json, CompatibilityReport.json...)."""

    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
    )
    #: e.g. "reference-manifest", "style-dna", "edl", "compatibility-report".
    kind: Mapped[str] = mapped_column(String(48), index=True)
    #: Monotonically increasing per (project, kind) so stages can be re-run.
    revision: Mapped[int] = mapped_column(Integer, default=1)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")

    project: Mapped[Project] = relationship(back_populates="artifacts")


def as_dict(row: Base, exclude: set[str] | None = None) -> dict[str, Any]:
    """Serialize an ORM row to a JSON-friendly dict."""
    excluded = exclude or set()
    return {
        column.key: getattr(row, column.key)
        for column in row.__table__.columns
        if column.key not in excluded
    }
