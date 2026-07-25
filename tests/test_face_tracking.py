"""Tests for face tracking."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.exceptions import UnknownFaceTrackerError
from app.reframe.models.faces import BoundingBox, DetectedFace, FrameFaces
from app.reframe.tracking.factory import get_face_tracker
from app.reframe.tracking.geometry import center_distance, intersection_over_union
from app.reframe.tracking.iou import IoUFaceTracker
from app.reframe.tracking.service import FaceTrackingService, track_faces_in_frames


def _face(x: float, y: float, *, size: float = 100, confidence: float = 0.9) -> DetectedFace:
    return DetectedFace(
        id=None,
        bounding_box=BoundingBox(x=x, y=y, width=size, height=size),
        confidence=confidence,
    )


def _frame(
    frame_number: int,
    faces: list[DetectedFace],
    *,
    timestamp: float | None = None,
) -> FrameFaces:
    return FrameFaces(
        frame_number=frame_number,
        timestamp=timestamp if timestamp is not None else float(frame_number),
        image_width=1920,
        image_height=1080,
        faces=faces,
    )


@pytest.fixture
def settings() -> Settings:
    return Settings(
        face_tracker="iou",
        tracking_iou_threshold=0.3,
        tracking_max_center_distance=250.0,
        tracking_max_age=3,
    )


class TestGeometry:
    def test_iou_identical_boxes(self) -> None:
        box = BoundingBox(x=100, y=100, width=50, height=50)
        assert intersection_over_union(box, box) == 1.0

    def test_iou_disjoint_boxes(self) -> None:
        a = BoundingBox(x=0, y=0, width=50, height=50)
        b = BoundingBox(x=200, y=200, width=50, height=50)
        assert intersection_over_union(a, b) == 0.0

    def test_center_distance(self) -> None:
        a = BoundingBox(x=0, y=0, width=100, height=100)
        b = BoundingBox(x=200, y=0, width=100, height=100)
        assert center_distance(a, b) == 200.0


class TestIoUFaceTracker:
    def test_single_face_keeps_same_track_id(self, settings: Settings) -> None:
        frames = [
            _frame(0, [_face(400, 200)]),
            _frame(1, [_face(405, 202)]),
            _frame(2, [_face(410, 205)]),
        ]
        result = IoUFaceTracker(settings=settings).track(frames)

        assert result.track_count == 1
        assert result.frames[0].faces[0].track_id == result.frames[2].faces[0].track_id

    def test_two_faces_get_distinct_track_ids(self, settings: Settings) -> None:
        frames = [
            _frame(0, [_face(200, 200), _face(800, 200)]),
            _frame(1, [_face(205, 205), _face(805, 205)]),
        ]
        result = IoUFaceTracker(settings=settings).track(frames)

        assert result.track_count == 2
        ids_frame_0 = {face.track_id for face in result.frames[0].faces}
        ids_frame_1 = {face.track_id for face in result.frames[1].faces}
        assert ids_frame_0 == ids_frame_1

    def test_occluded_face_recovers_same_track(self, settings: Settings) -> None:
        frames = [
            _frame(0, [_face(400, 200)]),
            _frame(1, []),
            _frame(2, []),
            _frame(3, [_face(415, 210)]),
        ]
        result = IoUFaceTracker(settings=settings).track(frames)

        assert result.frames[0].face_count == 1
        assert result.frames[1].face_count == 0
        assert result.frames[3].face_count == 1
        assert (
            result.frames[0].faces[0].track_id == result.frames[3].faces[0].track_id
        )

    def test_new_face_gets_new_track_id(self, settings: Settings) -> None:
        frames = [
            _frame(0, [_face(200, 200)]),
            _frame(1, [_face(200, 200), _face(900, 200)]),
        ]
        result = IoUFaceTracker(settings=settings).track(frames)

        assert result.track_count == 2
        assert result.frames[1].face_count == 2

    def test_track_summary_records_lifecycle(self, settings: Settings) -> None:
        frames = [
            _frame(0, [_face(400, 200)], timestamp=0.0),
            _frame(1, [_face(405, 202)], timestamp=0.5),
        ]
        result = IoUFaceTracker(settings=settings).track(frames)
        summary = next(iter(result.tracks.values()))

        assert summary.total_detections == 2
        assert summary.first_frame == 0
        assert summary.last_frame == 1
        assert summary.duration_seconds == 0.5


class TestFaceTrackerFactory:
    def test_creates_iou_tracker(self, settings: Settings) -> None:
        tracker = get_face_tracker(settings)
        assert tracker.tracker_name == "iou"

    def test_unknown_tracker_raises(self, settings: Settings) -> None:
        settings = settings.model_copy(update={"face_tracker": "deepsort"})
        with pytest.raises(UnknownFaceTrackerError, match="deepsort"):
            get_face_tracker(settings)


class TestFaceTrackingService:
    def test_track_frames_delegates_to_tracker(self, settings: Settings) -> None:
        frames = [_frame(0, [_face(100, 100)]), _frame(1, [_face(105, 105)])]
        result = FaceTrackingService(settings).track_frames(frames)

        assert result.track_count == 1
        assert len(result.frames) == 2

    def test_track_faces_in_frames_convenience(self, settings: Settings) -> None:
        frames = [_frame(0, [_face(300, 300)])]
        result = track_faces_in_frames(frames, settings=settings)
        assert result.frames[0].faces[0].track_id == "person_1"
