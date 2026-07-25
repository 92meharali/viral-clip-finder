"""Tests for importance scoring."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.exceptions import UnknownImportanceScorerError
from app.reframe.importance.factory import get_importance_scorer
from app.reframe.importance.fusion import FusionImportanceScorer
from app.reframe.importance.factors.center import FrameCenterFactor
from app.reframe.importance.factors.presence import ScreenPresenceFactor
from app.reframe.importance.factors.reaction import ReactionTargetFactor
from app.reframe.importance.factors.recent_speaker import RecentSpeakerFactor
from app.reframe.importance.factors.speaking import CurrentlySpeakingFactor
from app.reframe.importance.service import ImportanceScoringService, score_importance
from app.reframe.models.faces import BoundingBox, FaceLandmarks
from app.reframe.models.speakers import (
    ActiveSpeaker,
    FrameSpeakerConfidence,
    SpeakerEstimationResult,
)
from app.reframe.models.tracking import FrameTracks, TrackedFace, TrackingResult


def _tracked_face(
    track_id: str,
    x: float,
    y: float,
    *,
    width: float = 120,
    height: float = 150,
    mouth: tuple[float, float] | None = None,
    confidence: float = 0.95,
) -> TrackedFace:
    landmarks = FaceLandmarks(mouth=mouth) if mouth else None
    return TrackedFace(
        track_id=track_id,
        bounding_box=BoundingBox(x=x, y=y, width=width, height=height),
        detection_confidence=confidence,
        landmarks=landmarks,
    )


def _frame(
    frame_number: int,
    faces: list[TrackedFace],
    *,
    timestamp: float | None = None,
) -> FrameTracks:
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
        importance_scorer="fusion",
        importance_weight_speaking=0.40,
        importance_weight_expression=0.15,
        importance_weight_detection=0.05,
        importance_weight_center=0.10,
        importance_weight_presence=0.15,
        importance_weight_recent_speaker=0.10,
        importance_weight_reaction=0.05,
        importance_recent_speaker_decay_seconds=2.0,
    )


class TestScreenPresenceFactor:
    def test_larger_face_scores_higher(self) -> None:
        tracking = TrackingResult(
            frames=[
                _frame(
                    0,
                    [
                        _tracked_face("small", 300, 200, width=80, height=100),
                        _tracked_face("large", 900, 200, width=200, height=240),
                    ],
                )
            ],
            tracks={},
        )

        scores = ScreenPresenceFactor().score_frames(tracking)

        assert scores[0]["large"] == 1.0
        assert scores[0]["small"] < scores[0]["large"]


class TestFrameCenterFactor:
    def test_center_face_scores_higher(self) -> None:
        tracking = TrackingResult(
            frames=[
                _frame(
                    0,
                    [
                        _tracked_face("edge", 100, 200),
                        _tracked_face("center", 900, 200),
                    ],
                )
            ],
            tracks={},
        )

        scores = FrameCenterFactor().score_frames(tracking)

        assert scores[0]["center"] > scores[0]["edge"]


class TestCurrentlySpeakingFactor:
    def test_active_speaker_receives_max_score(self) -> None:
        tracking = TrackingResult(
            frames=[_frame(0, [_tracked_face("person_1", 400, 200), _tracked_face("person_2", 900, 200)])],
            tracks={},
        )
        speaker_result = SpeakerEstimationResult(
            frames=[
                FrameSpeakerConfidence(
                    frame_number=0,
                    timestamp=0.0,
                    active_track_id="person_1",
                    track_scores={"person_1": 0.82, "person_2": 0.25},
                )
            ],
            segments=[],
        )

        scores = CurrentlySpeakingFactor().score_frames(tracking, speaker_result=speaker_result)

        assert scores[0]["person_1"] == 1.0
        assert scores[0]["person_2"] == 0.25


class TestRecentSpeakerFactor:
    def test_recent_speaker_decays_over_time(self, settings: Settings) -> None:
        tracking = TrackingResult(
            frames=[
                _frame(0, [_tracked_face("person_1", 400, 200)], timestamp=0.0),
                _frame(1, [_tracked_face("person_1", 400, 200)], timestamp=2.5),
            ],
            tracks={},
        )
        speaker_result = SpeakerEstimationResult(
            segments=[
                ActiveSpeaker(
                    track_id="person_1",
                    confidence=0.9,
                    start_time=0.0,
                    end_time=1.0,
                )
            ],
            frames=[],
        )

        scores = RecentSpeakerFactor(settings).score_frames(tracking, speaker_result=speaker_result)

        assert scores[0]["person_1"] == 1.0
        assert scores[1]["person_1"] < scores[0]["person_1"]


class TestReactionTargetFactor:
    def test_central_listener_scores_when_others_are_expressive(self) -> None:
        tracking = TrackingResult(
            frames=[
                _frame(
                    0,
                    [
                        _tracked_face("listener", 860, 200, width=180, height=220, mouth=(950.0, 320.0)),
                        _tracked_face("speaker", 300, 200, mouth=(360.0, 290.0)),
                    ],
                    timestamp=0.0,
                ),
                _frame(
                    1,
                    [
                        _tracked_face("listener", 860, 200, width=180, height=220, mouth=(950.0, 321.0)),
                        _tracked_face("speaker", 300, 200, mouth=(360.0, 310.0)),
                    ],
                    timestamp=0.5,
                ),
            ],
            tracks={},
        )

        scores = ReactionTargetFactor().score_frames(tracking)

        assert scores[1]["listener"] > 0.0
        assert scores[1]["speaker"] == 0.0


class TestFusionImportanceScorer:
    def test_speaker_outranks_listener(self, settings: Settings) -> None:
        tracking = TrackingResult(
            frames=[
                _frame(
                    1,
                    [
                        _tracked_face("speaker", 300, 200, mouth=(360.0, 308.0)),
                        _tracked_face("listener", 900, 200, mouth=(960.0, 291.0)),
                    ],
                    timestamp=1.0,
                ),
            ],
            tracks={},
        )
        speaker_result = SpeakerEstimationResult(
            frames=[
                FrameSpeakerConfidence(
                    frame_number=1,
                    timestamp=1.0,
                    active_track_id="speaker",
                    track_scores={"speaker": 0.9, "listener": 0.2},
                )
            ],
            segments=[
                ActiveSpeaker(
                    track_id="speaker",
                    confidence=0.9,
                    start_time=1.0,
                    end_time=2.0,
                )
            ],
        )

        result = FusionImportanceScorer(settings).score(
            tracking,
            speaker_result=speaker_result,
        )

        assert result.frames[0].top_track_id == "speaker"
        assert result.frames[0].scores[0].score > result.frames[0].scores[1].score
        assert "currently speaking" in result.frames[0].scores[0].reasoning

    def test_large_center_face_scores_without_speaker_result(self, settings: Settings) -> None:
        tracking = TrackingResult(
            frames=[
                _frame(
                    0,
                    [
                        _tracked_face("edge", 100, 200, width=80, height=100),
                        _tracked_face("center", 900, 200, width=220, height=260),
                    ],
                )
            ],
            tracks={},
        )

        result = FusionImportanceScorer(settings).score(tracking)

        assert result.frames[0].top_track_id == "center"


class TestImportanceFactoryAndService:
    def test_factory_returns_fusion_scorer(self, settings: Settings) -> None:
        scorer = get_importance_scorer(settings)
        assert scorer.scorer_name == "fusion"

    def test_unknown_scorer_raises(self) -> None:
        with pytest.raises(UnknownImportanceScorerError):
            get_importance_scorer(Settings(importance_scorer="unknown"))

    def test_service_score_wrapper(self, settings: Settings) -> None:
        tracking = TrackingResult(
            frames=[_frame(0, [_tracked_face("person_1", 900, 200, width=200, height=240)])],
            tracks={},
        )
        service = ImportanceScoringService(settings=settings)

        result = service.score(tracking)

        assert len(result.frames) == 1
        assert result.frames[0].scores[0].track_id == "person_1"
        assert score_importance(tracking, settings=settings).frames[0].top_track_id == "person_1"
