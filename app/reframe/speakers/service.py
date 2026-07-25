"""Active speaker estimation orchestration service."""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from app.core.config import Settings, get_settings
from app.models.transcript import TranscriptSegment
from app.reframe.models.speakers import SpeakerEstimationResult
from app.reframe.models.tracking import TrackingResult
from app.reframe.speakers.base import ActiveSpeakerEstimator
from app.reframe.speakers.factory import get_speaker_estimator
from app.reframe.tracking.service import FaceTrackingService


class ActiveSpeakerEstimationService:
    """Estimate active speakers from tracked faces and supporting signals."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        estimator: ActiveSpeakerEstimator | None = None,
        tracking_service: FaceTrackingService | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._estimator = estimator
        self._tracking_service = tracking_service

    @property
    def estimator(self) -> ActiveSpeakerEstimator:
        if self._estimator is None:
            self._estimator = get_speaker_estimator(self.settings)
        return self._estimator

    @property
    def tracking_service(self) -> FaceTrackingService:
        if self._tracking_service is None:
            self._tracking_service = FaceTrackingService(self.settings)
        return self._tracking_service

    def estimate(
        self,
        tracking: TrackingResult,
        *,
        transcript_segments: list[TranscriptSegment] | None = None,
        video_path: str | Path | None = None,
        video_duration: float | None = None,
    ) -> SpeakerEstimationResult:
        """Estimate active speakers for an existing tracking result."""
        logger.info(
            "Estimating active speakers across {} tracked frames with {}",
            len(tracking.frames),
            self.estimator.estimator_name,
        )
        resolved_path = Path(video_path).resolve() if video_path is not None else None
        return self.estimator.estimate(
            tracking,
            transcript_segments=transcript_segments,
            video_path=resolved_path,
            video_duration=video_duration,
        )

    def estimate_video(
        self,
        video_path: str | Path,
        *,
        transcript_segments: list[TranscriptSegment] | None = None,
        fps: float | None = None,
        frames_dir: str | Path | None = None,
    ) -> SpeakerEstimationResult:
        """Track faces and estimate active speakers for a full video."""
        source = Path(video_path).resolve()
        logger.info("Starting active speaker estimation on {}", source.name)

        tracking = self.tracking_service.track_video(
            source,
            fps=fps,
            frames_dir=frames_dir,
        )
        return self.estimate(
            tracking,
            transcript_segments=transcript_segments,
            video_path=source,
        )

    def close(self) -> None:
        """Release tracking resources."""
        self.tracking_service.close()


def estimate_active_speakers(
    tracking: TrackingResult,
    *,
    settings: Settings | None = None,
    transcript_segments: list[TranscriptSegment] | None = None,
    video_path: str | Path | None = None,
    video_duration: float | None = None,
) -> SpeakerEstimationResult:
    """Convenience function to estimate active speakers from tracking data."""
    service = ActiveSpeakerEstimationService(settings=settings)
    try:
        return service.estimate(
            tracking,
            transcript_segments=transcript_segments,
            video_path=video_path,
            video_duration=video_duration,
        )
    finally:
        service.close()


def estimate_active_speakers_in_video(
    video_path: str | Path,
    *,
    settings: Settings | None = None,
    transcript_segments: list[TranscriptSegment] | None = None,
    fps: float | None = None,
    frames_dir: str | Path | None = None,
) -> SpeakerEstimationResult:
    """Convenience function to track faces and estimate active speakers."""
    service = ActiveSpeakerEstimationService(settings=settings)
    try:
        return service.estimate_video(
            video_path,
            transcript_segments=transcript_segments,
            fps=fps,
            frames_dir=frames_dir,
        )
    finally:
        service.close()
