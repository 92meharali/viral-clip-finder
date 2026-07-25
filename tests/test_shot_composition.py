"""Tests for shot composition."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.exceptions import UnknownCompositionPlannerError
from app.reframe.composition.factory import get_composition_planner
from app.reframe.composition.framing import compute_framing_target, union_bounding_boxes
from app.reframe.composition.heuristics import HeuristicCompositionPlanner
from app.reframe.composition.service import CompositionService, plan_composition
from app.reframe.models.faces import BoundingBox
from app.reframe.models.importance import FrameImportance, ImportanceFactor, ImportanceScore, ImportanceScoringResult
from app.reframe.models.composition import ShotType
from app.reframe.models.speakers import FrameSpeakerConfidence, SpeakerEstimationResult
from app.reframe.models.tracking import FrameTracks, TrackedFace, TrackingResult


def _tracked_face(track_id: str, x: float, y: float, *, width: float = 120, height: float = 150) -> TrackedFace:
    return TrackedFace(
        track_id=track_id,
        bounding_box=BoundingBox(x=x, y=y, width=width, height=height),
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


def _importance(frame_number: int, scores: list[tuple[str, float, str]]) -> FrameImportance:
    return FrameImportance(
        frame_number=frame_number,
        timestamp=float(frame_number),
        scores=[
            ImportanceScore(
                track_id=track_id,
                score=score,
                reasoning=reasoning,
                factors=[ImportanceFactor(factor_type="test", score=score)],
            )
            for track_id, score, reasoning in scores
        ],
    )


@pytest.fixture
def settings() -> Settings:
    return Settings(
        composition_planner="heuristic",
        composition_vote_reveal_face_threshold=4,
        composition_group_face_threshold=3,
        composition_conversation_importance_gap=0.15,
        composition_secondary_importance_min=0.45,
        vertical_width=1080,
        vertical_height=1920,
    )


class TestFraming:
    def test_union_bounding_boxes(self) -> None:
        boxes = [
            BoundingBox(x=100, y=100, width=50, height=50),
            BoundingBox(x=300, y=200, width=80, height=100),
        ]
        union = union_bounding_boxes(boxes)
        assert union is not None
        assert union.x == 100
        assert union.y == 100
        assert union.width == 280

    def test_compute_framing_target_includes_both_faces(self) -> None:
        faces = [
            _tracked_face("left", 300, 200),
            _tracked_face("right", 1200, 220),
        ]
        target = compute_framing_target(
            faces,
            ["left", "right"],
            image_width=1920,
            image_height=1080,
            target_aspect=1080 / 1920,
            min_padding=40,
            forehead_padding_ratio=0.35,
            rule_of_thirds_offset=0.08,
            zoom_multiplier=1.25,
        )

        union = union_bounding_boxes([face.bounding_box for face in faces])
        assert union is not None
        assert target.crop_width >= union.width
        assert target.crop_height >= union.height


class TestHeuristicCompositionPlanner:
    def test_single_speaker_for_dominant_face(self, settings: Settings) -> None:
        tracking = TrackingResult(
            frames=[_frame(0, [_tracked_face("speaker", 900, 200)])],
            tracks={},
        )
        importance = ImportanceScoringResult(
            frames=[_importance(0, [("speaker", 0.9, "currently speaking")])]
        )

        result = HeuristicCompositionPlanner(settings).plan(tracking, importance)

        assert result.frames[0].shot_type == ShotType.SINGLE_SPEAKER
        assert result.frames[0].target_track_ids == ["speaker"]

    def test_conversation_for_balanced_two_shot(self, settings: Settings) -> None:
        tracking = TrackingResult(
            frames=[
                _frame(
                    0,
                    [_tracked_face("person_1", 300, 200), _tracked_face("person_2", 1200, 200)],
                )
            ],
            tracks={},
        )
        importance = ImportanceScoringResult(
            frames=[
                _importance(
                    0,
                    [
                        ("person_1", 0.72, "currently speaking"),
                        ("person_2", 0.68, "recent speaker"),
                    ],
                )
            ]
        )

        result = HeuristicCompositionPlanner(settings).plan(tracking, importance)

        assert result.frames[0].shot_type == ShotType.CONVERSATION
        assert set(result.frames[0].target_track_ids) == {"person_1", "person_2"}

    def test_vote_reveal_for_many_faces(self, settings: Settings) -> None:
        faces = [_tracked_face(f"p{i}", 200 + i * 200, 200) for i in range(4)]
        tracking = TrackingResult(frames=[_frame(0, faces)], tracks={})
        importance = ImportanceScoringResult(
            frames=[
                _importance(
                    0,
                    [(face.track_id, 0.5, "visible participant") for face in faces],
                )
            ]
        )

        result = HeuristicCompositionPlanner(settings).plan(tracking, importance)

        assert result.frames[0].shot_type == ShotType.VOTE_REVEAL
        assert len(result.frames[0].target_track_ids) == 4

    def test_silent_reaction_prioritizes_reaction_focus(self, settings: Settings) -> None:
        tracking = TrackingResult(
            frames=[
                _frame(
                    0,
                    [_tracked_face("speaker", 300, 200), _tracked_face("reactor", 900, 200)],
                )
            ],
            tracks={},
        )
        importance = ImportanceScoringResult(
            frames=[
                _importance(
                    0,
                    [
                        ("speaker", 0.7, "currently speaking"),
                        ("reactor", 0.75, "reaction focus"),
                    ],
                )
            ]
        )
        speaker_result = SpeakerEstimationResult(
            frames=[
                FrameSpeakerConfidence(
                    frame_number=0,
                    timestamp=0.0,
                    active_track_id="speaker",
                    track_scores={"speaker": 0.8, "reactor": 0.2},
                )
            ],
            segments=[],
        )

        result = HeuristicCompositionPlanner(settings).plan(
            tracking,
            importance,
            speaker_result=speaker_result,
        )

        assert result.frames[0].shot_type == ShotType.SILENT_REACTION
        assert result.frames[0].target_track_ids == ["reactor"]


class TestCompositionFactoryAndService:
    def test_factory_returns_heuristic_planner(self, settings: Settings) -> None:
        assert get_composition_planner(settings).planner_name == "heuristic"

    def test_unknown_planner_raises(self) -> None:
        with pytest.raises(UnknownCompositionPlannerError):
            get_composition_planner(Settings(composition_planner="unknown"))

    def test_service_plan_wrapper(self, settings: Settings) -> None:
        tracking = TrackingResult(
            frames=[_frame(0, [_tracked_face("person_1", 900, 200)])],
            tracks={},
        )
        importance = ImportanceScoringResult(
            frames=[_importance(0, [("person_1", 0.9, "currently speaking")])]
        )
        service = CompositionService(settings=settings)

        result = service.plan(tracking, importance)

        assert result.frames[0].shot_type == ShotType.SINGLE_SPEAKER
        assert plan_composition(tracking, importance, settings=settings).frames[0].shot_type == ShotType.SINGLE_SPEAKER
