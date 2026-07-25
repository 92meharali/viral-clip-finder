"""Analysis job lifecycle management."""

from __future__ import annotations

from loguru import logger

from app.core.config import Settings, get_settings
from app.services.analysis.models import (
    AnalysisJob,
    AnalysisJobStatus,
    AnalysisStage,
    utc_now,
)
from app.services.analysis.pipeline import AnalysisPipeline
from app.services.analysis.store import AnalysisJobStore, InMemoryAnalysisJobStore
from app.services.youtube.urls import extract_video_id


class AnalysisJobService:
    """Create, schedule, and execute background analysis jobs."""

    def __init__(
        self,
        store: AnalysisJobStore,
        settings: Settings | None = None,
        pipeline: AnalysisPipeline | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._store = store
        self._pipeline = pipeline or AnalysisPipeline(self.settings)

    def create_job(
        self,
        url: str,
        *,
        provider: str | None = None,
        top_n: int | None = None,
    ) -> AnalysisJob:
        """Validate the URL and enqueue a new pending job."""
        video_id = extract_video_id(url)
        resolved_provider = (provider or self.settings.ai_provider).strip().lower()
        job = AnalysisJob(
            url=url.strip(),
            video_id=video_id,
            provider=resolved_provider,
            top_n=top_n,
        )
        created = self._store.create(job)
        logger.info(
            "Created analysis job {job_id} for video {video_id}",
            job_id=created.id,
            video_id=video_id,
        )
        return created

    def get_job(self, job_id: str) -> AnalysisJob | None:
        """Return a job by ID."""
        return self._store.get(job_id)

    def run_job(self, job_id: str) -> AnalysisJob:
        """Execute a job synchronously (intended for background workers)."""
        job = self._store.get(job_id)
        if job is None:
            raise KeyError(f"Analysis job not found: {job_id}")

        running = job.model_copy(
            update={
                "status": AnalysisJobStatus.RUNNING,
                "started_at": utc_now(),
                "error": None,
                "progress_message": "Job started",
            }
        )
        self._store.update(running)

        try:
            result = self._pipeline.run(
                running.url,
                provider=running.provider,
                top_n=running.top_n,
                on_progress=lambda stage, message: self._update_progress(job_id, stage, message),
            )
            finished = self._require_job(job_id).model_copy(
                update={
                    "status": AnalysisJobStatus.COMPLETED,
                    "stage": None,
                    "progress_message": "Analysis complete",
                    "finished_at": utc_now(),
                    "result": result,
                    "error": None,
                }
            )
            self._store.update(finished)
            logger.info("Analysis job {job_id} completed", job_id=job_id)
            return finished
        except Exception as exc:
            failed = self._require_job(job_id).model_copy(
                update={
                    "status": AnalysisJobStatus.FAILED,
                    "stage": None,
                    "progress_message": None,
                    "finished_at": utc_now(),
                    "error": str(exc),
                }
            )
            self._store.update(failed)
            logger.error("Analysis job {job_id} failed: {error}", job_id=job_id, error=exc)
            return failed

    def _update_progress(self, job_id: str, stage: AnalysisStage, message: str) -> None:
        current = self._require_job(job_id)
        updated = current.model_copy(
            update={
                "stage": stage,
                "progress_message": message,
            }
        )
        self._store.update(updated)

    def _require_job(self, job_id: str) -> AnalysisJob:
        job = self._store.get(job_id)
        if job is None:
            raise KeyError(f"Analysis job not found: {job_id}")
        return job


def build_default_job_service(
    store: AnalysisJobStore | None = None,
    settings: Settings | None = None,
) -> AnalysisJobService:
    """Create a job service with default dependencies."""
    resolved_settings = settings or get_settings()
    resolved_store = store or InMemoryAnalysisJobStore()
    return AnalysisJobService(resolved_store, resolved_settings)
