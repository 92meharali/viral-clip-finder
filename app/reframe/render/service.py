"""Reframe render orchestration service."""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from app.core.config import Settings, get_settings
from app.reframe.models.crop import CropPlan
from app.reframe.models.render import ReframeRenderResult
from app.reframe.render.base import ReframeRenderer
from app.reframe.render.factory import get_reframe_renderer
from app.video.ffmpeg import probe_duration


class ReframeRenderService:
    """Execute crop plans into final vertical videos."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        renderer: ReframeRenderer | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._renderer = renderer

    @property
    def renderer(self) -> ReframeRenderer:
        if self._renderer is None:
            self._renderer = get_reframe_renderer(self.settings)
        return self._renderer

    def render(
        self,
        source_path: str | Path,
        crop_plan: CropPlan,
        output_path: str | Path,
        *,
        duration_seconds: float | None = None,
        blurred_background: bool | None = None,
    ) -> ReframeRenderResult:
        """Render a crop plan to a vertical output file."""
        source = Path(source_path).resolve()
        resolved_duration = duration_seconds
        if resolved_duration is None:
            resolved_duration = probe_duration(source, self.settings)

        use_blur = (
            blurred_background
            if blurred_background is not None
            else self.settings.reframe_blur_background
        )

        logger.info(
            "Rendering reframed video {} → {} with {}",
            source.name,
            Path(output_path).name,
            self.renderer.renderer_name,
        )
        return self.renderer.render(
            source,
            crop_plan,
            output_path,
            duration_seconds=resolved_duration,
            blurred_background=use_blur,
        )


def render_reframed_video(
    source_path: str | Path,
    crop_plan: CropPlan,
    output_path: str | Path,
    *,
    settings: Settings | None = None,
    duration_seconds: float | None = None,
    blurred_background: bool | None = None,
) -> ReframeRenderResult:
    """Convenience function to render a crop plan."""
    return ReframeRenderService(settings=settings).render(
        source_path,
        crop_plan,
        output_path,
        duration_seconds=duration_seconds,
        blurred_background=blurred_background,
    )
