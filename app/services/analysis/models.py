"""Analysis job domain models."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field

from app.models.clip import RankedClip


def utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(UTC)


class AnalysisJobStatus(StrEnum):
    """Lifecycle states for an analysis job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisStage(StrEnum):
    """Pipeline stages reported while a job is running."""

    INGESTING = "ingesting"
    GENERATING_WINDOWS = "generating_windows"
    ANALYZING = "analyzing"
    RANKING = "ranking"
    FINALIZING = "finalizing"


class ClipSummary(BaseModel):
    """API-friendly summary of a ranked viral clip."""

    rank: int = Field(..., ge=1, description="Rank position after scoring")
    start: str = Field(..., description="Clip start timestamp")
    end: str = Field(..., description="Clip end timestamp")
    duration_seconds: float = Field(..., gt=0, description="Clip duration in seconds")
    viral_score: float = Field(..., ge=0, le=10, description="Model viral score")
    rank_score: float = Field(..., ge=0, description="Composite ranking score")
    emotion: str = Field(..., description="Primary emotion")
    hook: str = Field(..., description="Short social hook")
    reason: str = Field(..., description="Why this moment is engaging")
    summary: str = Field(..., description="Brief clip summary")

    @classmethod
    def from_ranked_clip(cls, clip: RankedClip, *, rank: int) -> ClipSummary:
        """Build a summary from a ranked clip."""
        return cls(
            rank=rank,
            start=clip.start,
            end=clip.end,
            duration_seconds=clip.duration_seconds,
            viral_score=clip.viral_score,
            rank_score=clip.rank_score,
            emotion=clip.emotion,
            hook=clip.hook,
            reason=clip.reason,
            summary=clip.summary,
        )


class AnalysisJobResult(BaseModel):
    """Successful analysis output attached to a completed job."""

    video_id: str
    title: str
    channel: str | None = None
    duration_seconds: float = Field(..., ge=0)
    webpage_url: str
    transcript_language: str
    transcript_source: str
    transcript_segments: int = Field(..., ge=0)
    candidate_windows: int = Field(..., ge=0)
    clips_analyzed: int = Field(..., ge=0)
    clips_ranked: int = Field(..., ge=0)
    clips: list[ClipSummary] = Field(default_factory=list)


class AnalysisJob(BaseModel):
    """Tracked background analysis job."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    url: str
    video_id: str | None = None
    provider: str
    top_n: int | None = None
    status: AnalysisJobStatus = AnalysisJobStatus.PENDING
    stage: AnalysisStage | None = None
    progress_message: str | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result: AnalysisJobResult | None = None

    model_config = {"frozen": True}
