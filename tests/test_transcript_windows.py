"""Tests for transcript window generation and windowed analysis."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.core.config import Settings
from app.core.exceptions import LLMAnalysisError
from app.models.clip import ViralClip
from app.models.transcript import TranscriptSegment
from app.services.transcript_windows import (
    analyze_transcript_with_windows,
    generate_transcript_windows,
    merge_window_clips,
)


def _segment(seconds: float, text: str) -> TranscriptSegment:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return TranscriptSegment(
        start=f"{hours:02d}:{minutes:02d}:{secs:02d}",
        seconds=seconds,
        text=text,
    )


@pytest.fixture
def short_segments() -> list[TranscriptSegment]:
    return [
        _segment(10.0, "Opening line"),
        _segment(40.0, "Second beat"),
        _segment(80.0, "Closing argument"),
    ]


@pytest.fixture
def long_segments() -> list[TranscriptSegment]:
    return [_segment(float(minute * 60), f"Minute {minute}") for minute in range(25)]


@pytest.fixture
def window_settings() -> Settings:
    return Settings(
        llm_window_enabled=True,
        llm_window_size_seconds=600.0,
        llm_window_overlap_seconds=60.0,
    )


class TestTranscriptWindowGenerator:
    def test_single_window_for_short_transcript(
        self,
        short_segments: list[TranscriptSegment],
        window_settings: Settings,
    ) -> None:
        result = generate_transcript_windows(
            short_segments,
            settings=window_settings,
            total_duration_seconds=120.0,
        )

        assert result.window_count == 1
        assert result.used_windowing is False
        assert len(result.windows[0].segments) == 3

    def test_generates_overlapping_windows_for_long_transcript(
        self,
        long_segments: list[TranscriptSegment],
        window_settings: Settings,
    ) -> None:
        result = generate_transcript_windows(
            long_segments,
            settings=window_settings,
            total_duration_seconds=1500.0,
        )

        assert result.window_count >= 2
        assert result.used_windowing is True
        assert all(window.segment_count > 0 for window in result.windows)

    def test_preserves_segment_boundaries(
        self,
        long_segments: list[TranscriptSegment],
        window_settings: Settings,
    ) -> None:
        result = generate_transcript_windows(
            long_segments,
            settings=window_settings,
            total_duration_seconds=1500.0,
        )

        original_ids = {id(segment) for segment in long_segments}
        for window in result.windows:
            for segment in window.segments:
                assert id(segment) in original_ids

    def test_disabled_windowing_returns_single_window(
        self,
        long_segments: list[TranscriptSegment],
    ) -> None:
        settings = Settings(llm_window_enabled=False, llm_window_size_seconds=600.0)
        result = generate_transcript_windows(
            long_segments,
            settings=settings,
            total_duration_seconds=1500.0,
        )

        assert result.window_count == 1

    def test_invalid_overlap_raises(self, short_segments: list[TranscriptSegment]) -> None:
        settings = Settings(
            llm_window_size_seconds=100.0,
            llm_window_overlap_seconds=100.0,
        )
        with pytest.raises(LLMAnalysisError, match="overlap"):
            generate_transcript_windows(
                short_segments,
                settings=settings,
                total_duration_seconds=120.0,
            )


class TestMergeWindowClips:
    def test_removes_exact_duplicates(self) -> None:
        clip_a = ViralClip(
            start="00:01:00",
            end="00:01:30",
            start_seconds=60.0,
            end_seconds=90.0,
            duration_seconds=30.0,
            reason="reason",
            viral_score=8.0,
            emotion="humor",
            hook="hook",
            summary="summary",
        )
        clip_b = ViralClip(
            start="00:02:00",
            end="00:02:30",
            start_seconds=120.0,
            end_seconds=150.0,
            duration_seconds=30.0,
            reason="reason",
            viral_score=7.0,
            emotion="shock",
            hook="hook 2",
            summary="summary 2",
        )

        merged = merge_window_clips([[clip_a, clip_b], [clip_a]])

        assert len(merged) == 2


class TestWindowedAnalyzer:
    def test_uses_single_call_for_short_transcript(
        self,
        short_segments: list[TranscriptSegment],
        window_settings: Settings,
    ) -> None:
        analyzer = MagicMock()
        analyzer.provider_name = "openai"
        analyzer.analyze_transcript.return_value = [
            ViralClip(
                start="00:00:10",
                end="00:00:40",
                start_seconds=10.0,
                end_seconds=40.0,
                duration_seconds=30.0,
                reason="reason",
                viral_score=8.0,
                emotion="humor",
                hook="hook",
                summary="summary",
            )
        ]

        clips, window_count = analyze_transcript_with_windows(
            analyzer,
            short_segments,
            settings=window_settings,
            total_duration_seconds=120.0,
        )

        assert window_count == 1
        assert len(clips) == 1
        analyzer.analyze_transcript.assert_called_once_with(short_segments)

    def test_analyzes_each_window_for_long_transcript(
        self,
        long_segments: list[TranscriptSegment],
        window_settings: Settings,
    ) -> None:
        analyzer = MagicMock()
        analyzer.provider_name = "openai"
        analyzer.analyze_transcript.return_value = [
            ViralClip(
                start="00:10:00",
                end="00:10:30",
                start_seconds=600.0,
                end_seconds=630.0,
                duration_seconds=30.0,
                reason="reason",
                viral_score=8.0,
                emotion="humor",
                hook="hook",
                summary="summary",
            )
        ]

        clips, window_count = analyze_transcript_with_windows(
            analyzer,
            long_segments,
            settings=window_settings,
            total_duration_seconds=1500.0,
        )

        assert window_count >= 2
        assert analyzer.analyze_transcript.call_count == window_count
        assert len(clips) == 1
