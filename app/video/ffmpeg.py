"""Low-level FFmpeg and FFprobe utilities."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from loguru import logger

from app.core.config import Settings, get_settings
from app.core.exceptions import VideoCutError

SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv"}


def ensure_ffmpeg_available(settings: Settings | None = None) -> None:
    """Verify that ffmpeg is available on the system PATH.

    Args:
        settings: Optional settings override.

    Raises:
        VideoCutError: If ffmpeg cannot be found.
    """
    resolved = settings or get_settings()
    if shutil.which(resolved.ffmpeg_path) is None:
        raise VideoCutError(
            f"ffmpeg not found at '{resolved.ffmpeg_path}'. Install ffmpeg and ensure it is on PATH."
        )


def validate_source_video(path: Path) -> None:
    """Validate that a source video file exists and has a supported extension.

    Args:
        path: Path to the source video.

    Raises:
        VideoCutError: If the file is missing or unsupported.
    """
    if not path.exists():
        raise VideoCutError(f"Source video not found: {path}", source_path=str(path))

    if not path.is_file():
        raise VideoCutError(f"Source path is not a file: {path}", source_path=str(path))

    if path.suffix.lower() not in SUPPORTED_VIDEO_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_VIDEO_EXTENSIONS))
        raise VideoCutError(
            f"Unsupported video format '{path.suffix}'. Supported: {supported}",
            source_path=str(path),
        )


def probe_duration(path: Path, settings: Settings | None = None) -> float:
    """Get the duration of a video file in seconds using ffprobe.

    Args:
        path: Path to the video file.
        settings: Optional settings override.

    Returns:
        Duration in seconds.

    Raises:
        VideoCutError: If ffprobe fails or returns invalid data.
    """
    resolved = settings or get_settings()
    if shutil.which(resolved.ffprobe_path) is None:
        raise VideoCutError(f"ffprobe not found at '{resolved.ffprobe_path}'")

    cmd = [
        resolved.ffprobe_path,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except subprocess.CalledProcessError as exc:
        logger.error("ffprobe failed for {}: {}", path, exc.stderr)
        raise VideoCutError(f"Failed to probe video duration: {path}") from exc
    except subprocess.TimeoutExpired as exc:
        raise VideoCutError(f"ffprobe timed out for: {path}") from exc

    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise VideoCutError(f"Invalid duration from ffprobe for: {path}") from exc


def probe_dimensions(path: Path, settings: Settings | None = None) -> tuple[int, int]:
    """Get video width and height in pixels using ffprobe.

    Args:
        path: Path to the video file.
        settings: Optional settings override.

    Returns:
        Tuple of ``(width, height)``.

    Raises:
        VideoCutError: If ffprobe fails or returns invalid data.
    """
    resolved = settings or get_settings()
    if shutil.which(resolved.ffprobe_path) is None:
        raise VideoCutError(f"ffprobe not found at '{resolved.ffprobe_path}'")

    cmd = [
        resolved.ffprobe_path,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "csv=p=0:s=x",
        str(path),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except subprocess.CalledProcessError as exc:
        logger.error("ffprobe failed for {}: {}", path, exc.stderr)
        raise VideoCutError(f"Failed to probe video dimensions: {path}") from exc
    except subprocess.TimeoutExpired as exc:
        raise VideoCutError(f"ffprobe timed out for: {path}") from exc

    raw = result.stdout.strip()
    if "x" not in raw:
        raise VideoCutError(f"Invalid dimensions from ffprobe for: {path}")

    width_str, height_str = raw.split("x", maxsplit=1)
    try:
        return int(width_str), int(height_str)
    except ValueError as exc:
        raise VideoCutError(f"Invalid dimensions from ffprobe for: {path}") from exc


def run_ffmpeg(
    args: list[str],
    *,
    settings: Settings | None = None,
    timeout: int = 300,
) -> subprocess.CompletedProcess[str]:
    """Run an ffmpeg command and return the completed process.

    Args:
        args: ffmpeg arguments (without the binary name).
        settings: Optional settings override.
        timeout: Command timeout in seconds.

    Returns:
        Completed subprocess result.

    Raises:
        VideoCutError: If ffmpeg is missing or the command fails.
    """
    resolved = settings or get_settings()
    ensure_ffmpeg_available(resolved)

    cmd = [resolved.ffmpeg_path, "-hide_banner", "-loglevel", "error", *args]
    logger.debug("Running ffmpeg: {}", " ".join(cmd))

    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout,
        )
    except subprocess.CalledProcessError as exc:
        logger.error("ffmpeg failed: {}", exc.stderr)
        raise VideoCutError(f"ffmpeg command failed: {exc.stderr.strip()}") from exc
    except subprocess.TimeoutExpired as exc:
        raise VideoCutError("ffmpeg command timed out") from exc
