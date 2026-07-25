"""Face detection orchestration service."""

# mypy: disable-error-code=import-not-found

from __future__ import annotations

import tempfile
from pathlib import Path

from loguru import logger

from app.core.config import Settings, get_settings
from app.reframe.detection.base import FaceDetector
from app.reframe.detection.factory import get_face_detector
from app.reframe.frames.extractor import FrameExtractor
from app.reframe.models.faces import FrameFaces, VideoFrame


class FaceDetectionService:
    """Extract frames from video and detect faces in each frame."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        detector: FaceDetector | None = None,
        frame_extractor: FrameExtractor | None = None,
    ) -> None:
        """Initialize the face detection service."""
        self.settings = settings or get_settings()
        self._detector = detector
        self._frame_extractor = frame_extractor or FrameExtractor(self.settings)

    @property
    def detector(self) -> FaceDetector:
        """Lazy-initialize the configured face detector."""
        if self._detector is None:
            self._detector = get_face_detector(self.settings)
        return self._detector

    def detect_video(
        self,
        video_path: str | Path,
        *,
        fps: float | None = None,
        frames_dir: str | Path | None = None,
    ) -> list[FrameFaces]:
        """Run face detection across an entire video.

        Pipeline: frame extraction → per-frame detection → :class:`FrameFaces`.

        Args:
            video_path: Source video file.
            fps: Optional frame sample rate override.
            frames_dir: Optional directory to persist extracted frames.

        Returns:
            Face detection results for each sampled frame.
        """
        source = Path(video_path).resolve()
        logger.info("Starting face detection on {}", source.name)

        if frames_dir is not None:
            frames = self._frame_extractor.extract(source, frames_dir, fps=fps)
            return self._detect_frames(frames)

        with tempfile.TemporaryDirectory(prefix="reframe_frames_") as temp_dir:
            frames = self._frame_extractor.extract(source, temp_dir, fps=fps)
            return self._detect_frames(frames)

    def detect_frame(self, image_path: str | Path, *, timestamp: float = 0.0) -> FrameFaces:
        """Detect faces in a single image file."""
        path = Path(image_path).resolve()
        faces = self.detector.detect(
            str(path),
            frame_number=0,
            timestamp=timestamp,
        )

        try:
            from PIL import Image

            with Image.open(path) as image:
                width, height = image.size
        except ImportError:
            width, height = 1920, 1080

        return FrameFaces(
            frame_number=0,
            timestamp=timestamp,
            image_width=width,
            image_height=height,
            faces=faces,
        )

    def _detect_frames(self, frames: list[VideoFrame]) -> list[FrameFaces]:
        """Run detection on a list of extracted frames."""
        results: list[FrameFaces] = []
        for frame in frames:
            faces = self.detector.detect(
                frame.image_path,
                frame_number=frame.frame_number,
                timestamp=frame.timestamp,
            )
            results.append(
                FrameFaces(
                    frame_number=frame.frame_number,
                    timestamp=frame.timestamp,
                    image_width=frame.width,
                    image_height=frame.height,
                    faces=faces,
                )
            )

        total_faces = sum(item.face_count for item in results)
        logger.info(
            "Face detection complete: {} frames, {} total face detections",
            len(results),
            total_faces,
        )
        return results

    def close(self) -> None:
        """Release detector resources."""
        self.detector.close()


def detect_faces_in_video(
    video_path: str | Path,
    *,
    settings: Settings | None = None,
    fps: float | None = None,
    frames_dir: str | Path | None = None,
) -> list[FrameFaces]:
    """Convenience function to detect faces across a video."""
    service = FaceDetectionService(settings=settings)
    try:
        return service.detect_video(video_path, fps=fps, frames_dir=frames_dir)
    finally:
        service.close()
