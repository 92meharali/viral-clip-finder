"""API schemas for analysis jobs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.exceptions import YouTubeIngestionError
from app.providers.factory import SUPPORTED_PROVIDERS
from app.services.analysis.models import (
    AnalysisJob,
    AnalysisJobResult,
    AnalysisJobStatus,
    AnalysisStage,
)
from app.services.youtube.urls import extract_video_id


class AnalyzeRequest(BaseModel):
    """Request body for starting a YouTube analysis job."""

    url: str = Field(..., min_length=1, description="YouTube watch URL or video ID")
    provider: str | None = Field(
        default=None,
        description="AI provider override (cursor or openai)",
    )
    top_n: int | None = Field(
        default=None,
        ge=1,
        le=100,
        description="Maximum number of ranked clips to return",
    )

    @field_validator("url")
    @classmethod
    def validate_youtube_url(cls, value: str) -> str:
        """Ensure the URL resolves to a YouTube video ID."""
        try:
            extract_video_id(value)
        except YouTubeIngestionError as exc:
            raise ValueError(str(exc)) from exc
        return value.strip()

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, value: str | None) -> str | None:
        """Ensure the provider name is supported when provided."""
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in SUPPORTED_PROVIDERS:
            supported = ", ".join(sorted(SUPPORTED_PROVIDERS))
            raise ValueError(f"Unsupported provider '{value}'. Supported: {supported}")
        return normalized


class ClipSummaryResponse(BaseModel):
    """Ranked clip returned by the analysis API."""

    rank: int
    start: str
    end: str
    duration_seconds: float
    viral_score: float
    rank_score: float
    emotion: str
    hook: str
    reason: str
    summary: str


class AnalysisJobResultResponse(BaseModel):
    """Completed analysis payload."""

    video_id: str
    title: str
    channel: str | None
    duration_seconds: float
    webpage_url: str
    transcript_language: str
    transcript_source: str
    transcript_segments: int
    candidate_windows: int
    clips_analyzed: int
    clips_ranked: int
    clips: list[ClipSummaryResponse]

    @classmethod
    def from_result(cls, result: AnalysisJobResult) -> AnalysisJobResultResponse:
        """Convert a domain result into an API response."""
        return cls(
            video_id=result.video_id,
            title=result.title,
            channel=result.channel,
            duration_seconds=result.duration_seconds,
            webpage_url=result.webpage_url,
            transcript_language=result.transcript_language,
            transcript_source=result.transcript_source,
            transcript_segments=result.transcript_segments,
            candidate_windows=result.candidate_windows,
            clips_analyzed=result.clips_analyzed,
            clips_ranked=result.clips_ranked,
            clips=[
                ClipSummaryResponse(
                    rank=clip.rank,
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
                for clip in result.clips
            ],
        )


class AnalysisJobResponse(BaseModel):
    """Analysis job status returned by the API."""

    id: str
    url: str
    video_id: str | None
    provider: str
    top_n: int | None
    status: AnalysisJobStatus
    stage: AnalysisStage | None
    progress_message: str | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    result: AnalysisJobResultResponse | None

    @classmethod
    def from_job(cls, job: AnalysisJob) -> AnalysisJobResponse:
        """Convert a domain job into an API response."""
        return cls(
            id=job.id,
            url=job.url,
            video_id=job.video_id,
            provider=job.provider,
            top_n=job.top_n,
            status=job.status,
            stage=job.stage,
            progress_message=job.progress_message,
            error=job.error,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            result=(
                AnalysisJobResultResponse.from_result(job.result)
                if job.result is not None
                else None
            ),
        )
