"""Tests for virtual camera planning."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.exceptions import UnknownCameraPlannerError
from app.reframe.camera.factory import get_camera_planner
from app.reframe.camera.pursuit import PursuitCameraPlanner
from app.reframe.camera.service import VirtualCameraService, plan_camera_path
from app.reframe.models.composition import CompositionResult, FrameComposition, FramingTarget, ShotType
from app.reframe.models.scenes import SceneBoundary, SceneBoundaryType, SceneDetectionResult, SceneSegment


def _composition_frame(
    frame_number: int,
    *,
    center_x: float,
    center_y: float,
    crop_width: float = 900.0,
    crop_height: float = 1600.0,
    timestamp: float | None = None,
) -> FrameComposition:
    return FrameComposition(
        frame_number=frame_number,
        timestamp=timestamp if timestamp is not None else float(frame_number),
        shot_type=ShotType.SINGLE_SPEAKER,
        target_track_ids=["person_1"],
        framing=FramingTarget(
            center_x=center_x,
            center_y=center_y,
            crop_width=crop_width,
            crop_height=crop_height,
        ),
        reasoning="test framing",
    )


@pytest.fixture
def settings() -> Settings:
    return Settings(
        camera_planner="pursuit",
        camera_max_pan_speed=200.0,
        camera_max_zoom_speed=150.0,
        camera_smoothing=0.5,
        camera_scene_reset=True,
        camera_scene_boundary_tolerance=0.1,
    )


class TestPursuitCameraPlanner:
    def test_first_frame_matches_target(self, settings: Settings) -> None:
        composition = CompositionResult(
            source_width=1920,
            source_height=1080,
            target_aspect=1080 / 1920,
            frames=[_composition_frame(0, center_x=500.0, center_y=400.0)],
        )

        path = PursuitCameraPlanner(settings).plan(composition)

        assert path.frames[0].center_x == 500.0
        assert path.frames[0].center_y == 400.0
        assert path.frames[0].velocity_x == 0.0

    def test_camera_moves_toward_target_without_instant_jump(self, settings: Settings) -> None:
        composition = CompositionResult(
            source_width=1920,
            source_height=1080,
            target_aspect=1080 / 1920,
            frames=[
                _composition_frame(0, center_x=500.0, center_y=400.0, timestamp=0.0),
                _composition_frame(1, center_x=1400.0, center_y=400.0, timestamp=1.0),
            ],
        )

        path = PursuitCameraPlanner(settings).plan(composition)

        assert path.frames[1].center_x > path.frames[0].center_x
        assert path.frames[1].center_x < 1400.0
        assert path.frames[1].velocity_x != 0.0

    def test_scene_boundary_resets_camera(self, settings: Settings) -> None:
        composition = CompositionResult(
            source_width=1920,
            source_height=1080,
            target_aspect=1080 / 1920,
            frames=[
                _composition_frame(0, center_x=500.0, center_y=400.0, timestamp=0.0),
                _composition_frame(1, center_x=1400.0, center_y=650.0, timestamp=1.0),
            ],
        )
        scene_result = SceneDetectionResult(
            source_path="clip.mp4",
            duration_seconds=5.0,
            boundaries=[
                SceneBoundary(
                    timestamp=1.0,
                    confidence=0.9,
                    boundary_type=SceneBoundaryType.CUT,
                )
            ],
            segments=[
                SceneSegment(index=0, start_seconds=0.0, end_seconds=1.0, duration_seconds=1.0),
                SceneSegment(index=1, start_seconds=1.0, end_seconds=5.0, duration_seconds=4.0),
            ],
        )

        path = PursuitCameraPlanner(settings).plan(composition, scene_result=scene_result)

        assert path.frames[1].center_x == 1400.0
        assert path.frames[1].center_y == 650.0
        assert path.frames[1].velocity_x == 0.0


class TestCameraFactoryAndService:
    def test_factory_returns_pursuit_planner(self, settings: Settings) -> None:
        assert get_camera_planner(settings).planner_name == "pursuit"

    def test_unknown_planner_raises(self) -> None:
        with pytest.raises(UnknownCameraPlannerError):
            get_camera_planner(Settings(camera_planner="unknown"))

    def test_service_plan_wrapper(self, settings: Settings) -> None:
        composition = CompositionResult(
            source_width=1920,
            source_height=1080,
            target_aspect=1080 / 1920,
            frames=[_composition_frame(0, center_x=700.0, center_y=500.0)],
        )
        service = VirtualCameraService(settings=settings)

        result = service.plan(composition)

        assert result.frame_count == 1
        assert plan_camera_path(composition, settings=settings).frames[0].center_x == 700.0
