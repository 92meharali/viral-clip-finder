"""Tests for candidate window generation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings
from app.models.transcript import TranscriptSegment
from app.services.candidate_windows.generator import CandidateWindowGenerator, generate_candidate_windows
from app.services.enrichment.adapters.transcript import TranscriptEnrichment


@pytest.fixture
def segments() -> list[TranscriptSegment]:
    return [
        TranscriptSegment(start="00:00:10", seconds=10.0, speaker="A", text="I never lie!"),
        TranscriptSegment(start="00:00:25", seconds=25.0, speaker="B", text="That's crazy."),
        TranscriptSegment(start="00:01:00", seconds=60.0, speaker="A", text="Vote now everyone."),
    ]


@pytest.fixture
def settings() -> Settings:
    return Settings(
        candidate_window_min_duration=10.0,
        candidate_window_max_duration=90.0,
        candidate_window_merge_gap=3.0,
        max_clips=5,
    )


class TestTranscriptEnrichment:
    def test_scores_emotional_segments(self, segments: list[TranscriptSegment]) -> None:
        signals = TranscriptEnrichment().analyze(segments)
        assert signals
        assert any("never" in signal.details.lower() for signal in signals)


class TestCandidateWindowGenerator:
    def test_merges_transcript_signals(self, settings: Settings, segments: list[TranscriptSegment]) -> None:
        generator = CandidateWindowGenerator(settings=settings, modules=[TranscriptEnrichment()])
        result = generator.generate(segments)

        assert result.window_count >= 1
        assert result.windows[0].duration_seconds >= settings.candidate_window_min_duration

    @patch("app.services.enrichment.adapters.scene.SceneDetectionService")
    def test_includes_scene_signals_when_video_available(
        self,
        mock_scene_service: MagicMock,
        settings: Settings,
        segments: list[TranscriptSegment],
    ) -> None:
        mock_scene_service.return_value.detect.return_value = MagicMock(
            segments=[
                MagicMock(
                    index=0,
                    start_seconds=0.0,
                    end_seconds=30.0,
                    duration_seconds=30.0,
                )
            ]
        )
        from app.services.enrichment.adapters.scene import ReframeSceneEnrichment

        generator = CandidateWindowGenerator(
            settings=settings,
            modules=[TranscriptEnrichment(), ReframeSceneEnrichment(scene_service=mock_scene_service.return_value)],
        )
        result = generator.generate(segments, video_path="episode.mp4")

        assert result.signal_count >= 1
        assert generate_candidate_windows(segments, settings=settings, top_n=2).window_count <= 2
