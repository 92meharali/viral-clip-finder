"""Shot composition planner factory."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.core.exceptions import UnknownCompositionPlannerError
from app.reframe.composition.base import CompositionPlanner
from app.reframe.composition.heuristics import HeuristicCompositionPlanner

SUPPORTED_COMPOSITION_PLANNERS = frozenset({"heuristic"})


def get_composition_planner(settings: Settings | None = None) -> CompositionPlanner:
    """Return the configured shot composition planner backend."""
    resolved = settings or get_settings()
    planner_name = resolved.composition_planner.strip().lower()

    if planner_name not in SUPPORTED_COMPOSITION_PLANNERS:
        supported = ", ".join(sorted(SUPPORTED_COMPOSITION_PLANNERS))
        raise UnknownCompositionPlannerError(
            f"Unsupported composition planner '{resolved.composition_planner}'. Supported: {supported}"
        )

    if planner_name == "heuristic":
        return HeuristicCompositionPlanner(resolved)

    raise UnknownCompositionPlannerError(
        f"No implementation for composition planner '{planner_name}'"
    )
