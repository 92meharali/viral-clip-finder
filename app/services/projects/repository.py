"""Read-only queries for persisted projects and clips."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.database.models import AnalysisJobRecord, ClipRecord, ProjectRecord
from app.schemas.analyze import ClipSummaryResponse


@dataclass(frozen=True)
class ProjectSummary:
    """Domain summary for a stored project."""

    id: str
    video_id: str
    title: str
    channel: str | None
    duration_seconds: float
    webpage_url: str
    youtube_url: str
    transcript_language: str | None
    transcript_source: str | None
    clip_count: int
    latest_job_status: str | None
    created_at: datetime
    updated_at: datetime


class ProjectRepository:
    """Query persisted projects and clips."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_projects(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ProjectSummary], int]:
        """Return paginated project summaries and total count."""
        with self._session_factory() as session:
            total = session.scalar(select(func.count()).select_from(ProjectRecord)) or 0
            projects = session.scalars(
                select(ProjectRecord)
                .order_by(ProjectRecord.updated_at.desc())
                .offset(offset)
                .limit(limit)
            ).all()
            summaries = [self._to_summary(session, project) for project in projects]
            return summaries, int(total)

    def get_project(self, project_id: str) -> ProjectSummary | None:
        """Return a project summary by ID."""
        with self._session_factory() as session:
            project = session.get(ProjectRecord, project_id)
            if project is None:
                return None
            return self._to_summary(session, project)

    def get_project_clips(self, project_id: str) -> list[ClipSummaryResponse]:
        """Return ranked clips for a project from the latest completed job."""
        with self._session_factory() as session:
            project = session.get(ProjectRecord, project_id)
            if project is None:
                return []

            latest_job = session.scalar(
                select(AnalysisJobRecord)
                .where(
                    AnalysisJobRecord.project_id == project_id,
                    AnalysisJobRecord.status == "completed",
                )
                .order_by(AnalysisJobRecord.finished_at.desc())
                .limit(1)
            )
            if latest_job is None:
                return self._clips_for_project(session, project_id)

            return self._clips_for_job(session, latest_job.id)

    def list_clips(
        self,
        *,
        project_id: str | None = None,
        job_id: str | None = None,
        emotion: str | None = None,
        min_score: float | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ClipSummaryResponse], int]:
        """Return filtered clips and total count."""
        with self._session_factory() as session:
            query = select(ClipRecord)
            if project_id is not None:
                query = query.where(ClipRecord.project_id == project_id)
            if job_id is not None:
                query = query.where(ClipRecord.job_id == job_id)
            if emotion is not None:
                query = query.where(
                    func.lower(ClipRecord.emotion) == emotion.strip().lower()
                )
            if min_score is not None:
                query = query.where(ClipRecord.viral_score >= min_score)

            count_query = select(func.count()).select_from(query.subquery())
            total = session.scalar(count_query) or 0

            clips = session.scalars(
                query.order_by(ClipRecord.rank_score.desc(), ClipRecord.rank.asc())
                .offset(offset)
                .limit(limit)
            ).all()
            return [self._clip_to_response(clip) for clip in clips], int(total)

    def _to_summary(self, session: Session, project: ProjectRecord) -> ProjectSummary:
        clip_count = session.scalar(
            select(func.count())
            .select_from(ClipRecord)
            .where(ClipRecord.project_id == project.id)
        )
        latest_status = session.scalar(
            select(AnalysisJobRecord.status)
            .where(AnalysisJobRecord.project_id == project.id)
            .order_by(AnalysisJobRecord.created_at.desc())
            .limit(1)
        )
        return ProjectSummary(
            id=project.id,
            video_id=project.video_id,
            title=project.title,
            channel=project.channel,
            duration_seconds=project.duration_seconds,
            webpage_url=project.webpage_url,
            youtube_url=project.youtube_url,
            transcript_language=project.transcript_language,
            transcript_source=project.transcript_source,
            clip_count=int(clip_count or 0),
            latest_job_status=latest_status,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    def _clips_for_project(self, session: Session, project_id: str) -> list[ClipSummaryResponse]:
        clips = session.scalars(
            select(ClipRecord)
            .where(ClipRecord.project_id == project_id)
            .order_by(ClipRecord.rank.asc())
        ).all()
        return [self._clip_to_response(clip) for clip in clips]

    def _clips_for_job(self, session: Session, job_id: str) -> list[ClipSummaryResponse]:
        clips = session.scalars(
            select(ClipRecord)
            .where(ClipRecord.job_id == job_id)
            .order_by(ClipRecord.rank.asc())
        ).all()
        return [self._clip_to_response(clip) for clip in clips]

    @staticmethod
    def _clip_to_response(clip: ClipRecord) -> ClipSummaryResponse:
        return ClipSummaryResponse(
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
