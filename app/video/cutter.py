"""Video clip extraction using FFmpeg."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from loguru import logger

from app.core.config import Settings, get_settings
from app.core.exceptions import VideoCutError
from app.models.clip import ViralClip
from app.models.export import ExtractedClip
from app.video.ffmpeg import probe_duration, run_ffmpeg, validate_source_video

DEFAULT_OUTPUT_FORMAT = "mp4"


def _build_output_path(output_dir: Path, index: int, output_format: str) -> Path:
    """Generate a numbered output file path such as ``clip1.mp4``."""
    return output_dir / f"clip{index}.{output_format}"


def _stream_copy_args(source: Path, output: Path, start: float, duration: float) -> list[str]:
    """Build ffmpeg arguments for lossless stream copy."""
    return [
        "-y",
        "-ss",
        f"{start:.3f}",
        "-i",
        str(source),
        "-t",
        f"{duration:.3f}",
        "-c",
        "copy",
        "-avoid_negative_ts",
        "make_zero",
        str(output),
    ]


def _reencode_args(source: Path, output: Path, start: float, duration: float) -> list[str]:
    """Build ffmpeg arguments for re-encoded extraction."""
    return [
        "-y",
        "-ss",
        f"{start:.3f}",
        "-i",
        str(source),
        "-t",
        f"{duration:.3f}",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        str(output),
    ]


def _extract_single_clip(
    source: Path,
    output: Path,
    clip: ViralClip,
    *,
    settings: Settings,
    force_reencode: bool = False,
) -> bool:
    """Extract one clip, trying stream copy first.

    Returns:
        True if the clip was re-encoded, False if stream-copied.
    """
    duration = clip.duration_seconds

    if not force_reencode:
        try:
            run_ffmpeg(
                _stream_copy_args(source, output, clip.start_seconds, duration),
                settings=settings,
            )
            logger.info("Stream-copied clip to {}", output)
            return False
        except VideoCutError:
            logger.warning(
                "Stream copy failed for {}-{}, falling back to re-encode", clip.start, clip.end
            )

    run_ffmpeg(
        _reencode_args(source, output, clip.start_seconds, duration),
        settings=settings,
    )
    logger.info("Re-encoded clip to {}", output)
    return True


class VideoCutter:
    """Extract viral clips from a source video using FFmpeg."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the video cutter.

        Args:
            settings: Optional settings override.
        """
        self.settings = settings or get_settings()

    def cut(
        self,
        source_video: str | Path,
        clips: Sequence[ViralClip],
        output_dir: str | Path | None = None,
        *,
        output_format: str = DEFAULT_OUTPUT_FORMAT,
    ) -> list[ExtractedClip]:
        """Extract clips from a source video file.

        Attempts stream copy (no re-encode) for each clip. Falls back to
        H.264/AAC re-encoding if stream copy fails.

        Args:
            source_video: Path to the source video (MP4, MOV, or MKV).
            clips: Clips to extract with start/end timestamps.
            output_dir: Directory for output files. Defaults to ``settings.output_dir``.
            output_format: Output container format extension (default: mp4).

        Returns:
            Metadata for each successfully extracted clip.

        Raises:
            VideoCutError: If the source is invalid, clips are empty, or cutting fails.
        """
        if not clips:
            raise VideoCutError("Cannot cut an empty clip list")

        source = Path(source_video).resolve()
        validate_source_video(source)

        out_dir = Path(output_dir or self.settings.output_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        video_duration = probe_duration(source, self.settings)
        logger.info(
            "Cutting {} clips from {} (duration {:.1f}s) → {}",
            len(clips),
            source.name,
            video_duration,
            out_dir,
        )

        extracted: list[ExtractedClip] = []
        output_index = 0

        for clip in clips:
            if clip.end_seconds > video_duration:
                logger.warning(
                    "Clip end {} exceeds video duration {:.1f}s, skipping",
                    clip.end,
                    video_duration,
                )
                continue

            output_index += 1
            output_path = _build_output_path(out_dir, output_index, output_format)
            reencoded = _extract_single_clip(
                source,
                output_path,
                clip,
                settings=self.settings,
            )

            extracted.append(
                ExtractedClip(
                    index=output_index,
                    source_path=str(source),
                    output_path=str(output_path),
                    start=clip.start,
                    end=clip.end,
                    start_seconds=clip.start_seconds,
                    end_seconds=clip.end_seconds,
                    duration_seconds=clip.duration_seconds,
                    reencoded=reencoded,
                )
            )

        if not extracted:
            raise VideoCutError(
                "No clips were extracted. Check timestamps against video duration.",
                source_path=str(source),
            )

        logger.info("Extracted {} clips to {}", len(extracted), out_dir)
        return extracted


def cut_clips(
    source_video: str | Path,
    clips: Sequence[ViralClip],
    output_dir: str | Path | None = None,
    *,
    settings: Settings | None = None,
    output_format: str = DEFAULT_OUTPUT_FORMAT,
) -> list[ExtractedClip]:
    """Convenience function to extract clips from a source video.

    Args:
        source_video: Path to the source video file.
        clips: Clips to extract.
        output_dir: Output directory for clip files.
        settings: Optional settings override.
        output_format: Output file format extension.

    Returns:
        List of extracted clip metadata.
    """
    return VideoCutter(settings=settings).cut(
        source_video,
        clips,
        output_dir,
        output_format=output_format,
    )
