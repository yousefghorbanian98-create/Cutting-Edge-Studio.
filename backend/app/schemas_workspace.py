"""Versioned editor snapshots validated with Pydantic, not a custom parser."""

# ruff: noqa: N815 -- names mirror the versioned browser workspace contract.

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas import Language, Name, Theme

Identifier = Annotated[str, Field(min_length=1, max_length=200)]
Time = Annotated[float, Field(ge=0, le=864000, allow_inf_nan=False)]


class StrictModel(BaseModel):
    """Reject unknown snapshot fields and nonfinite numeric values."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)


class TrackState(StrictModel):
    """Validated TrackState fields in workspace format v1."""

    id: Identifier
    name: Name
    kind: Literal["video", "audio"]
    locked: bool
    muted: bool


class ClipState(StrictModel):
    """Validated ClipState fields in workspace format v1."""

    id: Identifier
    mediaId: Annotated[str, Field(min_length=1, max_length=4096)]
    name: Annotated[str, Field(min_length=1, max_length=1024)]
    trackId: Identifier
    start: Time
    duration: Annotated[float, Field(gt=0, le=864000)]
    inPoint: Time
    kind: Literal["video", "audio"]


class BookmarkState(StrictModel):
    """Validated BookmarkState fields in workspace format v1."""

    id: Identifier
    time: Time
    label: Annotated[str, Field(max_length=200)]
    color: Annotated[str, Field(max_length=100)]


class TimelineState(StrictModel):
    """Validated TimelineState fields in workspace format v1."""

    tracks: Annotated[list[TrackState], Field(min_length=1, max_length=100)]
    clips: Annotated[list[ClipState], Field(max_length=10000)]
    bookmarks: Annotated[list[BookmarkState], Field(max_length=10000)]
    duration: Annotated[float, Field(ge=1, le=864000)]
    playhead: Time
    pxPerSecond: Annotated[float, Field(ge=8, le=400)]
    snapEnabled: bool

    @model_validator(mode="after")
    def valid_references(self) -> TimelineState:
        tracks = {track.id: track for track in self.tracks}
        if len(tracks) != len(self.tracks):
            raise ValueError("duplicate track IDs")
        for items in (self.clips, self.bookmarks):
            if len({item.id for item in items}) != len(items):
                raise ValueError("duplicate clip or bookmark IDs")
        for clip in self.clips:
            if clip.trackId not in tracks or tracks[clip.trackId].kind != clip.kind:
                raise ValueError("clip track is missing or has a different media kind")
            if clip.start + clip.duration > self.duration + 0.001:
                raise ValueError("clip extends past timeline duration")
        if self.playhead > self.duration or any(b.time > self.duration for b in self.bookmarks):
            raise ValueError("playhead/bookmark extends past timeline duration")
        return self


class FeaturesState(StrictModel):
    """Complete post feature switches; partial maps are invalid."""

    replay: bool
    comparison: bool
    captions: bool
    broll: bool
    loudness: bool
    thumbnail: bool
    templates: bool


class PostState(StrictModel):
    """Validated PostState fields in workspace format v1."""

    enabled: FeaturesState
    presetId: Literal["tiktok", "shorts", "youtube", "instagram_feed", "archive"]
    layout: Literal["side_by_side", "stacked", "picture_in_picture"]
    captionFormat: Literal["ass", "srt"]
    quality: Literal["preview", "final"]


class AppearanceState(StrictModel):
    """Validated AppearanceState fields in workspace format v1."""

    language: Language
    theme: Theme


class WorkspaceSnapshot(StrictModel):
    """Validated WorkspaceSnapshot fields in workspace format v1."""

    version: Literal[1]
    timeline: TimelineState
    mediaOrder: Annotated[list[Identifier], Field(max_length=10000)]
    selectedAssetId: Identifier | None
    referenceAssetId: Identifier | None
    wizardStep: Annotated[int, Field(ge=0, le=4)]
    post: PostState
    appearance: AppearanceState


class WorkspaceRead(StrictModel):
    """Validated WorkspaceRead fields in workspace format v1."""

    revision: str
    name: str
    snapshot: WorkspaceSnapshot | None


class WorkspaceSave(StrictModel):
    """Validated WorkspaceSave fields in workspace format v1."""

    base_revision: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    name: Name
    snapshot: WorkspaceSnapshot
