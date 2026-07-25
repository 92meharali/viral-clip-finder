"""Tests for safe crop generation."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.exceptions import UnknownCropGeneratorError
from app.reframe.crop.factory import get_crop_generator
from app.reframe.crop.generator import SafeCropGenerator
from app.reframe.crop.geometry import (
    camera_state_to_crop,
    clamp_crop_to_source,
    crop_from_center,
    enforce_face_safety,
    face_visibility_ratio,
    max_vertical_crop_size,
    pan_fixed_crop_for_faces,
)
from app.reframe.crop.interpolate import interpolate_crop_frames, merge_crop_segments
from app.reframe.crop.service import SafeCropService, generate_crop_plan
from app.reframe.models.camera import CameraPath, VirtualCameraFrame
from app.reframe.models.crop import CropFrame
from app.reframe.models.faces import BoundingBox
from app.reframe.models.tracking import FrameTracks, TrackedFace, TrackingResult


def _tracked_face(track_id: str, x: float, y: float) -> TrackedFace:
    return TrackedFace(
        track_id=track_id,
        bounding_box=BoundingBox(x=x, y=y, width=120, height=150),
        detection_confidence=0.95,
    )


def _frame(frame_number: int, faces: list[TrackedFace], *, timestamp: float | None = None) -> FrameTracks:
    return FrameTracks(
        frame_number=frame_number,
        timestamp=timestamp if timestamp is not None else float(frame_number),
        image_width=1920,
        image_height=1080,
        faces=faces,
        active_track_ids=[face.track_id for face in faces],
    )


@pytest.fixture
def settings() -> Settings:
    return Settings(
        crop_generator="safe",
        crop_face_safety_padding=20,
        vertical_width=1080,
        vertical_height=1920,
        reframe_segment_merge_threshold=5.0,
    )


class TestCropGeometry:
    def test_clamp_crop_stays_inside_source(self) -> None:
        crop = CropFrame(frame_number=0, timestamp=0.0, x=-50, y=-20, width=2200, height=1400)
        clamped = clamp_crop_to_source(
            crop,
            source_width=1920,
            source_height=1080,
            target_aspect=1080 / 1920,
        )

        assert clamped.x >= 0
        assert clamped.y >= 0
        assert clamped.x + clamped.width <= 1920
        assert clamped.y + clamped.height <= 1080

    def test_enforce_face_safety_includes_face(self) -> None:
        crop = CropFrame(frame_number=0, timestamp=0.0, x=0, y=0, width=400, height=700)
        face = _tracked_face("person_1", 1500, 500)
        safe = enforce_face_safety(
            crop,
            [face],
            source_width=1920,
            source_height=1080,
            target_aspect=1080 / 1920,
            face_padding=20,
        )

        assert face_visibility_ratio(safe, face) >= 0.95

    def test_max_vertical_crop_size_matches_target_aspect(self) -> None:
        width, height = max_vertical_crop_size(1920, 1080, 1080 / 1920)
        assert width / height == pytest.approx(1080 / 1920, rel=1e-3)
        assert width <= 1920
        assert height <= 1080

    def test_pan_only_crop_keeps_fixed_dimensions(self) -> None:
        fixed_width, fixed_height = max_vertical_crop_size(1920, 1080, 1080 / 1920)
        crop = crop_from_center(
            frame_number=0,
            timestamp=0.0,
            center_x=960.0,
            center_y=540.0,
            crop_width=fixed_width,
            crop_height=fixed_height,
            source_width=1920,
            source_height=1080,
        )
        face = _tracked_face("person_1", 1400, 500)
        panned = pan_fixed_crop_for_faces(
            crop,
            [face],
            source_width=1920,
            source_height=1080,
            face_padding=20,
        )

        assert panned.width == pytest.approx(fixed_width)
        assert panned.height == pytest.approx(fixed_height)
        assert face_visibility_ratio(panned, face) >= 0.95


class TestCropInterpolation:
    def test_interpolate_crop_frames(self) -> None:
        frames = [
            CropFrame(frame_number=0, timestamp=0.0, x=100, y=100, width=500, height=900),
            CropFrame(frame_number=1, timestamp=1.0, x=200, y=120, width=520, height=920),
        ]

        interpolated = interpolate_crop_frames(frames, duration_seconds=1.0, render_fps=2.0)

        assert len(interpolated) >= 2
        assert interpolated[0].timestamp == 0.0
        assert interpolated[-1].timestamp == pytest.approx(1.0)

    def test_merge_crop_segments(self) -> None:
        frames = [
            CropFrame(frame_number=0, timestamp=0.0, x=100, y=100, width=500, height=900),
            CropFrame(frame_number=1, timestamp=0.5, x=101, y=101, width=501, height=901),
            CropFrame(frame_number=2, timestamp=1.0, x=300, y=200, width=700, height=1200),
        ]

        segments = merge_crop_segments(frames, merge_threshold=5.0)

        assert len(segments) == 2


class TestSafeCropGenerator:
    def test_generates_crop_plan_from_camera_path(self, settings: Settings) -> None:
        camera_path = CameraPath(
            source_width=1920,
            source_height=1080,
            target_aspect=1080 / 1920,
            frames=[
                VirtualCameraFrame(
                    frame_number=0,
                    timestamp=0.0,
                    center_x=960.0,
                    center_y=540.0,
                    zoom=600.0,
                    crop_height=1066.0,
                )
            ],
        )
        tracking = TrackingResult(
            frames=[_frame(0, [_tracked_face("person_1", 860, 420)])],
            tracks={},
        )

        crop_plan = SafeCropGenerator(settings).generate(camera_path, tracking)

        assert crop_plan.frame_count == 1
        assert crop_plan.segments
        assert crop_plan.frames[0].width > 0
        assert crop_plan.frames[0].height > 0

    def test_camera_state_to_crop_conversion(self) -> None:
        crop = camera_state_to_crop(
            frame_number=0,
            timestamp=0.0,
            center_x=500.0,
            center_y=400.0,
            crop_width=200.0,
            crop_height=355.0,
        )

        assert crop.center_x == 500.0
        assert crop.center_y == 400.0


class TestCropFactoryAndService:
    def test_factory_returns_safe_generator(self, settings: Settings) -> None:
        assert get_crop_generator(settings).generator_name == "safe"

    def test_unknown_generator_raises(self) -> None:
        with pytest.raises(UnknownCropGeneratorError):
            get_crop_generator(Settings(crop_generator="unknown"))

    def test_service_wrapper(self, settings: Settings) -> None:
        camera_path = CameraPath(
            source_width=1920,
            source_height=1080,
            target_aspect=1080 / 1920,
            frames=[
                VirtualCameraFrame(
                    frame_number=0,
                    timestamp=0.0,
                    center_x=960.0,
                    center_y=540.0,
                    zoom=700.0,
                    crop_height=900.0,
                )
            ],
        )
        tracking = TrackingResult(frames=[_frame(0, [])], tracks={})
        service = SafeCropService(settings=settings)

        result = service.generate(camera_path, tracking)

        assert result.frame_count == 1
        assert generate_crop_plan(camera_path, tracking, settings=settings).frame_count == 1
