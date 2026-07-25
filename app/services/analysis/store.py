"""In-memory analysis job storage."""

from __future__ import annotations

import threading
from typing import Protocol

from app.services.analysis.models import AnalysisJob


class AnalysisJobStore(Protocol):
    """Persistence interface for analysis jobs.

    Swap this implementation for Redis or SQLAlchemy without changing callers.
    """

    def create(self, job: AnalysisJob) -> AnalysisJob:
        """Persist a new job."""

    def get(self, job_id: str) -> AnalysisJob | None:
        """Return a job by ID."""

    def update(self, job: AnalysisJob) -> AnalysisJob:
        """Replace a stored job."""

    def list_recent(self, *, limit: int = 20) -> list[AnalysisJob]:
        """Return the most recently created jobs."""


class InMemoryAnalysisJobStore:
    """Thread-safe in-process job store for development and tests."""

    def __init__(self) -> None:
        self._jobs: dict[str, AnalysisJob] = {}
        self._lock = threading.Lock()

    def create(self, job: AnalysisJob) -> AnalysisJob:
        with self._lock:
            self._jobs[job.id] = job
            return job

    def get(self, job_id: str) -> AnalysisJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job: AnalysisJob) -> AnalysisJob:
        with self._lock:
            self._jobs[job.id] = job
            return job

    def list_recent(self, *, limit: int = 20) -> list[AnalysisJob]:
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda item: item.created_at, reverse=True)
            return jobs[:limit]

    def clear(self) -> None:
        """Remove all jobs (testing helper)."""
        with self._lock:
            self._jobs.clear()
