"""Candidate window models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CandidateWindow(BaseModel):
    """A scored time span that may become a viral clip."""

    start_seconds: float = Field(..., ge=0)
    end_seconds: float = Field(..., gt=0)
    score: float = Field(..., ge=0, le=10)
    labels: list[str] = Field(default_factory=list)
    signal_types: list[str] = Field(default_factory=list)
    reasoning: str = Field(default="", description="Why this window was proposed")

    model_config = {"frozen": True}

    @property
    def duration_seconds(self) -> float:
        """Window duration."""
        return max(0.0, self.end_seconds - self.start_seconds)


class CandidateWindowResult(BaseModel):
    """Output from candidate window generation."""

    windows: list[CandidateWindow] = Field(default_factory=list)
    signal_count: int = Field(default=0, ge=0)

    model_config = {"frozen": True}

    @property
    def window_count(self) -> int:
        """Number of candidate windows."""
        return len(self.windows)
