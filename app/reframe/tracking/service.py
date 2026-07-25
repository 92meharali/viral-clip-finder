"""Face tracking orchestration service."""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from app.core.config import Settings, get_settings
from app.reframe.detection.service import FaceDetectionService
from app.reframe.models.faces import FrameFaces
from app.reframe.models.tracking import TrackingResult
from app.reframe.tracking.base import FaceTracker
from app.reframe.tracking.factory import get_face_tracker


class FaceTrackingService:
    """Assign persistent track ids to detected faces across frames."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        tracker: FaceTracker | None = None,
        detection_service: FaceDetectionService | None = None,
    ) -> None:
        """Initialize the face tracking service."""
        self.settings = settings or get_settings()
        self._tracker = tracker
        self._detection_service = detection_service

    @property
    def tracker(self) -> FaceTracker:
        """Lazy-initialize the configured face tracker."""
        if self._tracker is None:
            self._tracker = get_face_tracker(self.settings)
        return self._tracker

    @property
    def detection_service(self) -> FaceDetectionService:
        """Lazy-initialize the face detection service."""
        if self._detection_service is None:
            self._detection_service = FaceDetectionService(self.settings)
        return self._detection_service

    def track_frames(self, frames: list[FrameFaces]) -> TrackingResult:
        """Assign persistent track ids to an existing detection sequence."""
        self.tracker.reset()
        return self.tracker.track(frames)

    def track_video(
        self,
        video_path: str | Path,
        *,
        fps: float | None = None,
        frames_dir: str | Path | None = None,
    ) -> TrackingResult:
        """Detect and track faces across a full video."""
        source = Path(video_path).resolve()
        logger.info("Starting face tracking on {}", source.name)

        detections = self.detection_service.detect_video(
            source,
            fps=fps,
            frames_dir=frames_dir,
        )
        return self.track_frames(detections)

    def close(self) -> None:
        """Release tracker and detector resources."""
        self.tracker.reset()
        self.detection_service.close()


def track_faces_in_video(
    video_path: str | Path,
    *,
    settings: Settings | None = None,
    fps: float | None = None,
    frames_dir: str | Path | None = None,
) -> TrackingResult:
    """Convenience function to detect and track faces across a video."""
    service = FaceTrackingService(settings=settings)
    try:
        return service.track_video(video_path, fps=fps, frames_dir=frames_dir)
    finally:
        service.close()


def track_faces_in_frames(
    frames: list[FrameFaces],
    *,
    settings: Settings | None = None,
) -> TrackingResult:
    """Convenience function to track faces in precomputed detections."""
    service = FaceTrackingService(settings=settings)
    try:
        return service.track_frames(frames)
    finally:
        service.close()
