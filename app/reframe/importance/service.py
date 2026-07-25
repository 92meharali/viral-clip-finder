"""Importance scoring orchestration service."""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from app.core.config import Settings, get_settings
from app.models.transcript import TranscriptSegment
from app.reframe.importance.base import ImportanceScorer
from app.reframe.importance.factory import get_importance_scorer
from app.reframe.models.importance import ImportanceScoringResult
from app.reframe.models.speakers import SpeakerEstimationResult
from app.reframe.models.tracking import TrackingResult
from app.reframe.speakers.service import ActiveSpeakerEstimationService
from app.reframe.tracking.service import FaceTrackingService


class ImportanceScoringService:
    """Score how much attention each tracked person deserves over time."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        scorer: ImportanceScorer | None = None,
        speaker_service: ActiveSpeakerEstimationService | None = None,
        tracking_service: FaceTrackingService | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._scorer = scorer
        self._speaker_service = speaker_service
        self._tracking_service = tracking_service

    @property
    def scorer(self) -> ImportanceScorer:
        if self._scorer is None:
            self._scorer = get_importance_scorer(self.settings)
        return self._scorer

    @property
    def speaker_service(self) -> ActiveSpeakerEstimationService:
        if self._speaker_service is None:
            self._speaker_service = ActiveSpeakerEstimationService(self.settings)
        return self._speaker_service

    @property
    def tracking_service(self) -> FaceTrackingService:
        if self._tracking_service is None:
            self._tracking_service = FaceTrackingService(self.settings)
        return self._tracking_service

    def score(
        self,
        tracking: TrackingResult,
        *,
        speaker_result: SpeakerEstimationResult | None = None,
        transcript_segments: list[TranscriptSegment] | None = None,
        video_path: str | Path | None = None,
    ) -> ImportanceScoringResult:
        """Score importance for an existing tracking result."""
        resolved_speaker = speaker_result
        if resolved_speaker is None and transcript_segments is not None:
            resolved_speaker = self.speaker_service.estimate(
                tracking,
                transcript_segments=transcript_segments,
                video_path=video_path,
            )

        logger.info(
            "Scoring importance across {} tracked frames with {}",
            len(tracking.frames),
            self.scorer.scorer_name,
        )
        return self.scorer.score(tracking, speaker_result=resolved_speaker)

    def score_video(
        self,
        video_path: str | Path,
        *,
        transcript_segments: list[TranscriptSegment] | None = None,
        fps: float | None = None,
        frames_dir: str | Path | None = None,
    ) -> ImportanceScoringResult:
        """Track faces, estimate speakers, and score importance for a video."""
        source = Path(video_path).resolve()
        logger.info("Starting importance scoring on {}", source.name)

        tracking = self.tracking_service.track_video(
            source,
            fps=fps,
            frames_dir=frames_dir,
        )
        return self.score(
            tracking,
            transcript_segments=transcript_segments,
            video_path=source,
        )

    def close(self) -> None:
        """Release tracking and speaker estimation resources."""
        self.speaker_service.close()
        self.tracking_service.close()


def score_importance(
    tracking: TrackingResult,
    *,
    settings: Settings | None = None,
    speaker_result: SpeakerEstimationResult | None = None,
    transcript_segments: list[TranscriptSegment] | None = None,
    video_path: str | Path | None = None,
) -> ImportanceScoringResult:
    """Convenience function to score importance from tracking data."""
    service = ImportanceScoringService(settings=settings)
    try:
        return service.score(
            tracking,
            speaker_result=speaker_result,
            transcript_segments=transcript_segments,
            video_path=video_path,
        )
    finally:
        service.close()


def score_importance_in_video(
    video_path: str | Path,
    *,
    settings: Settings | None = None,
    transcript_segments: list[TranscriptSegment] | None = None,
    fps: float | None = None,
    frames_dir: str | Path | None = None,
) -> ImportanceScoringResult:
    """Convenience function to track faces and score importance."""
    service = ImportanceScoringService(settings=settings)
    try:
        return service.score_video(
            video_path,
            transcript_segments=transcript_segments,
            fps=fps,
            frames_dir=frames_dir,
        )
    finally:
        service.close()
