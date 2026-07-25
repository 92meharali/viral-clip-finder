"""Reframe pipeline data models."""

from app.reframe.models.camera import CameraPath, VirtualCameraFrame
from app.reframe.models.composition import (
    CompositionResult,
    FrameComposition,
    FramingTarget,
    ShotType,
)
from app.reframe.models.crop import CropFrame, CropPlan, CropSegment
from app.reframe.models.faces import BoundingBox, DetectedFace, FaceLandmarks, FrameFaces, VideoFrame
from app.reframe.models.importance import (
    FrameImportance,
    ImportanceFactor,
    ImportanceScore,
    ImportanceScoringResult,
)
from app.reframe.models.render import ReframeRenderResult
from app.reframe.models.scenes import (
    SceneBoundary,
    SceneBoundaryType,
    SceneDetectionResult,
    SceneSegment,
)
from app.reframe.models.speakers import (
    ActiveSpeaker,
    FrameSpeakerConfidence,
    SignalContribution,
    SpeakerEstimationResult,
)
from app.reframe.models.tracking import FrameTracks, TrackedFace, TrackingResult, TrackSummary

__all__ = [
    "ActiveSpeaker",
    "BoundingBox",
    "CameraPath",
    "CompositionResult",
    "CropFrame",
    "CropPlan",
    "CropSegment",
    "DetectedFace",
    "FaceLandmarks",
    "FrameComposition",
    "FrameFaces",
    "FrameImportance",
    "FrameSpeakerConfidence",
    "FrameTracks",
    "FramingTarget",
    "ImportanceFactor",
    "ImportanceScore",
    "ImportanceScoringResult",
    "ReframeRenderResult",
    "SceneBoundary",
    "SceneBoundaryType",
    "SceneDetectionResult",
    "SceneSegment",
    "ShotType",
    "SignalContribution",
    "SpeakerEstimationResult",
    "TrackedFace",
    "TrackingResult",
    "TrackSummary",
    "VideoFrame",
    "VirtualCameraFrame",
]
