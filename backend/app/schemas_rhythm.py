"""Typed rhythm observations, explicitly separate from media decode and model inference."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class RhythmEstimate(BaseModel):
    """Validated JSON boundary for the isolated librosa worker's PCM measurement."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    time_origin: Literal["extracted-pcm-start"] = "extracted-pcm-start"
    sha256: Digest
    samples_analyzed: int = Field(ge=22050, le=13230000)
    duration_seconds: float = Field(ge=1, le=600)
    tempo_bpm: float | None = Field(default=None, gt=0)
    beat_times_seconds: list[float] = Field(max_length=30000)
    library_version: Literal["0.11.0"]
    method: Literal["librosa.beat.beat_track"]
    scope: Literal["audio-rhythm-only"]

    @model_validator(mode="after")
    def consistent_measurement(self) -> RhythmEstimate:
        """No fabricated BPM, out-of-range beats or mismatched sample duration."""
        if (self.tempo_bpm is None) != (not self.beat_times_seconds):
            raise ValueError("Tempo and detected beats disagree")
        if abs(self.samples_analyzed / 22050 - self.duration_seconds) > 1 / 22050:
            raise ValueError("PCM sample count and duration disagree")
        if any(not 0 <= t <= self.duration_seconds for t in self.beat_times_seconds):
            raise ValueError("Beat timestamp outside the measured PCM")
        if any(
            a >= b
            for a, b in zip(self.beat_times_seconds, self.beat_times_seconds[1:], strict=False)
        ):
            raise ValueError("Beat timestamps must be strictly increasing")
        return self


class RhythmFile(BaseModel):
    """Original media identity/hash and optional derived-PCM rhythm estimate."""

    model_config = ConfigDict(allow_inf_nan=False)
    asset_id: str
    role: str
    name: str
    sha256: Digest
    size_bytes: int = Field(ge=0)
    mtime_ns: str
    duration: float = Field(gt=0)
    has_audio: bool
    status: Literal["estimated", "no-beats", "no-audio"]
    estimate: RhythmEstimate | None = None

    @model_validator(mode="after")
    def honest_audio_state(self) -> RhythmFile:
        """Distinguish a missing stream, silence and a detected rhythm."""
        if self.status == "no-audio":
            if self.has_audio or self.estimate is not None:
                raise ValueError("No-audio result cannot contain a rhythm estimate")
        elif not self.has_audio or self.estimate is None:
            raise ValueError("Audio result requires a PCM measurement")
        elif (self.status == "estimated") != bool(self.estimate.beat_times_seconds):
            raise ValueError("Rhythm status disagrees with detected beats")
        return self


class RhythmReport(BaseModel):
    """Estimated audio timing only; no shot/pose/sports/DNA/EDL claims."""

    version: Literal[1] = 1
    scope: Literal["audio-rhythm-only"] = "audio-rhythm-only"
    method: Literal["ffmpeg-pcm+librosa.beat.beat_track"] = "ffmpeg-pcm+librosa.beat.beat_track"
    files: list[RhythmFile] = Field(min_length=1, max_length=101)
    unavailable: list[str] = Field(
        default_factory=lambda: ["shot boundaries", "pose/action inference", "StyleDNA", "EDL"]
    )
