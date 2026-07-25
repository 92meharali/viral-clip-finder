"""Extract still frames from video files."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from loguru import logger

from app.core.config import Settings, get_settings
from app.core.exceptions import FrameExtractionError
from app.reframe.models.faces import VideoFrame
from app.video.ffmpeg import probe_dimensions, validate_source_video

_FRAME_PATTERN = re.compile(r"frame_(\d+)\.jpg$")


class FrameExtractor:
    """Extract still frames from a video at a configurable sample rate."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the frame extractor."""
        self.settings = settings or get_settings()

    def extract(
        self,
        video_path: str | Path,
        output_dir: str | Path,
        *,
        fps: float | None = None,
    ) -> list[VideoFrame]:
        """Extract JPEG frames from a video file.

        Args:
            video_path: Source video path.
            output_dir: Directory for extracted JPEG frames.
            fps: Frames per second to sample. Defaults to ``settings.face_extraction_fps``.

        Returns:
            Extracted frames with timestamps and dimensions.

        Raises:
            FrameExtractionError: If extraction fails.
        """
        source = Path(video_path).resolve()
        validate_source_video(source)

        sample_fps = fps if fps is not None else self.settings.face_extraction_fps
        if sample_fps <= 0:
            raise FrameExtractionError("Frame extraction fps must be greater than zero")

        width, height = probe_dimensions(source, self.settings)
        frames_dir = Path(output_dir).resolve()
        frames_dir.mkdir(parents=True, exist_ok=True)

        pattern = frames_dir / "frame_%06d.jpg"
        ffmpeg = self.settings.ffmpeg_path
        if shutil.which(ffmpeg) is None:
            raise FrameExtractionError(f"ffmpeg not found at '{ffmpeg}'")

        cmd = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-vf",
            f"fps={sample_fps}",
            str(pattern),
        ]

        logger.info("Extracting frames from {} at {:.2f} fps", source.name, sample_fps)

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=600)
        except subprocess.CalledProcessError as exc:
            logger.error("Frame extraction failed: {}", exc.stderr)
            raise FrameExtractionError(f"ffmpeg frame extraction failed: {exc.stderr}") from exc
        except subprocess.TimeoutExpired as exc:
            raise FrameExtractionError("ffmpeg frame extraction timed out") from exc

        frame_paths = sorted(frames_dir.glob("frame_*.jpg"))
        if not frame_paths:
            raise FrameExtractionError(f"No frames extracted from {source}")

        frames: list[VideoFrame] = []
        for path in frame_paths:
            match = _FRAME_PATTERN.search(path.name)
            if not match:
                continue
            frame_number = int(match.group(1)) - 1
            timestamp = frame_number / sample_fps
            frames.append(
                VideoFrame(
                    frame_number=frame_number,
                    timestamp=timestamp,
                    image_path=str(path.resolve()),
                    width=width,
                    height=height,
                )
            )

        logger.info("Extracted {} frames from {}", len(frames), source.name)
        return frames
