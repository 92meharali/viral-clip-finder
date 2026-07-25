"""Tests for project and clip API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.core.config import Settings
from app.database.session import Database
from app.services.analysis.models import (
    AnalysisJob,
    AnalysisJobResult,
    AnalysisJobStatus,
    ClipSummary,
    utc_now,
)
from app.services.analysis.sqlalchemy_store import SqlAlchemyAnalysisJobStore


@pytest.fixture
def database() -> Database:
    db = Database(Settings(database_url="sqlite:///:memory:"))
    db.create_tables()
    return db


@pytest.fixture
def client(database: Database) -> TestClient:
    store = SqlAlchemyAnalysisJobStore(database.session_factory)
    app = create_app(job_store=store)
    app.state.database = database
    return TestClient(app)


def _seed_completed_project(store: SqlAlchemyAnalysisJobStore) -> str:
    result = AnalysisJobResult(
        video_id="dQw4w9WgXcQ",
        title="Never Gonna Give You Up",
        channel="Rick Astley",
        duration_seconds=212.0,
        webpage_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        transcript_language="en",
        transcript_source="manual",
        transcript_segments=42,
        candidate_windows=3,
        llm_windows_analyzed=1,
        clips_analyzed=2,
        clips_ranked=2,
        clips=[
            ClipSummary(
                rank=1,
                start="00:01:00",
                end="00:01:30",
                duration_seconds=30.0,
                viral_score=9.0,
                rank_score=9.5,
                emotion="humor",
                hook="Iconic moment",
                reason="Memorable line",
                summary="Top clip",
            ),
            ClipSummary(
                rank=2,
                start="00:02:00",
                end="00:02:20",
                duration_seconds=20.0,
                viral_score=7.0,
                rank_score=7.5,
                emotion="shock",
                hook="Plot twist",
                reason="Unexpected",
                summary="Second clip",
            ),
        ],
    )
    job = AnalysisJob(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        video_id="dQw4w9WgXcQ",
        provider="openai",
        status=AnalysisJobStatus.COMPLETED,
        finished_at=utc_now(),
        result=result,
    )
    store.create(job)
    loaded = store.get(job.id)
    assert loaded is not None and loaded.result is not None
    project = store.get(job.id)
    assert project is not None
    # project id comes from DB - fetch via list endpoint in test instead
    return job.id


class TestProjectApi:
    def test_list_projects_returns_seeded_project(
        self,
        client: TestClient,
        database: Database,
    ) -> None:
        store = SqlAlchemyAnalysisJobStore(database.session_factory)
        _seed_completed_project(store)

        response = client.get("/projects")

        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 1
        assert payload["items"][0]["title"] == "Never Gonna Give You Up"
        assert payload["items"][0]["clip_count"] == 2

    def test_get_project_returns_clips(
        self,
        client: TestClient,
        database: Database,
    ) -> None:
        store = SqlAlchemyAnalysisJobStore(database.session_factory)
        _seed_completed_project(store)
        project_id = client.get("/projects").json()["items"][0]["id"]

        response = client.get(f"/projects/{project_id}")

        assert response.status_code == 200
        payload = response.json()
        assert payload["video_id"] == "dQw4w9WgXcQ"
        assert len(payload["clips"]) == 2
        assert payload["clips"][0]["hook"] == "Iconic moment"

    def test_get_missing_project_returns_404(self, client: TestClient) -> None:
        response = client.get("/projects/missing-id")
        assert response.status_code == 404


class TestClipApi:
    def test_list_clips_supports_filters(
        self,
        client: TestClient,
        database: Database,
    ) -> None:
        store = SqlAlchemyAnalysisJobStore(database.session_factory)
        job_id = _seed_completed_project(store)
        project_id = client.get("/projects").json()["items"][0]["id"]

        all_clips = client.get("/clips", params={"project_id": project_id})
        humor_clips = client.get("/clips", params={"project_id": project_id, "emotion": "humor"})
        high_score = client.get("/clips", params={"project_id": project_id, "min_score": 8.0})
        job_clips = client.get("/clips", params={"job_id": job_id})

        assert all_clips.json()["total"] == 2
        assert humor_clips.json()["total"] == 1
        assert high_score.json()["total"] == 1
        assert job_clips.json()["total"] == 2
