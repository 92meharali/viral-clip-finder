"""Active speaker estimation data models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SignalContribution(BaseModel):
    """A single signal's contribution to a track's speaker confidence."""

    signal_type: str = Field(..., min_length=1)
    score: float = Field(..., ge=0, le=1)

    model_config = {"frozen": True}


class FrameSpeakerConfidence(BaseModel):
    """Per-frame speaker confidence for every visible track."""

    frame_number: int = Field(..., ge=0)
    timestamp: float = Field(..., ge=0)
    active_track_id: str | None = Field(
        default=None,
        description="Highest-confidence speaking track, if above threshold",
    )
    track_scores: dict[str, float] = Field(default_factory=dict)
    signal_breakdown: dict[str, list[SignalContribution]] = Field(
        default_factory=dict,
        description="Per-track signal contributions",
    )

    model_config = {"frozen": True}


class ActiveSpeaker(BaseModel):
    """A time span where one tracked person is estimated to be speaking."""

    track_id: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0, le=1, description="Mean confidence across the span")
    start_time: float = Field(..., ge=0)
    end_time: float = Field(..., ge=0)
    speaker_label: str | None = Field(
        default=None,
        description="Transcript speaker label when diarization is available",
    )

    model_config = {"frozen": True}

    @property
    def duration_seconds(self) -> float:
        """Span length in seconds."""
        return max(0.0, self.end_time - self.start_time)


class SpeakerEstimationResult(BaseModel):
    """Full active speaker estimation output."""

    segments: list[ActiveSpeaker] = Field(default_factory=list)
    frames: list[FrameSpeakerConfidence] = Field(default_factory=list)

    model_config = {"frozen": True}

    @property
    def segment_count(self) -> int:
        """Number of active speaker segments."""
        return len(self.segments)
