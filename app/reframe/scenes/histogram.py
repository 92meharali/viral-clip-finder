"""Histogram-based scene detection backend."""

# mypy: disable-error-code=import-not-found

from __future__ import annotations

from pathlib import Path

from loguru import logger

from app.core.config import Settings, get_settings
from app.core.exceptions import SceneDetectionError
from app.reframe.frames.extractor import FrameExtractor
from app.reframe.models.faces import VideoFrame
from app.reframe.models.scenes import SceneBoundary, SceneBoundaryType, SceneDetectionResult
from app.reframe.scenes.base import SceneDetector
from app.reframe.scenes.segments import build_scene_segments, merge_close_boundaries
from app.video.ffmpeg import probe_duration, validate_source_video


def _normalized_histogram(image_path: str) -> list[float]:
    """Compute a normalized grayscale histogram for an image."""
    try:
        from PIL import Image
    except ImportError as exc:
        raise SceneDetectionError(
            "Pillow is required for histogram scene detection. Install with: uv sync --extra vision"
        ) from exc

    with Image.open(image_path).convert("L") as image:
        histogram = image.histogram()

    total = float(sum(histogram)) or 1.0
    return [value / total for value in histogram]


def _histogram_difference(left: list[float], right: list[float]) -> float:
    """Return a 0-1 difference score between two normalized histograms."""
    return sum(abs(a - b) for a, b in zip(left, right, strict=True)) / 2.0


class HistogramSceneDetector(SceneDetector):
    """Detect scene changes by comparing consecutive frame histograms."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        frame_extractor: FrameExtractor | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._frame_extractor = frame_extractor or FrameExtractor(self.settings)

    @property
    def detector_name(self) -> str:
        return "histogram"

    def detect(self, video_path: str | Path) -> SceneDetectionResult:
        source = Path(video_path).resolve()
        validate_source_video(source)
        duration = probe_duration(source, self.settings)

        import tempfile

        with tempfile.TemporaryDirectory(prefix="reframe_scene_frames_") as temp_dir:
            frames = self._frame_extractor.extract(
                source,
                temp_dir,
                fps=self.settings.scene_extraction_fps,
            )
            boundaries = self.detect_frames(frames)

        boundaries = merge_close_boundaries(
            boundaries,
            min_gap_seconds=self.settings.scene_min_gap_seconds,
        )
        segments = build_scene_segments(boundaries, duration)

        logger.info(
            "Histogram scene detection found {} boundaries in {}",
            len(boundaries),
            source.name,
        )

        return SceneDetectionResult(
            source_path=str(source),
            duration_seconds=duration,
            boundaries=boundaries,
            segments=segments,
        )

    def detect_frames(self, frames: list[VideoFrame]) -> list[SceneBoundary]:
        """Detect boundaries from pre-extracted frames."""
        if len(frames) < 2:
            return []

        threshold = self.settings.scene_detection_threshold
        boundaries: list[SceneBoundary] = []
        previous_hist = _normalized_histogram(frames[0].image_path)

        for frame in frames[1:]:
            current_hist = _normalized_histogram(frame.image_path)
            difference = _histogram_difference(previous_hist, current_hist)
            if difference >= threshold:
                boundaries.append(
                    SceneBoundary(
                        timestamp=frame.timestamp,
                        confidence=min(max(difference, 0.0), 1.0),
                        boundary_type=SceneBoundaryType.CUT,
                        frame_number=frame.frame_number,
                    )
                )
            previous_hist = current_hist

        return boundaries
