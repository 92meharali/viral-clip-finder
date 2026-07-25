"""Map between analysis domain models and ORM records."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database.models import AnalysisJobRecord, ClipRecord, ProjectRecord, utc_now
from app.services.analysis.models import (
    AnalysisJob,
    AnalysisJobResult,
    AnalysisJobStatus,
    AnalysisStage,
    ClipSummary,
)
from app.utils.time_utils import parse_timestamp


def job_to_record(job: AnalysisJob) -> AnalysisJobRecord:
    """Convert a domain job into an ORM record without clips."""
    result = job.result
    return AnalysisJobRecord(
        id=job.id,
        project_id=None,
        youtube_url=job.url,
        video_id=job.video_id,
        provider=job.provider,
        top_n=job.top_n,
        status=job.status.value,
        stage=job.stage.value if job.stage is not None else None,
        progress_message=job.progress_message,
        error=job.error,
        transcript_segments=result.transcript_segments if result else None,
        candidate_windows=result.candidate_windows if result else None,
        llm_windows_analyzed=result.llm_windows_analyzed if result else None,
        clips_analyzed=result.clips_analyzed if result else None,
        clips_ranked=result.clips_ranked if result else None,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


def record_to_job(record: AnalysisJobRecord) -> AnalysisJob:
    """Convert an ORM record into a domain job."""
    result = None
    if record.status == AnalysisJobStatus.COMPLETED.value and record.video_id and record.clips:
        sorted_clips = sorted(record.clips, key=lambda clip: clip.rank)
        result = AnalysisJobResult(
            video_id=record.video_id,
            title=record.project.title if record.project else record.video_id,
            channel=record.project.channel if record.project else None,
            duration_seconds=record.project.duration_seconds if record.project else 0.0,
            webpage_url=record.project.webpage_url if record.project else record.youtube_url,
            transcript_language=record.project.transcript_language if record.project else "",
            transcript_source=record.project.transcript_source if record.project else "",
            transcript_segments=record.transcript_segments or 0,
            candidate_windows=record.candidate_windows or 0,
            llm_windows_analyzed=record.llm_windows_analyzed or 1,
            clips_analyzed=record.clips_analyzed or 0,
            clips_ranked=record.clips_ranked or 0,
            clips=[
                ClipSummary(
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
                for clip in sorted_clips
            ],
        )

    return AnalysisJob(
        id=record.id,
        url=record.youtube_url,
        video_id=record.video_id,
        provider=record.provider,
        top_n=record.top_n,
        status=AnalysisJobStatus(record.status),
        stage=AnalysisStage(record.stage) if record.stage else None,
        progress_message=record.progress_message,
        error=record.error,
        created_at=record.created_at,
        started_at=record.started_at,
        finished_at=record.finished_at,
        result=result,
    )


def upsert_project(session: Session, result: AnalysisJobResult, youtube_url: str) -> ProjectRecord:
    """Create or update a project from a completed analysis result."""
    project = session.scalar(
        select(ProjectRecord).where(ProjectRecord.video_id == result.video_id)
    )
    if project is None:
        project = ProjectRecord(
            id=str(uuid4()),
            video_id=result.video_id,
            youtube_url=youtube_url,
            title=result.title,
            channel=result.channel,
            duration_seconds=result.duration_seconds,
            webpage_url=result.webpage_url,
            thumbnail_url=None,
            description=None,
            transcript_language=result.transcript_language,
            transcript_source=result.transcript_source,
        )
        session.add(project)
    else:
        project.youtube_url = youtube_url
        project.title = result.title
        project.channel = result.channel
        project.duration_seconds = result.duration_seconds
        project.webpage_url = result.webpage_url
        project.transcript_language = result.transcript_language
        project.transcript_source = result.transcript_source
        project.updated_at = utc_now()

    return project


def replace_job_clips(
    session: Session,
    *,
    job: AnalysisJobRecord,
    project: ProjectRecord,
    clips: list[ClipSummary],
) -> None:
    """Replace persisted clips for a completed job."""
    for existing in list(job.clips):
        session.delete(existing)

    for clip in clips:
        start_seconds = parse_timestamp(clip.start)
        end_seconds = parse_timestamp(clip.end)
        session.add(
            ClipRecord(
                id=str(uuid4()),
                project_id=project.id,
                job_id=job.id,
                rank=clip.rank,
                start=clip.start,
                end=clip.end,
                start_seconds=start_seconds,
                end_seconds=end_seconds,
                duration_seconds=clip.duration_seconds,
                viral_score=clip.viral_score,
                rank_score=clip.rank_score,
                emotion=clip.emotion,
                hook=clip.hook,
                reason=clip.reason,
                summary=clip.summary,
            )
        )


def load_job(session: Session, job_id: str) -> AnalysisJobRecord | None:
    """Load a job with related project and clips."""
    return session.scalar(
        select(AnalysisJobRecord)
        .where(AnalysisJobRecord.id == job_id)
        .options(
            selectinload(AnalysisJobRecord.project),
            selectinload(AnalysisJobRecord.clips),
        )
    )
