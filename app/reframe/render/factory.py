"""Reframe renderer factory."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.core.exceptions import UnknownReframeRendererError
from app.reframe.render.base import ReframeRenderer
from app.reframe.render.ffmpeg import FFmpegReframeRenderer

SUPPORTED_REFRAME_RENDERERS = frozenset({"ffmpeg"})


def get_reframe_renderer(settings: Settings | None = None) -> ReframeRenderer:
    """Return the configured reframe renderer backend."""
    resolved = settings or get_settings()
    renderer_name = resolved.reframe_renderer.strip().lower()

    if renderer_name not in SUPPORTED_REFRAME_RENDERERS:
        supported = ", ".join(sorted(SUPPORTED_REFRAME_RENDERERS))
        raise UnknownReframeRendererError(
            f"Unsupported reframe renderer '{resolved.reframe_renderer}'. Supported: {supported}"
        )

    if renderer_name == "ffmpeg":
        return FFmpegReframeRenderer(resolved)

    raise UnknownReframeRendererError(f"No implementation for reframe renderer '{renderer_name}'")
