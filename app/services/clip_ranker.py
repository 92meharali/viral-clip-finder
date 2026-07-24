"""Clip ranking and deduplication service."""

from __future__ import annotations

from dataclasses import dataclass

from loguru import logger

from app.core.config import Settings, get_settings
from app.core.exceptions import ClipRankingError
from app.models.clip import RankedClip, ViralClip
from app.models.transcript import TranscriptSegment

# Emotion intensity weights (0.0 - 1.0). Matched case-insensitively against clip.emotion.
EMOTION_INTENSITY: dict[str, float] = {
    "betrayal": 1.0,
    "shock": 0.95,
    "accusation": 0.9,
    "anger": 0.9,
    "reveal": 0.9,
    "cliffhanger": 0.88,
    "suspense": 0.85,
    "argument": 0.85,
    "lie": 0.85,
    "drama": 0.8,
    "voting": 0.8,
    "emotional": 0.78,
    "strategy": 0.75,
    "laughter": 0.72,
    "humor": 0.72,
    "funny": 0.7,
    "surprise": 0.7,
    "memorable": 0.65,
}

DEFAULT_EMOTION_INTENSITY = 0.5
IDEAL_MIN_DURATION = 30.0
IDEAL_MAX_DURATION = 60.0
DEFAULT_OVERLAP_THRESHOLD = 0.5
VARIETY_BONUS = 1.0

WEIGHT_VIRAL_SCORE = 0.40
WEIGHT_EMOTION = 0.25
WEIGHT_DIALOGUE = 0.20
WEIGHT_LENGTH = 0.15


@dataclass(frozen=True)
class RankingWeights:
    """Configurable weights for the composite rank score."""

    viral_score: float = WEIGHT_VIRAL_SCORE
    emotion: float = WEIGHT_EMOTION
    dialogue: float = WEIGHT_DIALOGUE
    length: float = WEIGHT_LENGTH


def _emotion_intensity(emotion: str) -> float:
    """Return the intensity weight for an emotion label."""
    normalized = emotion.strip().lower()
    if normalized in EMOTION_INTENSITY:
        return EMOTION_INTENSITY[normalized]

    for keyword, weight in EMOTION_INTENSITY.items():
        if keyword in normalized:
            return weight

    return DEFAULT_EMOTION_INTENSITY


def _dialogue_density(clip: ViralClip, segments: list[TranscriptSegment]) -> float:
    """Calculate characters of dialogue per second within the clip window."""
    matching = [
        segment for segment in segments if clip.start_seconds <= segment.seconds < clip.end_seconds
    ]
    if not matching:
        return 0.0

    char_count = sum(len(segment.text) for segment in matching)
    return char_count / clip.duration_seconds


def _length_score(duration: float, min_duration: int, max_duration: int) -> float:
    """Score how well a clip duration fits the ideal short-form range."""
    if duration < min_duration or duration > max_duration:
        return 0.0

    if IDEAL_MIN_DURATION <= duration <= IDEAL_MAX_DURATION:
        return 1.0

    if duration < IDEAL_MIN_DURATION:
        span = IDEAL_MIN_DURATION - min_duration
        if span <= 0:
            return 0.0
        return (duration - min_duration) / span

    span = max_duration - IDEAL_MAX_DURATION
    if span <= 0:
        return 0.0
    return (max_duration - duration) / span


def _overlap_ratio(clip_a: ViralClip, clip_b: ViralClip) -> float:
    """Return overlap as a fraction of the shorter clip's duration."""
    overlap_start = max(clip_a.start_seconds, clip_b.start_seconds)
    overlap_end = min(clip_a.end_seconds, clip_b.end_seconds)
    if overlap_end <= overlap_start:
        return 0.0

    overlap = overlap_end - overlap_start
    shorter_duration = min(clip_a.duration_seconds, clip_b.duration_seconds)
    return overlap / shorter_duration


def _compute_rank_score(
    clip: ViralClip,
    *,
    emotion_intensity: float,
    dialogue_density: float,
    length_score: float,
    normalized_dialogue: float,
    weights: RankingWeights,
) -> float:
    """Combine individual factors into a composite rank score."""
    return (
        clip.viral_score * weights.viral_score
        + emotion_intensity * 10 * weights.emotion
        + normalized_dialogue * 10 * weights.dialogue
        + length_score * 10 * weights.length
    )


