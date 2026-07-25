"""Analysis pipeline orchestration."""

from __future__ import annotations

from collections.abc import Callable

from loguru import logger

from app.core.config import Settings, get_settings
from app.core.exceptions import LLMAnalysisError
from app.providers.factory import get_clip_analyzer
from app.services.analysis.models import (
    AnalysisJobResult,
    AnalysisStage,
    ClipSummary,
)
from app.services.candidate_windows import generate_candidate_windows
from app.services.youtube import YouTubeIngestionService
from app.services.youtube.client import YouTubeClient


class AnalysisPipeline:
    """Run ingestion, windowing, AI analysis, and ranking for a YouTube URL."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        youtube_client: YouTubeClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._youtube = YouTubeIngestionService(
            client=youtube_client,
            settings=self.settings,
        )

    def run(
        self,
        url: str,
        *,
        provider: str | None = None,
        top_n: int | None = None,
        on_progress: Callable[[AnalysisStage, str], None] | None = None,
    ) -> AnalysisJobResult:
        """Execute the full analysis pipeline for a YouTube URL."""
        resolved_provider = (provider or self.settings.ai_provider).strip().lower()
        resolved_top_n = top_n if top_n is not None else self.settings.max_clips

        self._report(
            on_progress,
            AnalysisStage.INGESTING,
            "Fetching YouTube metadata and transcript",
        )
        ingestion = self._youtube.ingest(url)
        segments = ingestion.segments
        metadata = ingestion.metadata

        self._report(
            on_progress,
            AnalysisStage.GENERATING_WINDOWS,
            "Generating candidate windows from transcript signals",
        )
        candidate_windows = generate_candidate_windows(
            segments,
            settings=self.settings,
            top_n=resolved_top_n,
        )

        self._report(on_progress, AnalysisStage.ANALYZING, "Analyzing transcript for viral moments")
        analyzer = get_clip_analyzer(self.settings, provider=resolved_provider)
        logger.info("Running analysis with provider={}", analyzer.provider_name)
        analyzed = analyzer.analyze_transcript(segments)
        if not analyzed:
            raise LLMAnalysisError("AI analysis returned no clips")

        self._report(
            on_progress,
            AnalysisStage.RANKING,
            "Ranking and deduplicating clip candidates",
        )
        ranked = analyzer.rank_candidates(analyzed, segments, top_n=resolved_top_n)
        if not ranked:
            raise LLMAnalysisError("Ranking returned no clips")

        self._report(on_progress, AnalysisStage.FINALIZING, "Preparing analysis results")
        clip_summaries = [
            ClipSummary.from_ranked_clip(clip, rank=index)
            for index, clip in enumerate(ranked, start=1)
        ]

        return AnalysisJobResult(
            video_id=metadata.video_id,
            title=metadata.title,
            channel=metadata.channel,
            duration_seconds=metadata.duration_seconds,
            webpage_url=str(metadata.webpage_url),
            transcript_language=ingestion.transcript_language,
            transcript_source=ingestion.transcript_source,
            transcript_segments=len(segments),
            candidate_windows=len(candidate_windows.windows),
            clips_analyzed=len(analyzed),
            clips_ranked=len(ranked),
            clips=clip_summaries,
        )

    @staticmethod
    def _report(
        on_progress: Callable[[AnalysisStage, str], None] | None,
        stage: AnalysisStage,
        message: str,
    ) -> None:
        logger.info("[{stage}] {message}", stage=stage.value, message=message)
        if on_progress is not None:
            on_progress(stage, message)
