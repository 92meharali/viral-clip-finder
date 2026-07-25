"""Face detection backends and service."""

from app.reframe.detection.base import FaceDetector
from app.reframe.detection.factory import SUPPORTED_FACE_DETECTORS, get_face_detector
from app.reframe.detection.service import FaceDetectionService, detect_faces_in_video

__all__ = [
    "FaceDetectionService",
    "FaceDetector",
    "SUPPORTED_FACE_DETECTORS",
    "detect_faces_in_video",
    "get_face_detector",
]
