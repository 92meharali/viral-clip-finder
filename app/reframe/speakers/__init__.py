"""Active speaker estimation package."""

from app.reframe.speakers.factory import SUPPORTED_SPEAKER_ESTIMATORS, get_speaker_estimator
from app.reframe.speakers.service import (
    ActiveSpeakerEstimationService,
    estimate_active_speakers,
    estimate_active_speakers_in_video,
)

__all__ = [
    "ActiveSpeakerEstimationService",
    "SUPPORTED_SPEAKER_ESTIMATORS",
    "estimate_active_speakers",
    "estimate_active_speakers_in_video",
    "get_speaker_estimator",
]
