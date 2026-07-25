"""Viral clip data models."""

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.utils.time_utils import format_timestamp, parse_timestamp


class ViralClipBase(BaseModel):
    """Raw viral clip fields returned by the LLM."""

    model_config = ConfigDict(populate_by_name=True)

    start: str = Field(..., description="Clip start timestamp (HH:MM:SS or MM:SS)")
    end: str = Field(..., description="Clip end timestamp (HH:MM:SS or MM:SS)")
    reason: str = Field(..., min_length=1, description="Why this moment is viral")
    viral_score: float = Field(
        ...,
        ge=0,
        le=10,
        alias="score",
        description="Viral potential score 0-10",
    )
    emotion: str = Field(..., min_length=1, description="Primary emotion detected")
    hook: str = Field(..., min_length=1, description="Short hook for social media")
    summary: str = Field(default="", description="Brief summary of the clip")

    @field_validator("start", "end")
    @classmethod
    def validate_timestamp(cls, value: str) -> str:
        """Ensure timestamps are parseable and normalize to HH:MM:SS."""
        seconds = parse_timestamp(value)
        return format_timestamp(seconds)

    @model_validator(mode="after")
    def default_summary_from_reason(self) -> "ViralClipBase":
        """Use reason as summary when the model omits summary."""
        if not self.summary.strip():
            self.summary = self.reason
        return self


class ViralClip(ViralClipBase):
    """A detected viral moment with computed timing fields."""

    start_seconds: float = Field(..., ge=0, description="Start time in seconds")
    end_seconds: float = Field(..., ge=0, description="End time in seconds")
    duration_seconds: float = Field(..., gt=0, description="Clip duration in seconds")

    @model_validator(mode="after")
    def validate_duration(self) -> "ViralClip":
        """Ensure end time is after start time."""
        if self.end_seconds <= self.start_seconds:
            raise ValueError(f"end ({self.end}) must be after start ({self.start})")
        return self

    @classmethod
    def from_base(cls, clip: ViralClipBase) -> "ViralClip":
        """Create a ViralClip with computed second fields from LLM output."""
        start_seconds = parse_timestamp(clip.start)
        end_seconds = parse_timestamp(clip.end)
        return cls(
            **clip.model_dump(),
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            duration_seconds=end_seconds - start_seconds,
        )

    model_config = {"frozen": True}


class ClipAnalysisResponse(BaseModel):
    """Structured JSON response expected from the LLM."""

    clips: list[ViralClipBase] = Field(default_factory=list)


class RankedClip(ViralClip):
    """A viral clip enriched with ranking metadata."""

    rank_score: float = Field(..., ge=0, description="Composite ranking score")
    emotion_intensity: float = Field(
        ..., ge=0, le=1, description="Normalized emotion intensity weight"
    )
    dialogue_density: float = Field(
        ..., ge=0, description="Dialogue density (characters per second)"
    )
    length_score: float = Field(..., ge=0, le=1, description="Score based on ideal clip duration")

    model_config = {"frozen": True}
