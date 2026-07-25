"""Tests for SQLAlchemy project persistence."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.database.session import Database
from app.services.analysis.models import (
    AnalysisJob,
    AnalysisJobResult,
    AnalysisJobStatus,
    AnalysisStage,
    ClipSummary,
    utc_now,
)
from app.services.analysis.service import AnalysisJobService
from app.services.analysis.sqlalchemy_store import SqlAlchemyAnalysisJobStore


@pytest.fixture
def database() -> Database:
    db = Database(Settings(database_url="sqlite:///:memory:"))
    db.create_tables()
    return db


@pytest.fixture
def store(database: Database) -> SqlAlchemyAnalysisJobStore:
    return SqlAlchemyAnalysisJobStore(database.session_factory)


def _completed_result() -> AnalysisJobResult:
    return AnalysisJobResult(
        video_id="dQw4w9WgXcQ",
        title="Never Gonna Give You Up",
        channel="Rick Astley",
        duration_seconds=212.0,
        webpage_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        transcript_language="en",
        transcript_source="manual",
        transcript_segments=42,
        candidate_windows=3,
        llm_windows_analyzed=2,
        clips_analyzed=5,
        clips_ranked=1,
        clips=[
            ClipSummary(
                rank=1,
                start="00:01:00",
                end="00:01:30",
                duration_seconds=30.0,
                viral_score=8.5,
                rank_score=9.1,
                emotion="humor",
                hook="Unexpected twist",
                reason="Great delivery",
                summary="A standout moment",
            )
        ],
    )


class TestSqlAlchemyAnalysisJobStore:
    def test_persists_completed_job_with_clips(self, store: SqlAlchemyAnalysisJobStore) -> None:
        job = AnalysisJob(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            video_id="dQw4w9WgXcQ",
            provider="openai",
            status=AnalysisJobStatus.COMPLETED,
            finished_at=utc_now(),
            result=_completed_result(),
        )

        store.create(job)
        loaded = store.get(job.id)

        assert loaded is not None
        assert loaded.status == AnalysisJobStatus.COMPLETED
        assert loaded.result is not None
        assert loaded.result.title == "Never Gonna Give You Up"
        assert len(loaded.result.clips) == 1
        assert loaded.result.clips[0].hook == "Unexpected twist"

    def test_updates_running_job_progress(self, store: SqlAlchemyAnalysisJobStore) -> None:
        job = AnalysisJob(
            url="https://youtu.be/dQw4w9WgXcQ",
            video_id="dQw4w9WgXcQ",
            provider="openai",
        )
        created = store.create(job)
        running = created.model_copy(
            update={
                "status": AnalysisJobStatus.RUNNING,
                "stage": AnalysisStage.ANALYZING,
                "progress_message": "Analyzing transcript",
            }
        )

        store.update(running)
        loaded = store.get(created.id)

        assert loaded is not None
        assert loaded.status == AnalysisJobStatus.RUNNING
        assert loaded.stage == AnalysisStage.ANALYZING

    def test_list_recent_returns_jobs(self, store: SqlAlchemyAnalysisJobStore) -> None:
        store.create(
            AnalysisJob(
                url="https://youtu.be/dQw4w9WgXcQ",
                video_id="dQw4w9WgXcQ",
                provider="openai",
            )
        )

        jobs = store.list_recent(limit=5)

        assert len(jobs) == 1
        assert jobs[0].video_id == "dQw4w9WgXcQ"


class TestAnalysisJobServiceWithDatabase:
    def test_service_round_trip_with_sql_store(
        self,
        store: SqlAlchemyAnalysisJobStore,
    ) -> None:
        service = AnalysisJobService(store)
        created = service.create_job("dQw4w9WgXcQ", provider="openai")
        finished = created.model_copy(
            update={
                "status": AnalysisJobStatus.COMPLETED,
                "finished_at": utc_now(),
                "result": _completed_result(),
            }
        )
        service._store.update(finished)

        loaded = service.get_job(created.id)
        assert loaded is not None
        assert loaded.result is not None
        assert loaded.result.clips_ranked == 1
