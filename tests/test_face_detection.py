"""Tests for face detection models and service."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings
from app.core.exceptions import UnknownFaceDetectorError
from app.reframe.detection.factory import get_face_detector
from app.reframe.detection.service import FaceDetectionService
from app.reframe.models.faces import BoundingBox, DetectedFace, FaceLandmarks, FrameFaces, VideoFrame


class TestBoundingBox:
    def test_center_and_area(self) -> None:
        box = BoundingBox(x=100, y=50, width=200, height=100)
        assert box.center == (200.0, 100.0)
        assert box.area == 20000

    def test_contains_point(self) -> None:
        box = BoundingBox(x=10, y=10, width=20, height=20)
        assert box.contains_point(15, 15)
        assert not box.contains_point(50, 50)

    def test_expand_adds_padding(self) -> None:
        box = BoundingBox(x=10, y=10, width=20, height=20)
        expanded = box.expand(5)
        assert expanded.x == 5
        assert expanded.width == 30


class TestFrameFaces:
    def test_face_count(self) -> None:
        frame = FrameFaces(
            frame_number=0,
            timestamp=0.0,
            image_width=1920,
            image_height=1080,
            faces=[
                DetectedFace(
                    id="face0",
                    bounding_box=BoundingBox(x=0, y=0, width=100, height=100),
                    confidence=0.9,
                )
            ],
        )
        assert frame.face_count == 1


class MockFaceDetector:
    """Test double for face detection."""

    detector_name = "mock"

    def __init__(self, faces: list[DetectedFace] | None = None) -> None:
        self.faces = faces or []
        self.calls: list[str] = []

    def detect(
        self,
        image_path: str,
        *,
        frame_number: int = 0,
        timestamp: float = 0.0,
    ) -> list[DetectedFace]:
        self.calls.append(image_path)
        return self.faces

    def close(self) -> None:
        return None


@pytest.fixture
def settings() -> Settings:
    return Settings(
        face_detector="mediapipe",
        face_detection_min_confidence=0.5,
        face_extraction_fps=2.0,
        minimum_face_size=40,
    )


@pytest.fixture
def sample_face() -> DetectedFace:
    return DetectedFace(
        id="frame0_face0",
        bounding_box=BoundingBox(x=400, y=100, width=160, height=200),
        confidence=0.95,
        landmarks=FaceLandmarks(
            left_eye=(460, 150),
            right_eye=(520, 152),
            nose=(490, 180),
            mouth=(488, 220),
        ),
    )


class TestFaceDetectorFactory:
    def test_creates_mediapipe_detector(self, settings: Settings) -> None:
        detector = get_face_detector(settings)
        assert detector.detector_name == "mediapipe"

    def test_unknown_detector_raises(self, settings: Settings) -> None:
        settings = settings.model_copy(update={"face_detector": "retinaface"})
        with pytest.raises(UnknownFaceDetectorError, match="retinaface"):
            get_face_detector(settings)


class TestFaceDetectionService:
    def test_detect_video_runs_extraction_and_detection(
        self,
        settings: Settings,
        sample_face: DetectedFace,
        tmp_path: Path,
    ) -> None:
        frame_path = tmp_path / "frame_000001.jpg"
        frame_path.write_bytes(b"jpg")

        frames = [
            VideoFrame(
                frame_number=0,
                timestamp=0.0,
                image_path=str(frame_path),
                width=1920,
                height=1080,
            )
        ]
        detector = MockFaceDetector(faces=[sample_face])
        extractor = MagicMock()
        extractor.extract.return_value = frames

        service = FaceDetectionService(settings, detector=detector, frame_extractor=extractor)
        results = service.detect_video("video.mp4", frames_dir=tmp_path / "frames")

        assert len(results) == 1
        assert results[0].face_count == 1
        assert results[0].faces[0].confidence == 0.95
        extractor.extract.assert_called_once()

    def test_detect_frame_returns_frame_faces(
        self,
        settings: Settings,
        sample_face: DetectedFace,
        tmp_path: Path,
    ) -> None:
        image = tmp_path / "still.jpg"
        image.write_bytes(b"fake")

        detector = MockFaceDetector(faces=[sample_face])
        service = FaceDetectionService(settings, detector=detector)
        result = service.detect_frame(image, timestamp=1.5)

        assert isinstance(result, FrameFaces)
        assert result.timestamp == 1.5
        assert result.face_count == 1
        assert len(detector.calls) == 1


class TestMediaPipeDetector:
    def test_detects_on_blank_image_when_mediapipe_installed(
        self,
        settings: Settings,
        tmp_path: Path,
    ) -> None:
        pytest.importorskip("mediapipe")
        from PIL import Image

        from app.reframe.detection.mediapipe import MediaPipeFaceDetector

        image_path = tmp_path / "blank.jpg"
        Image.new("RGB", (640, 480), color=(30, 30, 30)).save(image_path)

        detector = MediaPipeFaceDetector(settings)
        try:
            faces = detector.detect(str(image_path))
        finally:
            detector.close()

        assert isinstance(faces, list)
