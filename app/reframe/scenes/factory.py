"""Scene detector factory."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.core.exceptions import UnknownSceneDetectorError
from app.reframe.scenes.base import SceneDetector
from app.reframe.scenes.ffmpeg import FFmpegSceneDetector
from app.reframe.scenes.histogram import HistogramSceneDetector

SUPPORTED_SCENE_DETECTORS = frozenset({"ffmpeg", "histogram"})


def get_scene_detector(
    settings: Settings | None = None,
    *,
    provider: str | None = None,
) -> SceneDetector:
    """Create a :class:`SceneDetector` for the configured backend."""
    resolved = settings or get_settings()
    detector_name = (provider or resolved.scene_detector).strip().lower()

    if detector_name not in SUPPORTED_SCENE_DETECTORS:
        supported = ", ".join(sorted(SUPPORTED_SCENE_DETECTORS))
        raise UnknownSceneDetectorError(
            f"Unknown scene detector '{detector_name}'. Supported detectors: {supported}"
        )

    if detector_name == "ffmpeg":
        return FFmpegSceneDetector(resolved)
    if detector_name == "histogram":
        return HistogramSceneDetector(resolved)

    raise UnknownSceneDetectorError(f"Detector '{detector_name}' is not implemented")
