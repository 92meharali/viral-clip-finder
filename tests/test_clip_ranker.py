"""Tests for clip ranking service."""

import pytest

from app.core.config import Settings
from app.core.exceptions import ClipRankingError
from app.models.clip import ViralClip
from app.models.transcript import TranscriptSegment
from app.services.clip_ranker import (
    ClipRanker,
    _deduplicate_clips,
    _dialogue_density,
    _emotion_intensity,
    _length_score,
    _overlap_ratio,
    _score_clips,
    rank_clips,
)


def _make_clip(
    *,
    start: str = "00:00:00",
    start_seconds: float = 0.0,
    end: str = "00:00:45",
    end_seconds: float = 45.0,
    duration_seconds: float = 45.0,
    viral_score: float = 8.0,
    emotion: str = "betrayal",
    hook: str = "Test hook",
    reason: str = "Test reason",
    summary: str = "Test summary",
) -> ViralClip:
    return ViralClip(
        start=start,
        end=end,
        reason=reason,
        viral_score=viral_score,
        emotion=emotion,
        hook=hook,
        summary=summary,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        duration_seconds=duration_seconds,
    )


@pytest.fixture
def settings() -> Settings:
    return Settings(
        max_clips=3,
        min_clip_duration_seconds=20,
        max_clip_duration_seconds=90,
    )


@pytest.fixture
def sample_segments() -> list[TranscriptSegment]:
    return [
        TranscriptSegment(start="00:00:10", seconds=10.0, speaker="A", text="Hello there."),
        TranscriptSegment(start="00:00:20", seconds=20.0, speaker="B", text="I disagree strongly."),
        TranscriptSegment(
            start="00:00:30", seconds=30.0, speaker="A", text="You're lying to everyone."
        ),
        TranscriptSegment(start="00:01:00", seconds=60.0, speaker="C", text="Vote time."),
        TranscriptSegment(start="00:01:30", seconds=90.0, speaker="D", text="Shocking reveal."),
    ]


class TestScoringHelpers:
    def test_emotion_intensity_exact_match(self) -> None:
        assert _emotion_intensity("betrayal") == 1.0

    def test_emotion_intensity_partial_match(self) -> None:
        assert _emotion_intensity("pure betrayal moment") == 1.0

    def test_emotion_intensity_unknown_defaults(self) -> None:
        assert _emotion_intensity("calm") == 0.5

    def test_dialogue_density(self, sample_segments: list[TranscriptSegment]) -> None:
        clip = _make_clip(start_seconds=15.0, end_seconds=45.0, duration_seconds=30.0)
        density = _dialogue_density(clip, sample_segments)
        assert density > 0

    def test_dialogue_density_empty_window(self, sample_segments: list[TranscriptSegment]) -> None:
        clip = _make_clip(start_seconds=0.0, end_seconds=5.0, duration_seconds=5.0)
        assert _dialogue_density(clip, sample_segments) == 0.0

    def test_length_score_ideal_range(self) -> None:
        assert _length_score(45.0, 20, 90) == 1.0

    def test_length_score_too_short(self) -> None:
        assert _length_score(10.0, 20, 90) == 0.0

    def test_length_score_too_long(self) -> None:
        assert _length_score(100.0, 20, 90) == 0.0

    def test_overlap_ratio_full_overlap(self) -> None:
        clip_a = _make_clip(start_seconds=10.0, end_seconds=40.0, duration_seconds=30.0)
        clip_b = _make_clip(start_seconds=15.0, end_seconds=35.0, duration_seconds=20.0)
        assert _overlap_ratio(clip_a, clip_b) == 1.0

    def test_overlap_ratio_no_overlap(self) -> None:
        clip_a = _make_clip(start_seconds=0.0, end_seconds=30.0, duration_seconds=30.0)
        clip_b = _make_clip(start_seconds=60.0, end_seconds=90.0, duration_seconds=30.0)
        assert _overlap_ratio(clip_a, clip_b) == 0.0


