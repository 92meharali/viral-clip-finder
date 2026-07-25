"""Reframe renderer interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.reframe.models.crop import CropPlan
from app.reframe.models.render import ReframeRenderResult


class ReframeRenderer(ABC):
    """Render a vertical video from a crop plan."""

    @property
    @abstractmethod
    def renderer_name(self) -> str:
        """Return the renderer backend identifier."""

    @abstractmethod
    def render(
        self,
        source_path: str | Path,
        crop_plan: CropPlan,
        output_path: str | Path,
        *,
        duration_seconds: float,
        blurred_background: bool = False,
    ) -> ReframeRenderResult:
        """Execute the crop plan and write the output video."""
