"""Scene detection orchestration service."""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from app.core.config import Settings, get_settings
from app.reframe.models.scenes import SceneDetectionResult
from app.reframe.scenes.base import SceneDetector
from app.reframe.scenes.factory import get_scene_detector


class SceneDetectionService:
    """Detect shot boundaries and build scene segments for a video."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        detector: SceneDetector | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._detector = detector

    @property
    def detector(self) -> SceneDetector:
        if self._detector is None:
            self._detector = get_scene_detector(self.settings)
        return self._detector

    def detect(self, video_path: str | Path) -> SceneDetectionResult:
        """Detect scene boundaries in a video."""
        source = Path(video_path).resolve()
        logger.info("Starting scene detection on {} with {}", source.name, self.detector.detector_name)
        return self.detector.detect(source)


def detect_scenes(
    video_path: str | Path,
    *,
    settings: Settings | None = None,
) -> SceneDetectionResult:
    """Convenience function to detect scenes in a video."""
    return SceneDetectionService(settings=settings).detect(video_path)
