"""Tests for clip quality checking."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.exceptions import QualityCheckError
from app.models.clip import ViralClip
from app.models.quality import QualityIssueCode
from app.models.transcript import TranscriptSegment
from app.services.quality_checker import (
    ClipQualityChecker,
    QualityThresholds,
    compute_silence_ratio,
    filter_quality_clips,
)


def _make_clip(
    *,
    start_seconds: float = 10.0,
    end_seconds: float = 50.0,
    duration_seconds: float = 40.0,
    viral_score: float = 8.0,
) -> ViralClip:
    return ViralClip(
        start="00:00:10",
        end="00:00:50",
        reason="Test moment",
        viral_score=viral_score,
        emotion="betrayal",
        hook="Test hook",
        summary="Test summary",
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        duration_seconds=duration_seconds,
    )


@pytest.fixture
def segments() -> list[TranscriptSegment]:
    return [
        TranscriptSegment(start="00:00:12", seconds=12.0, speaker="A", text="Hello there."),
        TranscriptSegment(start="00:00:18", seconds=18.0, speaker="B", text="You're lying."),
        TranscriptSegment(start="00:00:25", seconds=25.0, speaker="A", text="I didn't do it."),
        TranscriptSegment(start="00:00:35", seconds=35.0, speaker="B", text="Vote now."),
        TranscriptSegment(start="00:00:42", seconds=42.0, speaker="A", text="Fine."),
    ]


@pytest.fixture
def thresholds() -> QualityThresholds:
    return QualityThresholds(
        min_duration_seconds=20,
        max_duration_seconds=90,
        min_viral_score=5.0,
        max_silence_ratio=0.6,
    )


class TestSilenceRatio:
    def test_low_silence_with_dense_dialogue(
        self,
        segments: list[TranscriptSegment],
    ) -> None:
        clip = _make_clip(start_seconds=10.0, end_seconds=50.0, duration_seconds=40.0)
        ratio = compute_silence_ratio(clip, segments)
        assert ratio < 0.6

    def test_high_silence_with_sparse_dialogue(self) -> None:
        sparse = [
            TranscriptSegment(start="00:00:15", seconds=15.0, text="One line only."),
        ]
        clip = _make_clip(start_seconds=10.0, end_seconds=100.0, duration_seconds=90.0)
        ratio = compute_silence_ratio(clip, sparse)
        assert ratio > 0.6

    def test_full_silence_without_dialogue(self) -> None:
        clip = _make_clip()
        assert compute_silence_ratio(clip, []) == 1.0


class TestClipQualityChecker:
    def test_passes_valid_clip(
        self,
        segments: list[TranscriptSegment],
        thresholds: QualityThresholds,
    ) -> None:
        settings = Settings(min_viral_score=5.0, max_silence_ratio=0.6)
        checker = ClipQualityChecker(settings=settings, thresholds=thresholds)
        report = checker.check([_make_clip()], segments)

        assert report.total == 1
        assert report.passed == [1]
        assert report.rejected == []

    def test_rejects_too_short(
        self,
        segments: list[TranscriptSegment],
        thresholds: QualityThresholds,
    ) -> None:
        clip = _make_clip(start_seconds=10.0, end_seconds=25.0, duration_seconds=15.0)
        checker = ClipQualityChecker(thresholds=thresholds)
        report = checker.check([clip], segments)

        assert report.rejected[0].passed is False
        assert any(issue.code == QualityIssueCode.TOO_SHORT for issue in report.rejected[0].issues)

    def test_rejects_too_long(
        self,
        segments: list[TranscriptSegment],
        thresholds: QualityThresholds,
    ) -> None:
        clip = _make_clip(start_seconds=0.0, end_seconds=100.0, duration_seconds=100.0)
        checker = ClipQualityChecker(thresholds=thresholds)
        report = checker.check([clip], segments)

        assert any(issue.code == QualityIssueCode.TOO_LONG for issue in report.rejected[0].issues)

    def test_rejects_low_confidence(
        self,
        segments: list[TranscriptSegment],
        thresholds: QualityThresholds,
    ) -> None:
        clip = _make_clip(viral_score=3.0)
        checker = ClipQualityChecker(thresholds=thresholds)
        report = checker.check([clip], segments)

        assert any(
            issue.code == QualityIssueCode.LOW_CONFIDENCE for issue in report.rejected[0].issues
        )

    def test_rejects_too_much_silence(self, thresholds: QualityThresholds) -> None:
        sparse = [TranscriptSegment(start="00:00:15", seconds=15.0, text="Brief.")]
        clip = _make_clip(start_seconds=10.0, end_seconds=100.0, duration_seconds=90.0)
        checker = ClipQualityChecker(thresholds=thresholds)
        report = checker.check([clip], sparse)

        assert any(
            issue.code == QualityIssueCode.TOO_MUCH_SILENCE for issue in report.rejected[0].issues
        )

    def test_rejects_internal_repeated_dialogue(
        self,
        thresholds: QualityThresholds,
    ) -> None:
        repeated = [
            TranscriptSegment(start="00:00:12", seconds=12.0, text="Same line."),
            TranscriptSegment(start="00:00:20", seconds=20.0, text="Same line."),
            TranscriptSegment(start="00:00:30", seconds=30.0, text="Different."),
        ]
        checker = ClipQualityChecker(thresholds=thresholds)
        report = checker.check([_make_clip()], repeated)

        assert any(
            issue.code == QualityIssueCode.REPEATED_DIALOGUE for issue in report.rejected[0].issues
        )

    def test_rejects_duplicate_across_batch(
        self,
        thresholds: QualityThresholds,
    ) -> None:
        dialogue = [
            TranscriptSegment(start="00:00:12", seconds=12.0, text="Hello."),
            TranscriptSegment(start="00:00:20", seconds=20.0, text="World."),
        ]
        clip_a = _make_clip(start_seconds=10.0, end_seconds=50.0, duration_seconds=40.0)
        clip_b = _make_clip(
            start_seconds=60.0,
            end_seconds=100.0,
            duration_seconds=40.0,
            viral_score=7.0,
        )
        extended = dialogue + [
            TranscriptSegment(start="00:01:02", seconds=62.0, text="Hello."),
            TranscriptSegment(start="00:01:10", seconds=70.0, text="World."),
        ]
        checker = ClipQualityChecker(
            thresholds=QualityThresholds(
                min_duration_seconds=20,
                max_duration_seconds=90,
                min_viral_score=5.0,
                max_silence_ratio=1.0,
            )
        )
        report = checker.check([clip_a, clip_b], extended)

        assert report.passed == [1]
        assert len(report.rejected) == 1
        assert any(
            issue.code == QualityIssueCode.REPEATED_DIALOGUE for issue in report.rejected[0].issues
        )

    def test_filter_clips_returns_only_passed(
        self,
        segments: list[TranscriptSegment],
        thresholds: QualityThresholds,
    ) -> None:
        good = _make_clip()
        bad = _make_clip(start_seconds=10.0, end_seconds=25.0, duration_seconds=15.0)
        checker = ClipQualityChecker(thresholds=thresholds)
        passed = checker.filter_clips([good, bad], segments)

        assert len(passed) == 1
        assert passed[0].duration_seconds == 40.0

    def test_empty_clips_raises(self, segments: list[TranscriptSegment]) -> None:
        with pytest.raises(QualityCheckError, match="empty clip list"):
            ClipQualityChecker().check([], segments)

    def test_filter_quality_clips_convenience(
        self,
        segments: list[TranscriptSegment],
        thresholds: QualityThresholds,
    ) -> None:
        good = _make_clip()
        bad = _make_clip(viral_score=2.0)
        settings = Settings(min_viral_score=5.0)
        passed, report = filter_quality_clips([good, bad], segments, settings=settings)

        assert len(passed) == 1
        assert report.total == 2
        assert len(report.rejected) == 1