class TestDeduplication:
    def test_removes_overlapping_clips(self, settings: Settings) -> None:
        clips = [
            _make_clip(
                start_seconds=10.0,
                end_seconds=50.0,
                duration_seconds=40.0,
                viral_score=9.0,
            ),
            _make_clip(
                start_seconds=15.0,
                end_seconds=45.0,
                duration_seconds=30.0,
                viral_score=7.0,
            ),
        ]
        # Need RankedClip for dedup - use _score_clips
        segments: list[TranscriptSegment] = []
        ranked = _score_clips(clips, segments, settings, ClipRanker().weights)
        result = _deduplicate_clips(ranked, overlap_threshold=0.5)
        assert len(result) == 1
        assert result[0].viral_score == 9.0


class TestClipRanker:
    def test_ranks_by_composite_score(
        self,
        settings: Settings,
        sample_segments: list[TranscriptSegment],
    ) -> None:
        clips = [
            _make_clip(
                start_seconds=15.0,
                end_seconds=50.0,
                duration_seconds=35.0,
                viral_score=7.0,
                emotion="calm",
            ),
            _make_clip(
                start="00:01:00",
                start_seconds=60.0,
                end="00:01:30",
                end_seconds=90.0,
                duration_seconds=30.0,
                viral_score=8.0,
                emotion="betrayal",
            ),
        ]
        ranker = ClipRanker(settings=settings)
        ranked = ranker.rank(clips, sample_segments, top_n=2)

        assert len(ranked) == 2
        assert all(clip.rank_score > 0 for clip in ranked)

    def test_respects_top_n(
        self,
        settings: Settings,
        sample_segments: list[TranscriptSegment],
    ) -> None:
        clips = [
            _make_clip(
                start_seconds=i * 100.0,
                end_seconds=i * 100.0 + 40.0,
                duration_seconds=40.0,
                viral_score=float(10 - i),
                emotion=f"emotion_{i}",
            )
            for i in range(5)
        ]
        ranker = ClipRanker(settings=Settings(max_clips=2))
        ranked = ranker.rank(clips, sample_segments)

        assert len(ranked) == 2

    def test_deduplicates_overlapping(
        self,
        settings: Settings,
        sample_segments: list[TranscriptSegment],
    ) -> None:
        clips = [
            _make_clip(
                start_seconds=10.0,
                end_seconds=50.0,
                duration_seconds=40.0,
                viral_score=9.5,
                emotion="betrayal",
            ),
            _make_clip(
                start_seconds=12.0,
                end_seconds=48.0,
                duration_seconds=36.0,
                viral_score=8.0,
                emotion="shock",
            ),
            _make_clip(
                start_seconds=100.0,
                end_seconds=140.0,
                duration_seconds=40.0,
                viral_score=7.0,
                emotion="humor",
            ),
        ]
        ranked = rank_clips(clips, sample_segments, top_n=5, settings=settings)
        assert len(ranked) == 2

    def test_prefers_emotional_variety(
        self,
        sample_segments: list[TranscriptSegment],
    ) -> None:
        clips = [
            _make_clip(
                start_seconds=0.0,
                end_seconds=40.0,
                duration_seconds=40.0,
                viral_score=8.0,
                emotion="betrayal",
            ),
            _make_clip(
                start_seconds=100.0,
                end_seconds=140.0,
                duration_seconds=40.0,
                viral_score=7.9,
                emotion="betrayal",
            ),
            _make_clip(
                start_seconds=200.0,
                end_seconds=240.0,
                duration_seconds=40.0,
                viral_score=7.5,
                emotion="humor",
            ),
        ]
        ranked = rank_clips(clips, sample_segments, top_n=2)

        emotions = {clip.emotion for clip in ranked}
        assert "humor" in emotions

    def test_empty_clips_raises(self, sample_segments: list[TranscriptSegment]) -> None:
        with pytest.raises(ClipRankingError, match="empty clip list"):
            rank_clips([], sample_segments)

    def test_ranked_clip_has_metadata(
        self,
        settings: Settings,
        sample_segments: list[TranscriptSegment],
    ) -> None:
        clips = [_make_clip()]
        ranked = rank_clips(clips, sample_segments, settings=settings)

        assert ranked[0].rank_score > 0
        assert ranked[0].emotion_intensity > 0
        assert ranked[0].length_score > 0
