"""SQLAlchemy-backed analysis job store."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.database.mappers import (
    job_to_record,
    load_job,
    record_to_job,
    replace_job_clips,
    upsert_project,
)
from app.database.models import AnalysisJobRecord
from app.services.analysis.models import AnalysisJob, AnalysisJobStatus


class SqlAlchemyAnalysisJobStore:
    """Persist analysis jobs, projects, and clips in SQLAlchemy."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(self, job: AnalysisJob) -> AnalysisJob:
        with self._session_factory() as session:
            record = job_to_record(job)
            session.add(record)
            self._apply_job_state(session, record, job)
            session.commit()
            loaded = load_job(session, job.id)
            if loaded is None:
                raise RuntimeError(f"Failed to persist analysis job {job.id}")
            return record_to_job(loaded)

    def get(self, job_id: str) -> AnalysisJob | None:
        with self._session_factory() as session:
            record = load_job(session, job_id)
            return record_to_job(record) if record is not None else None

    def update(self, job: AnalysisJob) -> AnalysisJob:
        with self._session_factory() as session:
            record = load_job(session, job.id)
            if record is None:
                raise KeyError(f"Analysis job not found: {job.id}")

            record.youtube_url = job.url
            record.video_id = job.video_id
            record.provider = job.provider
            record.top_n = job.top_n
            record.status = job.status.value
            record.stage = job.stage.value if job.stage is not None else None
            record.progress_message = job.progress_message
            record.error = job.error
            record.started_at = job.started_at
            record.finished_at = job.finished_at
            self._apply_job_state(session, record, job)

            session.commit()
            refreshed = load_job(session, job.id)
            if refreshed is None:
                raise RuntimeError(f"Failed to refresh analysis job {job.id}")
            return record_to_job(refreshed)

    def list_recent(self, *, limit: int = 20) -> list[AnalysisJob]:
        with self._session_factory() as session:
            records = session.scalars(
                select(AnalysisJobRecord)
                .order_by(AnalysisJobRecord.created_at.desc())
                .limit(limit)
            ).all()
            return [record_to_job(record) for record in records]

    @staticmethod
    def _apply_job_state(
        session: Session,
        record: AnalysisJobRecord,
        job: AnalysisJob,
    ) -> None:
        """Persist result metadata, project, and clips when available."""
        if job.result is None:
            return

        record.transcript_segments = job.result.transcript_segments
        record.candidate_windows = job.result.candidate_windows
        record.llm_windows_analyzed = job.result.llm_windows_analyzed
        record.clips_analyzed = job.result.clips_analyzed
        record.clips_ranked = job.result.clips_ranked

        if job.status == AnalysisJobStatus.COMPLETED:
            project = upsert_project(session, job.result, job.url)
            record.project_id = project.id
            replace_job_clips(
                session,
                job=record,
                project=project,
                clips=job.result.clips,
            )
