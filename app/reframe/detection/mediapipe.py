"""MediaPipe face detection backend."""

# mypy: disable-error-code=import-not-found

from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger

from app.core.config import Settings, get_settings
from app.core.exceptions import FaceDetectionError
from app.reframe.detection.base import FaceDetector
from app.reframe.models.faces import BoundingBox, DetectedFace, FaceLandmarks

_MODEL_DIR = Path(__file__).resolve().parent / "models"
_SHORT_RANGE_MODEL = _MODEL_DIR / "blaze_face_short_range.tflite"
_FULL_RANGE_MODEL = _MODEL_DIR / "blaze_face_full_range.tflite"

# MediaPipe Face Detection keypoint indices.
_KEYPOINT_RIGHT_EYE = 0
_KEYPOINT_LEFT_EYE = 1
_KEYPOINT_NOSE = 2
_KEYPOINT_MOUTH = 3


def _load_rgb_image(image_path: str) -> tuple[object, int, int]:
    """Load an image as an RGB numpy array."""
    try:
        from PIL import Image
    except ImportError as exc:
        raise FaceDetectionError(
            "Pillow is required for face detection. Install with: uv sync --extra vision"
        ) from exc

    path = Path(image_path)
    if not path.exists():
        raise FaceDetectionError(f"Frame image not found: {image_path}")

    try:
        image = Image.open(path).convert("RGB")
    except OSError as exc:
        raise FaceDetectionError(f"Could not read frame image: {image_path}") from exc

    import numpy as np

    array = np.asarray(image)
    return array, image.width, image.height


def _landmarks_from_keypoints(
    detection: Any,
    *,
    width: int,
    height: int,
) -> FaceLandmarks | None:
    """Extract eye and mouth landmarks from MediaPipe keypoints."""
    keypoints = detection.keypoints
    if not keypoints:
        return None

    def point(index: int) -> tuple[float, float] | None:
        if index >= len(keypoints):
            return None
        kp = keypoints[index]
        return (kp.x * width, kp.y * height)

    return FaceLandmarks(
        right_eye=point(_KEYPOINT_RIGHT_EYE),
        left_eye=point(_KEYPOINT_LEFT_EYE),
        nose=point(_KEYPOINT_NOSE),
        mouth=point(_KEYPOINT_MOUTH),
    )


class MediaPipeFaceDetector(FaceDetector):
    """Detect faces using Google MediaPipe Face Detection."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the MediaPipe detector.

        Args:
            settings: Optional settings override.
        """
        self.settings = settings or get_settings()
        self._detector: Any | None = None

    @property
    def detector_name(self) -> str:
        return "mediapipe"

    def _model_path(self) -> Path:
        """Resolve the bundled BlazeFace model path."""
        full_range = _FULL_RANGE_MODEL
        short_range = _SHORT_RANGE_MODEL
        if full_range.exists():
            return full_range
        if short_range.exists():
            return short_range
        raise FaceDetectionError(
            "MediaPipe face models not found. Expected bundled models under "
            f"{_MODEL_DIR}. Reinstall with: uv sync --extra vision"
        )

    def _get_detector(self) -> Any:
        """Lazy-initialize the MediaPipe face detector."""
        if self._detector is not None:
            return self._detector

        try:
            from mediapipe import Image  # noqa: F401
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision
        except ImportError as exc:
            raise FaceDetectionError(
                "MediaPipe is not installed. Install with: uv sync --extra vision"
            ) from exc

        model_path = self._model_path()
        options = vision.FaceDetectorOptions(
            base_options=python.BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.IMAGE,
            min_detection_confidence=self.settings.face_detection_min_confidence,
        )
        self._detector = vision.FaceDetector.create_from_options(options)
        logger.debug(
            "Initialized MediaPipe face detector ({}, confidence >= {})",
            model_path.name,
            self.settings.face_detection_min_confidence,
        )
        return self._detector

    def detect(
        self,
        image_path: str,
        *,
        frame_number: int = 0,
        timestamp: float = 0.0,
    ) -> list[DetectedFace]:
        from mediapipe import Image, ImageFormat

        image, width, height = _load_rgb_image(image_path)
        detector = self._get_detector()
        mp_image = Image(image_format=ImageFormat.SRGB, data=image)
        results = detector.detect(mp_image)

        if not results.detections:
            return []

        faces: list[DetectedFace] = []
        min_size = self.settings.minimum_face_size

        for index, detection in enumerate(results.detections):
            confidence = (
                float(detection.categories[0].score) if detection.categories else 0.0
            )
            bbox = detection.bounding_box
            bounding_box = BoundingBox(
                x=float(bbox.origin_x),
                y=float(bbox.origin_y),
                width=float(bbox.width),
                height=float(bbox.height),
            )

            if bounding_box.width < min_size or bounding_box.height < min_size:
                logger.debug(
                    "Skipping small face {}x{} below minimum {}",
                    bounding_box.width,
                    bounding_box.height,
                    min_size,
                )
                continue

            faces.append(
                DetectedFace(
                    id=f"frame{frame_number}_face{index}",
                    bounding_box=bounding_box,
                    confidence=confidence,
                    landmarks=_landmarks_from_keypoints(detection, width=width, height=height),
                )
            )

        faces.sort(key=lambda face: face.confidence, reverse=True)
        logger.debug(
            "Detected {} faces in frame {} ({:.2f}s)",
            len(faces),
            frame_number,
            timestamp,
        )
        return faces

    def close(self) -> None:
        """Release MediaPipe resources."""
        if self._detector is not None:
            self._detector.close()
            self._detector = None
