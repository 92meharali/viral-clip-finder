"""FFmpeg scene-change detection backend."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from loguru import logger

from app.core.config import Settings, get_settings
from app.core.exceptions import SceneDetectionError
from app.reframe.models.scenes import SceneBoundary, SceneBoundaryType, SceneDetectionResult
from app.reframe.scenes.base import SceneDetector
from app.reframe.scenes.segments import build_scene_segments, merge_close_boundaries
from app.video.ffmpeg import probe_duration, validate_source_video

_PTS_TIME_PATTERN = re.compile(r"pts_time:([0-9.]+)")
_SCENE_SCORE_PATTERN = re.compile(r"scene:([0-9.]+)")


class FFmpegSceneDetector(SceneDetector):
    """Detect hard cuts using FFmpeg's built-in scene change score."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def detector_name(self) -> str:
        return "ffmpeg"

    def detect(self, video_path: str | Path) -> SceneDetectionResult:
        source = Path(video_path).resolve()
        validate_source_video(source)

        ffmpeg = self.settings.ffmpeg_path
        if shutil.which(ffmpeg) is None:
            raise SceneDetectionError(f"ffmpeg not found at '{ffmpeg}'")

        duration = probe_duration(source, self.settings)
        threshold = self.settings.scene_detection_threshold
        filter_expr = f"select='gt(scene,{threshold})',showinfo"

        cmd = [
            ffmpeg,
            "-hide_banner",
            "-i",
            str(source),
            "-filter:v",
            filter_expr,
            "-f",
            "null",
            "-",
        ]

        logger.info(
            "Detecting scene boundaries in {} with ffmpeg threshold {}",
            source.name,
            threshold,
        )

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=600,
            )
        except subprocess.TimeoutExpired as exc:
            raise SceneDetectionError("ffmpeg scene detection timed out") from exc

        if result.returncode not in {0, 255}:
            raise SceneDetectionError(
                f"ffmpeg scene detection failed: {result.stderr.strip()}"
            )

        boundaries = self._parse_showinfo(result.stderr, threshold=threshold)
        boundaries = merge_close_boundaries(
            boundaries,
            min_gap_seconds=self.settings.scene_min_gap_seconds,
        )
        segments = build_scene_segments(boundaries, duration)

        logger.info(
            "Detected {} scene boundaries → {} segments in {}",
            len(boundaries),
            len(segments),
            source.name,
        )

        return SceneDetectionResult(
            source_path=str(source),
            duration_seconds=duration,
            boundaries=boundaries,
            segments=segments,
        )

    def _parse_showinfo(self, stderr: str, *, threshold: float) -> list[SceneBoundary]:
        boundaries: list[SceneBoundary] = []
        for line in stderr.splitlines():
            if "pts_time:" not in line:
                continue
            timestamp_match = _PTS_TIME_PATTERN.search(line)
            if not timestamp_match:
                continue

            timestamp = float(timestamp_match.group(1))
            score_match = _SCENE_SCORE_PATTERN.search(line)
            confidence = float(score_match.group(1)) if score_match else threshold
            confidence = min(max(confidence, 0.0), 1.0)

            boundaries.append(
                SceneBoundary(
                    timestamp=timestamp,
                    confidence=confidence,
                    boundary_type=SceneBoundaryType.CUT,
                )
            )

        return sorted(boundaries, key=lambda item: item.timestamp)
