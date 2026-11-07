"""Typed FFmpeg cut candidates, explicitly not pretrained/semantic scene analysis."""

from __future__ import annotations

from itertools import pairwise
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas_rhythm import Digest


class CutCandidate(BaseModel):
    """One threshold crossing reported by the native scdet filter, not a shot label."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    frame_index: int = Field(ge=1)
    time_seconds: float = Field(gt=0)
    score_percent: float = Field(ge=10, le=100)


class SceneEstimate(BaseModel):
    """Observed first-video-frame-relative timings; no inferred edit or action labels."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    method: Literal["ffmpeg.scdet"] = "ffmpeg.scdet"
    time_origin: Literal["first-decoded-video-frame"] = "first-decoded-video-frame"
    threshold_percent: Literal[10] = 10
    scaled_width: Literal[320] = 320
    frames_analyzed: int = Field(ge=1, le=36000)
    first_frame_pts_seconds: float
    decoded_span_seconds: float = Field(ge=0, le=600.25)
    candidates: list[CutCandidate] = Field(max_length=36000)

    @model_validator(mode="after")
    def consistent_candidates(self) -> SceneEstimate:
        """Reject unobserved, unordered or out-of-range candidates."""
        if any(
            c.frame_index >= self.frames_analyzed
            or c.time_seconds > self.decoded_span_seconds + 1e-5
            for c in self.candidates
        ):
            raise ValueError("Cut candidate is outside observed video frames")
        if any(
            a.time_seconds >= b.time_seconds or a.frame_index >= b.frame_index
            for a, b in pairwise(self.candidates)
        ):
            raise ValueError("Cut candidates must follow strictly increasing frame/time order")
        return self


class SceneFile(BaseModel):
    """Original asset identity and candidate-only observation, or an explicit no-video skip."""

    model_config = ConfigDict(allow_inf_nan=False)
    asset_id: str
    role: str
    name: str
    sha256: Digest
    size_bytes: int = Field(ge=0)
    mtime_ns: str
    duration: float = Field(gt=0)
    has_audio: bool
    has_video: bool
    status: Literal["candidates", "no-candidates", "no-video"]
    estimate: SceneEstimate | None = None

    @model_validator(mode="after")
    def honest_video_state(self) -> SceneFile:
        """Distinguish a missing video stream from a measured clip without candidates."""
        if self.status == "no-video":
            if self.has_video or self.estimate is not None:
                raise ValueError("No-video input cannot contain detected candidates")
        elif not self.has_video or self.estimate is None:
            raise ValueError("Video result requires observed native frame data")
        elif (self.status == "candidates") != bool(self.estimate.candidates):
            raise ValueError("Cut status and measured candidates disagree")
        return self


class SceneReport(BaseModel):
    """Rule-based cut candidates only, not TransNetV2, StyleDNA or edit-ready scene labels."""

    version: Literal[1] = 1
    scope: Literal["shot-candidates-only"] = "shot-candidates-only"
    method: Literal["ffprobe-lavfi+scdet"] = "ffprobe-lavfi+scdet"
    files: list[SceneFile] = Field(min_length=1, max_length=101)
    unavailable: list[str] = Field(
        default_factory=lambda: [
            "TransNetV2 inference",
            "semantic shot labels",
            "pose/action inference",
            "StyleDNA",
            "EDL",
        ]
    )
