"""Scene detection backends and service."""

from app.reframe.scenes.base import SceneDetector
from app.reframe.scenes.factory import SUPPORTED_SCENE_DETECTORS, get_scene_detector
from app.reframe.scenes.ffmpeg import FFmpegSceneDetector
from app.reframe.scenes.histogram import HistogramSceneDetector
from app.reframe.scenes.service import SceneDetectionService, detect_scenes

__all__ = [
    "FFmpegSceneDetector",
    "HistogramSceneDetector",
    "SUPPORTED_SCENE_DETECTORS",
    "SceneDetectionService",
    "SceneDetector",
    "detect_scenes",
    "get_scene_detector",
]
