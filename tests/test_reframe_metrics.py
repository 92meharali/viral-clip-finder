"""Tests for reframe evaluation metrics."""

from __future__ import annotations

from app.reframe.crop.geometry import camera_state_to_crop
from app.reframe.metrics.evaluation import evaluate_reframe
from app.reframe.models.camera import CameraPath, VirtualCameraFrame
from app.reframe.models.crop import CropPlan
from app.reframe.models.faces import BoundingBox
from app.reframe.models.tracking import FrameTracks, TrackedFace, TrackingResult


def _tracked_face(track_id: str, x: float, y: float) -> TrackedFace:
    return TrackedFace(
        track_id=track_id,
        bounding_box=BoundingBox(x=x, y=y, width=120, height=150),
        detection_confidence=0.95,
    )


class TestEvaluateReframe:
    def test_computes_face_visibility_metrics(self) -> None:
        tracking = TrackingResult(
            frames=[
                FrameTracks(
                    frame_number=0,
                    timestamp=0.0,
                    image_width=1920,
                    image_height=1080,
                    faces=[_tracked_face("person_1", 860, 420)],
                    active_track_ids=["person_1"],
                )
            ],
            tracks={},
        )
        crop = camera_state_to_crop(
            frame_number=0,
            timestamp=0.0,
            center_x=920.0,
            center_y=500.0,
            crop_width=700.0,
            crop_height=1244.0,
        )
        crop_plan = CropPlan(
            source_width=1920,
            source_height=1080,
            target_width=1080,
            target_height=1920,
            frames=[crop],
        )
        camera_path = CameraPath(
            source_width=1920,
            source_height=1080,
            target_aspect=1080 / 1920,
            frames=[
                VirtualCameraFrame(
                    frame_number=0,
                    timestamp=0.0,
                    center_x=920.0,
                    center_y=500.0,
                    zoom=700.0,
                    crop_height=1244.0,
                ),
                VirtualCameraFrame(
                    frame_number=1,
                    timestamp=1.0,
                    center_x=950.0,
                    center_y=510.0,
                    zoom=710.0,
                    crop_height=1244.0,
                    velocity_x=30.0,
                    velocity_y=10.0,
                ),
            ],
        )

        metrics = evaluate_reframe(
            tracking=tracking,
            crop_plan=crop_plan,
            camera_path=camera_path,
        )

        assert metrics.average_face_visibility > 0.9
        assert metrics.camera_movement_distance > 0.0
        assert metrics.frame_count == 1
