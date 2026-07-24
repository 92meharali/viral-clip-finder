"""Quality check result models."""

from enum import Enum

from pydantic import BaseModel, Field


class QualityIssueCode(str, Enum):
    """Machine-readable quality failure codes."""

    TOO_SHORT = "too_short"
    TOO_LONG = "too_long"
    TOO_MUCH_SILENCE = "too_much_silence"
    REPEATED_DIALOGUE = "repeated_dialogue"
    LOW_CONFIDENCE = "low_confidence"


class QualityIssue(BaseModel):
    """A single quality check failure."""

    code: QualityIssueCode = Field(..., description="Failure category")
    message: str = Field(..., min_length=1, description="Human-readable explanation")

    model_config = {"frozen": True}


class ClipQualityResult(BaseModel):
    """Quality check outcome for a single clip."""

    index: int = Field(..., ge=1, description="1-based clip number")
    clip_start: str = Field(..., description="Clip start timestamp")
    clip_end: str = Field(..., description="Clip end timestamp")
    viral_score: float = Field(..., ge=0, description="LLM viral score")
    passed: bool = Field(..., description="Whether the clip passed all checks")
    issues: list[QualityIssue] = Field(default_factory=list, description="Detected issues")

    model_config = {"frozen": True}


class QualityFilterResult(BaseModel):
    """Aggregated quality filter results for a clip batch."""

    passed: list[int] = Field(
        default_factory=list,
        description="Indices of clips that passed (1-based)",
    )
    rejected: list[ClipQualityResult] = Field(
        default_factory=list,
        description="Rejected clips with issue details",
    )
    total: int = Field(..., ge=0, description="Total clips evaluated")

    model_config = {"frozen": True}
