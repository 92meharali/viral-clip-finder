"""Face detector factory."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.core.exceptions import UnknownFaceDetectorError
from app.reframe.detection.base import FaceDetector
from app.reframe.detection.mediapipe import MediaPipeFaceDetector

SUPPORTED_FACE_DETECTORS = frozenset({"mediapipe"})


def get_face_detector(
    settings: Settings | None = None,
    *,
    provider: str | None = None,
) -> FaceDetector:
    """Create a :class:`FaceDetector` for the configured backend.

    Args:
        settings: Optional settings override.
        provider: Detector name override (``mediapipe``).

    Returns:
        Configured face detector instance.

    Raises:
        UnknownFaceDetectorError: If the detector name is not supported.
    """
    resolved = settings or get_settings()
    detector_name = (provider or resolved.face_detector).strip().lower()

    if detector_name not in SUPPORTED_FACE_DETECTORS:
        supported = ", ".join(sorted(SUPPORTED_FACE_DETECTORS))
        raise UnknownFaceDetectorError(
            f"Unknown face detector '{detector_name}'. Supported detectors: {supported}"
        )

    if detector_name == "mediapipe":
        return MediaPipeFaceDetector(resolved)

    raise UnknownFaceDetectorError(f"Detector '{detector_name}' is not implemented")
