"""Future enrichment module interfaces."""

from app.services.enrichment.base import (
    AudioAnalyzer,
    EmotionDetector,
    EnrichmentModule,
    EnrichmentSignal,
    FaceTracker,
    FrameSampler,
    SceneDetector,
)
from app.services.enrichment.adapters import ReframeSceneEnrichment, TranscriptEnrichment

__all__ = [
    "AudioAnalyzer",
    "EmotionDetector",
    "EnrichmentModule",
    "EnrichmentSignal",
    "FaceTracker",
    "FrameSampler",
    "ReframeSceneEnrichment",
    "SceneDetector",
    "TranscriptEnrichment",
]