def _score_clips(
    clips: list[ViralClip],
    segments: list[TranscriptSegment],
    settings: Settings,
    weights: RankingWeights,
) -> list[RankedClip]:
    """Score all clips and return RankedClip objects."""
    densities = [_dialogue_density(clip, segments) for clip in clips]
    max_density = max(densities) if densities else 0.0

    ranked: list[RankedClip] = []
    for clip, density in zip(clips, densities, strict=True):
        emotion = _emotion_intensity(clip.emotion)
        length = _length_score(
            clip.duration_seconds,
            settings.min_clip_duration_seconds,
            settings.max_clip_duration_seconds,
        )
        normalized_dialogue = density / max_density if max_density > 0 else 0.0
        rank_score = _compute_rank_score(
            clip,
            emotion_intensity=emotion,
            dialogue_density=density,
            length_score=length,
            normalized_dialogue=normalized_dialogue,
            weights=weights,
        )
        ranked.append(
            RankedClip(
                **clip.model_dump(),
                rank_score=round(rank_score, 3),
                emotion_intensity=emotion,
                dialogue_density=round(density, 3),
                length_score=round(length, 3),
            )
        )

    return ranked


def _deduplicate_clips(
    clips: list[RankedClip],
    overlap_threshold: float,
) -> list[RankedClip]:
    """Remove temporally overlapping clips, keeping the higher rank score."""
    sorted_clips = sorted(clips, key=lambda clip: clip.rank_score, reverse=True)
    selected: list[RankedClip] = []

    for candidate in sorted_clips:
        is_duplicate = any(
            _overlap_ratio(candidate, kept) >= overlap_threshold for kept in selected
        )
        if is_duplicate:
            logger.debug(
                "Skipping duplicate clip {}-{} (rank {:.2f})",
                candidate.start,
                candidate.end,
                candidate.rank_score,
            )
            continue
        selected.append(candidate)

    return selected


def _select_with_variety(clips: list[RankedClip], top_n: int) -> list[RankedClip]:
    """Select top N clips while preferring emotional variety."""
    remaining = sorted(clips, key=lambda clip: clip.rank_score, reverse=True)
    selected: list[RankedClip] = []
    seen_emotions: set[str] = set()

    while remaining and len(selected) < top_n:
        best_index = 0
        best_selection_score = -1.0

        for index, candidate in enumerate(remaining):
            emotion_key = candidate.emotion.strip().lower()
            variety_bonus = VARIETY_BONUS if emotion_key not in seen_emotions else 0.0
            selection_score = candidate.rank_score + variety_bonus
            if selection_score > best_selection_score:
                best_selection_score = selection_score
                best_index = index

        chosen = remaining.pop(best_index)
        selected.append(chosen)
        seen_emotions.add(chosen.emotion.strip().lower())

    return selected


class ClipRanker:
    """Rank, deduplicate, and select the top viral clips."""

    def __init__(
        self,
        settings: Settings | None = None,
        weights: RankingWeights | None = None,
        overlap_threshold: float = DEFAULT_OVERLAP_THRESHOLD,
    ) -> None:
        """Initialize the ranker.

        Args:
            settings: Optional settings override.
            weights: Optional custom scoring weights.
            overlap_threshold: Overlap ratio above which clips are considered duplicates.
        """
        self.settings = settings or get_settings()
        self.weights = weights or RankingWeights()
        self.overlap_threshold = overlap_threshold

    def rank(
        self,
        clips: list[ViralClip],
        segments: list[TranscriptSegment],
        *,
        top_n: int | None = None,
    ) -> list[RankedClip]:
        """Rank clips and return the top N after deduplication and variety selection.

        Args:
            clips: Viral clips detected by the LLM analyzer.
            segments: Parsed transcript segments for dialogue density scoring.
            top_n: Maximum clips to return. Defaults to ``settings.max_clips``.

        Returns:
            Ranked clips ordered by final selection priority.

        Raises:
            ClipRankingError: If clips list is empty.
        """
        if not clips:
            raise ClipRankingError("Cannot rank an empty clip list")

        limit = top_n if top_n is not None else self.settings.max_clips
        logger.info("Ranking {} clips, selecting top {}", len(clips), limit)

        scored = _score_clips(clips, segments, self.settings, self.weights)
        deduplicated = _deduplicate_clips(scored, self.overlap_threshold)
        selected = _select_with_variety(deduplicated, limit)

        logger.info(
            "Ranked {} clips → {} after dedup → {} selected",
            len(clips),
            len(deduplicated),
            len(selected),
        )
        return selected


def rank_clips(
    clips: list[ViralClip],
    segments: list[TranscriptSegment],
    *,
    top_n: int | None = None,
    settings: Settings | None = None,
    overlap_threshold: float = DEFAULT_OVERLAP_THRESHOLD,
) -> list[RankedClip]:
    """Convenience function to rank and select top viral clips.

    Args:
        clips: Viral clips from LLM analysis.
        segments: Parsed transcript segments.
        top_n: Maximum clips to return.
        settings: Optional settings override.
        overlap_threshold: Duplicate detection threshold.

    Returns:
        Top ranked clips.
    """
    return ClipRanker(settings=settings, overlap_threshold=overlap_threshold).rank(
        clips, segments, top_n=top_n
    )
