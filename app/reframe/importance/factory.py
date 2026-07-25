"""Importance scorer factory."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.core.exceptions import UnknownImportanceScorerError
from app.reframe.importance.base import ImportanceScorer
from app.reframe.importance.fusion import FusionImportanceScorer

SUPPORTED_IMPORTANCE_SCORERS = frozenset({"fusion"})


def get_importance_scorer(settings: Settings | None = None) -> ImportanceScorer:
    """Return the configured importance scorer backend."""
    resolved = settings or get_settings()
    scorer_name = resolved.importance_scorer.strip().lower()

    if scorer_name not in SUPPORTED_IMPORTANCE_SCORERS:
        supported = ", ".join(sorted(SUPPORTED_IMPORTANCE_SCORERS))
        raise UnknownImportanceScorerError(
            f"Unsupported importance scorer '{resolved.importance_scorer}'. Supported: {supported}"
        )

    if scorer_name == "fusion":
        return FusionImportanceScorer(resolved)

    raise UnknownImportanceScorerError(
        f"No implementation for importance scorer '{scorer_name}'"
    )
