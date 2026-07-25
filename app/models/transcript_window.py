"""Transcript window models for chunked LLM analysis."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.transcript import TranscriptSegment


class TranscriptWindow(BaseModel):
    """A time-bounded slice of transcript segments for LLM analysis."""

    index: int = Field(..., ge=0, description="Zero-based window index")
    start_seconds: float = Field(..., ge=0, description="Window start in seconds")
    end_seconds: float = Field(..., gt=0, description="Window end in seconds")
    segments: list[TranscriptSegment] = Field(
        default_factory=list,
        description="Segments fully contained in this window",
    )

    model_config = {"frozen": True}

    @property
    def duration_seconds(self) -> float:
        """Window duration."""
        return max(0.0, self.end_seconds - self.start_seconds)

    @property
    def segment_count(self) -> int:
        """Number of segments in the window."""
        return len(self.segments)


class TranscriptWindowResult(BaseModel):
    """Output from transcript window generation."""

    windows: list[TranscriptWindow] = Field(default_factory=list)
    total_duration_seconds: float = Field(..., ge=0)
    window_size_seconds: float = Field(..., gt=0)
    overlap_seconds: float = Field(..., ge=0)

    model_config = {"frozen": True}

    @property
    def window_count(self) -> int:
        """Number of generated windows."""
        return len(self.windows)

    @property
    def used_windowing(self) -> bool:
        """Whether the transcript required more than one window."""
        return self.window_count > 1
