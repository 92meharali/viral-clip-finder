"""Importance scoring data models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ImportanceFactor(BaseModel):
    """A single factor contributing to a track's importance score."""

    factor_type: str = Field(..., min_length=1)
    score: float = Field(..., ge=0, le=1)

    model_config = {"frozen": True}


class ImportanceScore(BaseModel):
    """Importance score for one tracked person at a point in time."""

    track_id: str = Field(..., min_length=1)
    score: float = Field(..., ge=0, le=1, description="Fused importance score")
    reasoning: str = Field(
        ...,
        min_length=1,
        description="Human-readable summary of dominant factors",
    )
    factors: list[ImportanceFactor] = Field(default_factory=list)

    model_config = {"frozen": True}


class FrameImportance(BaseModel):
    """Importance scores for all visible tracks in one frame."""

    frame_number: int = Field(..., ge=0)
    timestamp: float = Field(..., ge=0)
    scores: list[ImportanceScore] = Field(default_factory=list)

    model_config = {"frozen": True}

    @property
    def top_track_id(self) -> str | None:
        """Track with the highest importance score in this frame."""
        if not self.scores:
            return None
        return max(self.scores, key=lambda item: item.score).track_id


class ImportanceScoringResult(BaseModel):
    """Full importance scoring output for a tracked sequence."""

    frames: list[FrameImportance] = Field(default_factory=list)

    model_config = {"frozen": True}

    def top_track_at(self, frame_number: int) -> str | None:
        """Return the most important track id for a frame, if scored."""
        for frame in self.frames:
            if frame.frame_number == frame_number:
                return frame.top_track_id
        return None
