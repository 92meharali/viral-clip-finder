"""Future vision modules for the reframing pipeline.

These interfaces define extension points for emotion recognition, gaze estimation,
hand gesture detection, object detection, and micro-expression analysis.
Implementations will plug into importance scoring without architectural changes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.reframe.models.faces import FrameFaces


@dataclass(frozen=True)
class VisionSignal:
    """A scored visual signal from a future vision module."""

    frame_number: int
    timestamp: float
    track_id: str | None
    signal_type: str
    score: float
    label: str
    details: str = ""


class VisionModule(ABC):
    """Base class for future reframing vision modules."""

    @property
    @abstractmethod
    def module_name(self) -> str:
        """Return the module identifier."""

    @abstractmethod
    def analyze(self, frame_faces: FrameFaces) -> list[VisionSignal]:
        """Produce vision signals from detected faces in a frame."""


class EmotionRecognizer(VisionModule):
    """Detect emotional intensity from facial expressions."""

    @property
    def module_name(self) -> str:
        return "emotion_recognition"

    @abstractmethod
    def analyze(self, frame_faces: FrameFaces) -> list[VisionSignal]:
        """Return emotion-based signals."""


class GazeEstimator(VisionModule):
    """Estimate where each face is looking."""

    @property
    def module_name(self) -> str:
        return "gaze_estimation"

    @abstractmethod
    def analyze(self, frame_faces: FrameFaces) -> list[VisionSignal]:
        """Return gaze-based attention signals."""


class HandGestureDetector(VisionModule):
    """Detect hand gestures such as votes or reactions."""

    @property
    def module_name(self) -> str:
        return "hand_gesture_detection"

    @abstractmethod
    def analyze(self, frame_faces: FrameFaces) -> list[VisionSignal]:
        """Return gesture-based signals."""


class ObjectDetector(VisionModule):
    """Detect scene objects such as cards, tables, or props."""

    @property
    def module_name(self) -> str:
        return "object_detection"

    @abstractmethod
    def analyze(self, frame_faces: FrameFaces) -> list[VisionSignal]:
        """Return object-based scene signals."""


class MicroExpressionDetector(VisionModule):
    """Detect brief involuntary facial expressions."""

    @property
    def module_name(self) -> str:
        return "micro_expression_detection"

    @abstractmethod
    def analyze(self, frame_faces: FrameFaces) -> list[VisionSignal]:
        """Return micro-expression signals."""
