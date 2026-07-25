"""Active speaker estimator factory."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.core.exceptions import UnknownSpeakerEstimatorError
from app.reframe.speakers.base import ActiveSpeakerEstimator
from app.reframe.speakers.fusion import FusionActiveSpeakerEstimator

SUPPORTED_SPEAKER_ESTIMATORS = frozenset({"fusion"})


def get_speaker_estimator(settings: Settings | None = None) -> ActiveSpeakerEstimator:
    """Return the configured active speaker estimator backend."""
    resolved = settings or get_settings()
    estimator_name = resolved.speaker_estimator.strip().lower()

    if estimator_name not in SUPPORTED_SPEAKER_ESTIMATORS:
        supported = ", ".join(sorted(SUPPORTED_SPEAKER_ESTIMATORS))
        raise UnknownSpeakerEstimatorError(
            f"Unsupported speaker estimator '{resolved.speaker_estimator}'. Supported: {supported}"
        )

    if estimator_name == "fusion":
        return FusionActiveSpeakerEstimator(resolved)

    raise UnknownSpeakerEstimatorError(f"No implementation for speaker estimator '{estimator_name}'")
