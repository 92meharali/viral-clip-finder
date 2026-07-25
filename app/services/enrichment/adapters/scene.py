"""Scene detection enrichment adapter."""

from __future__ import annotations

from pathlib import Path

from app.reframe.scenes.service import SceneDetectionService
from app.models.transcript import TranscriptSegment
from app.services.enrichment.base import EnrichmentSignal, SceneDetector


class ReframeSceneEnrichment(SceneDetector):
    """Bridge scene detection into candidate window generation."""

    def __init__(self, *, scene_service: SceneDetectionService | None = None) -> None:
        self._scene_service = scene_service or SceneDetectionService()

    @property
    def module_name(self) -> str:
        return "scene_detection"

    def analyze(
        self,
        segments: list[TranscriptSegment],
        *,
        video_path: str | None = None,
    ) -> list[EnrichmentSignal]:
        if video_path is None:
            return []

        result = self._scene_service.detect(Path(video_path))
        signals: list[EnrichmentSignal] = []
        for segment in result.segments:
            midpoint = (segment.start_seconds + segment.end_seconds) / 2
            window_half = min(15.0, segment.duration_seconds / 2)
            signals.append(
                EnrichmentSignal(
                    start_seconds=max(0.0, midpoint - window_half),
                    end_seconds=midpoint + window_half,
                    signal_type="scene_segment",
                    score=0.6,
                    label="scene_anchor",
                    details=f"Scene {segment.index} span",
                )
            )
        return signals
