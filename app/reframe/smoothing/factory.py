"""Temporal smoothing factory."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.core.exceptions import UnknownTemporalSmootherError
from app.reframe.smoothing.base import TemporalSmoother
from app.reframe.smoothing.ema import EmaTemporalSmoother

SUPPORTED_TEMPORAL_SMOOTHERS = frozenset({"ema"})


def get_temporal_smoother(settings: Settings | None = None) -> TemporalSmoother:
    """Return the configured temporal smoother backend."""
    resolved = settings or get_settings()
    smoother_name = resolved.temporal_smoother.strip().lower()

    if smoother_name not in SUPPORTED_TEMPORAL_SMOOTHERS:
        supported = ", ".join(sorted(SUPPORTED_TEMPORAL_SMOOTHERS))
        raise UnknownTemporalSmootherError(
            f"Unsupported temporal smoother '{resolved.temporal_smoother}'. Supported: {supported}"
        )

    if smoother_name == "ema":
        return EmaTemporalSmoother(resolved)

    raise UnknownTemporalSmootherError(
        f"No implementation for temporal smoother '{smoother_name}'"
    )
