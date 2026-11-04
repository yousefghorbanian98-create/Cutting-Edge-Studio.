"""Typed real-media inspection records, explicitly distinct from model inference."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas_rhythm import RhythmReport

Operation = Literal["decode", "rhythm"]

AssetId = Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]


class InspectionRequest(BaseModel):
    """Only registered IDs are accepted, never client-supplied filesystem paths/labels."""

    model_config = ConfigDict(extra="forbid", strict=True)
    reference_asset_id: AssetId
    source_asset_ids: Annotated[list[AssetId], Field(min_length=1, max_length=100)]


class InspectedFile(BaseModel):
    """Actual ffprobe facts and FFmpeg decode observations for one immutable input."""

    model_config = ConfigDict(allow_inf_nan=False)

    asset_id: str
    role: str
    name: str
    sha256: str
    size_bytes: int
    mtime_ns: str
    duration: float
    width: int
    height: int
    fps: float
    video_codec: str | None
    audio_codec: str | None
    has_audio: bool
    decoded_frames: int
    decoded_seconds: float


class InspectionReport(BaseModel):
    """A decode-verification report; there are no inferred moments, beats or DNA."""

    version: Literal[1] = 1
    method: Literal["ffprobe+ffmpeg-full-decode"] = "ffprobe+ffmpeg-full-decode"
    scope: Literal["media-inspection-only"] = "media-inspection-only"
    files: list[InspectedFile]
    unavailable: list[str] = Field(
        default_factory=lambda: [
            "beats",
            "shot boundaries",
            "pose/action inference",
            "StyleDNA",
            "EDL",
        ]
    )


class InspectionRead(BaseModel):
    """Durable job identity and terminal result, with live observed progress."""

    operation: Operation = "decode"
    id: str
    project_id: str
    reference_asset_id: str
    source_asset_ids: list[str]
    state: Literal["queued", "running", "done", "failed", "cancelled", "interrupted"]
    percent: float = 0
    message: str = ""
    error: str | None = None
    stale: bool = False
    report: Annotated[InspectionReport | RhythmReport, Field(discriminator="scope")] | None = None

    @model_validator(mode="after")
    def completed_report_required(self) -> InspectionRead:
        """Reject success-shaped records without measured, committed report data."""
        if self.state == "done" and (self.report is None or self.percent != 100):
            raise ValueError("Completed inspection has no measured report")
        if self.report is not None:
            expected = (
                "media-inspection-only" if self.operation == "decode" else "audio-rhythm-only"
            )
            if self.report.scope != expected:
                raise ValueError("Report scope disagrees with job operation")
        return self
