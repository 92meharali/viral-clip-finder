"""Intelligent vertical reframing pipeline."""

from app.reframe.camera.service import VirtualCameraService, plan_camera_path
from app.reframe.composition.service import CompositionService, plan_composition
from app.reframe.crop.service import SafeCropService, generate_crop_plan
from app.reframe.detection.service import FaceDetectionService, detect_faces_in_video
from app.reframe.importance.service import (
    ImportanceScoringService,
    score_importance,
    score_importance_in_video,
)
from app.reframe.models.camera import CameraPath, VirtualCameraFrame
from app.reframe.models.composition import CompositionResult, FrameComposition, ShotType
from app.reframe.models.crop import CropFrame, CropPlan, CropSegment
from app.reframe.models.faces import BoundingBox, DetectedFace, FaceLandmarks, FrameFaces
from app.reframe.models.importance import (
    FrameImportance,
    ImportanceScore,
    ImportanceScoringResult,
)
from app.reframe.export.vertical import REFRAME_CROP_MODE, reframe_to_vertical
from app.reframe.metrics import ReframeEvaluationMetrics, evaluate_reframe
from app.reframe.models.render import ReframeRenderResult
from app.reframe.models.scenes import SceneBoundary, SceneDetectionResult, SceneSegment
from app.reframe.models.speakers import ActiveSpeaker, FrameSpeakerConfidence, SpeakerEstimationResult
from app.reframe.models.tracking import FrameTracks, TrackedFace, TrackingResult, TrackSummary
from app.reframe.pipeline.service import ReframePipelineResult, ReframePipelineService
from app.reframe.render.service import ReframeRenderService, render_reframed_video
from app.reframe.scenes.service import SceneDetectionService, detect_scenes
from app.reframe.smoothing.service import TemporalSmoothingService, smooth_camera_path
from app.reframe.speakers.service import (
    ActiveSpeakerEstimationService,
    estimate_active_speakers,
    estimate_active_speakers_in_video,
)
from app.reframe.tracking.service import (
    FaceTrackingService,
    track_faces_in_frames,
    track_faces_in_video,
)

__all__ = [
    "ActiveSpeaker",
    "ActiveSpeakerEstimationService",
    "BoundingBox",
    "CameraPath",
    "CompositionResult",
    "CompositionService",
    "CropFrame",
    "CropPlan",
    "CropSegment",
    "DetectedFace",
    "FaceDetectionService",
    "FaceLandmarks",
    "FaceTrackingService",
    "FrameComposition",
    "FrameFaces",
    "FrameImportance",
    "FrameSpeakerConfidence",
    "FrameTracks",
    "ImportanceScore",
    "ImportanceScoringResult",
    "ImportanceScoringService",
    "ReframeEvaluationMetrics",
    "ReframePipelineResult",
    "ReframePipelineService",
    "ReframeRenderResult",
    "ReframeRenderService",
    "REFRAME_CROP_MODE",
    "SafeCropService",
    "SceneBoundary",
    "SceneDetectionResult",
    "SceneDetectionService",
    "SceneSegment",
    "ShotType",
    "SpeakerEstimationResult",
    "TemporalSmoothingService",
    "TrackedFace",
    "TrackingResult",
    "TrackSummary",
    "VirtualCameraFrame",
    "VirtualCameraService",
    "detect_faces_in_video",
    "detect_scenes",
    "estimate_active_speakers",
    "estimate_active_speakers_in_video",
    "generate_crop_plan",
    "plan_camera_path",
    "plan_composition",
    "render_reframed_video",
    "reframe_to_vertical",
    "evaluate_reframe",
    "score_importance",
    "score_importance_in_video",
    "smooth_camera_path",
    "track_faces_in_frames",
    "track_faces_in_video",
]
