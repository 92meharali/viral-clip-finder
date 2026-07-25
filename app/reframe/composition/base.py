"""Shot composition planner interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.reframe.models.composition import CompositionResult
from app.reframe.models.importance import ImportanceScoringResult
from app.reframe.models.scenes import SceneDetectionResult
from app.reframe.models.speakers import SpeakerEstimationResult
from app.reframe.models.tracking import TrackingResult


class CompositionPlanner(ABC):
    """Plan what should appear in the vertical frame over time."""

    @property
    @abstractmethod
    def planner_name(self) -> str:
        """Return the planner backend identifier."""

    @abstractmethod
    def plan(
        self,
        tracking: TrackingResult,
        importance: ImportanceScoringResult,
        *,
        speaker_result: SpeakerEstimationResult | None = None,
        scene_result: SceneDetectionResult | None = None,
    ) -> CompositionResult:
        """Return per-frame shot composition decisions."""
