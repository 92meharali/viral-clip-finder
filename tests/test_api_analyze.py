"""Tests for analysis job API and service."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_analysis_job_service
from app.api.main import create_app
from app.services.analysis.models import (
    AnalysisJobResult,
    AnalysisJobStatus,
    AnalysisStage,
    ClipSummary,
)
from app.services.analysis.pipeline import AnalysisPipeline
from app.services.analysis.service import AnalysisJobService
from app.services.analysis.store import InMemoryAnalysisJobStore


def _sample_result() -> AnalysisJobResult:
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
        clips_analyzed=5,
        clips_ranked=2,
        clips=[
            ClipSummary(
                rank=1,
                start="00:00:13",
                end="00:00:45",
                duration_seconds=32.0,
                viral_score=8.5,
                rank_score=9.1,
                emotion="humor",
                hook="You won't believe this moment",
                reason="Unexpected punchline",
                summary="A standout comedic beat",
            )
        ],
    )


class FakeAnalysisPipeline(AnalysisPipeline):
    """Pipeline stub for API tests."""

    def __init__(
        self,
        *,
        result: AnalysisJobResult | None = None,
        error: Exception | None = None,
        on_run: Callable[[], None] | None = None,
    ) -> None:
        self._result = result or _sample_result()
        self._error = error
        self._on_run = on_run

    def run(
        self,
        url: str,
        *,
        provider: str | None = None,
        top_n: int | None = None,
        on_progress: Callable[[AnalysisStage, str], None] | None = None,
    ) -> AnalysisJobResult:
        if self._on_run is not None:
            self._on_run()
        if on_progress is not None:
            on_progress(AnalysisStage.INGESTING, "Fetching transcript")
            on_progress(AnalysisStage.ANALYZING, "Analyzing")
        if self._error is not None:
            raise self._error
        return self._result


@pytest.fixture
def job_store() -> InMemoryAnalysisJobStore:
    return InMemoryAnalysisJobStore()


@pytest.fixture
def analysis_service(job_store: InMemoryAnalysisJobStore) -> AnalysisJobService:
    return AnalysisJobService(job_store, pipeline=FakeAnalysisPipeline())


@pytest.fixture
def client(
    job_store: InMemoryAnalysisJobStore,
    analysis_service: AnalysisJobService,
) -> TestClient:
    app = create_app(job_store=job_store)
    app.dependency_overrides[get_analysis_job_service] = lambda: analysis_service
    return TestClient(app)


class TestAnalyzeApi:
    def test_start_analysis_returns_accepted_job(self, client: TestClient) -> None:
        response = client.post(
            "/analyze",
            json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "provider": "openai"},
        )

        assert response.status_code == 202
        payload = response.json()
        assert payload["status"] == AnalysisJobStatus.PENDING.value
        assert payload["video_id"] == "dQw4w9WgXcQ"
        assert payload["provider"] == "openai"
        assert payload["result"] is None

    def test_get_job_returns_completed_result(self, client: TestClient) -> None:
        created = client.post(
            "/analyze",
            json={"url": "dQw4w9WgXcQ"},
        ).json()

        response = client.get(f"/analyze/{created['id']}")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == AnalysisJobStatus.COMPLETED.value
        assert payload["result"]["title"] == "Never Gonna Give You Up"
        assert payload["result"]["clips_ranked"] == 2
        assert payload["result"]["clips"][0]["hook"] == "You won't believe this moment"

    def test_get_missing_job_returns_404(self, client: TestClient) -> None:
        response = client.get("/analyze/missing-job-id")

        assert response.status_code == 404

    def test_invalid_url_returns_422(self, client: TestClient) -> None:
        response = client.post("/analyze", json={"url": "https://example.com/video"})

        assert response.status_code == 422

    def test_invalid_provider_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/analyze",
            json={"url": "dQw4w9WgXcQ", "provider": "unknown"},
        )

        assert response.status_code == 422


class TestAnalysisJobService:
    def test_run_job_marks_failure(self, job_store: InMemoryAnalysisJobStore) -> None:
        service = AnalysisJobService(
            job_store,
            pipeline=FakeAnalysisPipeline(error=RuntimeError("analysis failed")),
        )
        job = service.create_job("dQw4w9WgXcQ")

        finished = service.run_job(job.id)

        assert finished.status == AnalysisJobStatus.FAILED
        assert finished.error == "analysis failed"

    def test_run_job_updates_progress(self, job_store: InMemoryAnalysisJobStore) -> None:
        service = AnalysisJobService(job_store, pipeline=FakeAnalysisPipeline())
        job = service.create_job("dQw4w9WgXcQ")

        service.run_job(job.id)
        stored = service.get_job(job.id)

        assert stored is not None
        assert stored.status == AnalysisJobStatus.COMPLETED
        assert stored.result is not None
        assert stored.result.clips_ranked == 2
