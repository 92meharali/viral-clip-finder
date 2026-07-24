"""Clip quality validation and filtering."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from loguru import logger

from app.core.config import Settings, get_settings
from app.core.exceptions import QualityCheckError
from app.models.clip import ViralClip
from app.models.quality import (
    ClipQualityResult,
    QualityFilterResult,
    QualityIssue,
    QualityIssueCode,
)
from app.models.transcript import TranscriptSegment

DEFAULT_MIN_VIRAL_SCORE = 5.0
DEFAULT_MAX_SILENCE_RATIO = 0.6
MAX_SPEECH_SEGMENT_SECONDS = 5.0


@dataclass(frozen=True)
class QualityThresholds:
    """Configurable thresholds for clip quality checks."""

    min_duration_seconds: int
    max_duration_seconds: int
    min_viral_score: float
    max_silence_ratio: float


def _thresholds_from_settings(settings: Settings) -> QualityThresholds:
    """Build quality thresholds from application settings."""
    return QualityThresholds(
        min_duration_seconds=settings.min_clip_duration_seconds,
        max_duration_seconds=settings.max_clip_duration_seconds,
        min_viral_score=settings.min_viral_score,
        max_silence_ratio=settings.max_silence_ratio,
    )


def _segments_in_clip(
    segments: list[TranscriptSegment],
    clip: ViralClip,
) -> list[TranscriptSegment]:
    """Return transcript segments within a clip window."""
    return sorted(
        (
            segment
            for segment in segments
            if clip.start_seconds <= segment.seconds < clip.end_seconds
        ),
        key=lambda segment: segment.seconds,
    )


def compute_silence_ratio(clip: ViralClip, segments: list[TranscriptSegment]) -> float:
    """Estimate the fraction of a clip without dialogue.

    Uses transcript segment spacing to approximate silent gaps.
    Returns ``1.0`` when no dialogue exists in the clip window.

    Args:
        clip: Clip with timing metadata.
        segments: Full parsed transcript.

    Returns:
        Silence ratio between 0.0 and 1.0.
    """
    in_window = _segments_in_clip(segments, clip)
    if not in_window:
        return 1.0

    speech_time = 0.0
    for index, segment in enumerate(in_window):
        if index + 1 < len(in_window):
            segment_end = in_window[index + 1].seconds
        else:
            segment_end = clip.end_seconds
        speech_time += min(
            max(0.0, segment_end - segment.seconds),
            MAX_SPEECH_SEGMENT_SECONDS,
        )

    speech_ratio = min(1.0, speech_time / clip.duration_seconds)
    return 1.0 - speech_ratio


def _dialogue_fingerprint(segments: list[TranscriptSegment], clip: ViralClip) -> str:
    """Build a normalized dialogue fingerprint for duplicate detection."""
    in_window = _segments_in_clip(segments, clip)
    return " ".join(segment.text.lower().strip() for segment in in_window)


def _has_internal_repeated_dialogue(segments: list[TranscriptSegment], clip: ViralClip) -> bool:
    """Detect duplicate dialogue lines within a single clip."""
    in_window = _segments_in_clip(segments, clip)
    normalized = [segment.text.lower().strip() for segment in in_window]
    return len(normalized) != len(set(normalized))


def check_clip_quality(
    clip: ViralClip,
    segments: list[TranscriptSegment],
    *,
    index: int,
    thresholds: QualityThresholds,
    seen_fingerprints: set[str],
) -> ClipQualityResult:
    """Run all quality checks against a single clip.

    Args:
        clip: Clip to validate.
        segments: Full transcript segments.
        index: 1-based clip index.
        thresholds: Quality thresholds.
        seen_fingerprints: Fingerprints from previously accepted clips in batch.

    Returns:
        :class:`ClipQualityResult` with pass/fail and issue list.
    """
    issues: list[QualityIssue] = []

    if clip.duration_seconds < thresholds.min_duration_seconds:
        issues.append(
            QualityIssue(
                code=QualityIssueCode.TOO_SHORT,
                message=(
                    f"Clip duration {clip.duration_seconds:.1f}s is below minimum "
                    f"{thresholds.min_duration_seconds}s"
                ),
            )
        )

    if clip.duration_seconds > thresholds.max_duration_seconds:
        issues.append(
            QualityIssue(
                code=QualityIssueCode.TOO_LONG,
                message=(
                    f"Clip duration {clip.duration_seconds:.1f}s exceeds maximum "
                    f"{thresholds.max_duration_seconds}s"
                ),
            )
        )

    silence_ratio = compute_silence_ratio(clip, segments)
    if silence_ratio > thresholds.max_silence_ratio:
        issues.append(
            QualityIssue(
                code=QualityIssueCode.TOO_MUCH_SILENCE,
                message=(
                    f"Estimated silence ratio {silence_ratio:.0%} exceeds maximum "
                    f"{thresholds.max_silence_ratio:.0%}"
                ),
            )
        )

    if clip.viral_score < thresholds.min_viral_score:
        issues.append(
            QualityIssue(
                code=QualityIssueCode.LOW_CONFIDENCE,
                message=(
                    f"Viral score {clip.viral_score:.1f} is below minimum "
                    f"{thresholds.min_viral_score:.1f}"
                ),
            )
        )

    if _has_internal_repeated_dialogue(segments, clip):
        issues.append(
            QualityIssue(
                code=QualityIssueCode.REPEATED_DIALOGUE,
                message="Clip contains repeated dialogue lines",
            )
        )

    fingerprint = _dialogue_fingerprint(segments, clip)
    if fingerprint and fingerprint in seen_fingerprints:
        issues.append(
            QualityIssue(
                code=QualityIssueCode.REPEATED_DIALOGUE,
                message="Clip dialogue duplicates another clip in the batch",
            )
        )

    return ClipQualityResult(
        index=index,
        clip_start=clip.start,
        clip_end=clip.end,
        viral_score=clip.viral_score,
        passed=len(issues) == 0,
        issues=issues,
    )


class ClipQualityChecker:
    """Validate viral clips against duration, silence, confidence, and dialogue checks."""

    def __init__(
        self,
        settings: Settings | None = None,
        thresholds: QualityThresholds | None = None,
    ) -> None:
        """Initialize the quality checker.

        Args:
            settings: Optional settings override.
            thresholds: Optional explicit thresholds override.
        """
        self.settings = settings or get_settings()
        self.thresholds = thresholds or _thresholds_from_settings(self.settings)

    def check(
        self,
        clips: Sequence[ViralClip],
        segments: list[TranscriptSegment],
    ) -> QualityFilterResult:
        """Evaluate clips and separate passed from rejected.

        Args:
            clips: Clips to validate.
            segments: Full parsed transcript for silence and dialogue checks.

        Returns:
            :class:`QualityFilterResult` with passed indices and rejected details.

        Raises:
            QualityCheckError: If inputs are empty.
        """
        if not clips:
            raise QualityCheckError("Cannot run quality checks on an empty clip list")

        logger.info("Running quality checks on {} clips", len(clips))

        passed_indices: list[int] = []
        rejected: list[ClipQualityResult] = []
        seen_fingerprints: set[str] = set()

        for index, clip in enumerate(clips, start=1):
            result = check_clip_quality(
                clip,
                segments,
                index=index,
                thresholds=self.thresholds,
                seen_fingerprints=seen_fingerprints,
            )

            if result.passed:
                passed_indices.append(index)
                fingerprint = _dialogue_fingerprint(segments, clip)
                if fingerprint:
                    seen_fingerprints.add(fingerprint)
                logger.debug("Clip {} passed quality checks", index)
            else:
                rejected.append(result)
                codes = ", ".join(issue.code.value for issue in result.issues)
                logger.info("Clip {} rejected: {}", index, codes)

        logger.info(
            "Quality checks complete: {} passed, {} rejected",
            len(passed_indices),
            len(rejected),
        )

        return QualityFilterResult(
            passed=passed_indices,
            rejected=rejected,
            total=len(clips),
        )

    def filter_clips(
        self,
        clips: Sequence[ViralClip],
        segments: list[TranscriptSegment],
    ) -> list[ViralClip]:
        """Return only clips that pass all quality checks.

        Args:
            clips: Clips to filter.
            segments: Parsed transcript segments.

        Returns:
            Clips that passed quality validation, preserving order.
        """
        report = self.check(clips, segments)
        return [clip for index, clip in enumerate(clips, start=1) if index in report.passed]


def filter_quality_clips(
    clips: Sequence[ViralClip],
    segments: list[TranscriptSegment],
    *,
    settings: Settings | None = None,
) -> tuple[list[ViralClip], QualityFilterResult]:
    """Convenience function to filter clips by quality.

    Args:
        clips: Clips to validate.
        segments: Parsed transcript segments.
        settings: Optional settings override.

    Returns:
        Tuple of (passed clips, full quality report).
    """
    checker = ClipQualityChecker(settings=settings)
    report = checker.check(clips, segments)
    passed = [clip for index, clip in enumerate(clips, start=1) if index in report.passed]
    return passed, report
