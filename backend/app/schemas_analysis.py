"""Analysis orchestration report — honest blocking, no synthetic labels."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AnalysisFile(BaseModel):
    """One asset's contribution — provenance only, no inference when blocked."""

    model_config = ConfigDict(allow_inf_nan=False)
    asset_id: str
    role: str
    name: str
    sha256: str
    size_bytes: int
    mtime_ns: str
    duration: float
    has_audio: bool
    has_video: bool


class AnalysisReport(BaseModel):
    """Terminal orchestration report — lists verified inputs, not generated labels."""

    version: Literal[1] = 1
    method: Literal["registry-checked-orchestration"] = "registry-checked-orchestration"
    scope: Literal["analysis-orchestration-only"] = "analysis-orchestration-only"
    files: list[AnalysisFile]
    unavailable: list[str] = Field(
        default_factory=lambda: [
            "shot boundaries",
            "pose/action inference",
            "StyleDNA",
            "EDL",
        ]
    )
    # When models are present, downstream DNA/EDL would be added here — not faked.
