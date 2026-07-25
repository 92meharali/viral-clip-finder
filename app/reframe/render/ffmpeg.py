"""FFmpeg reframe renderer."""

from __future__ import annotations

import tempfile
from pathlib import Path

from loguru import logger

from app.core.config import Settings, get_settings
from app.core.exceptions import ReframeRenderError
from app.reframe.crop.interpolate import interpolate_crop_frames, merge_crop_segments
from app.reframe.models.crop import CropPlan, CropSegment
from app.reframe.models.render import ReframeRenderResult
from app.reframe.render.base import ReframeRenderer
from app.reframe.render.filters import (
    build_segment_blur_filter,
    build_segment_crop_filter,
    even_crop_dimensions,
)
from app.video.ffmpeg import run_ffmpeg, validate_source_video


class FFmpegReframeRenderer(ReframeRenderer):
    """Render crop plans with ffmpeg using merged segments."""

    renderer_name = "ffmpeg"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def render(
        self,
        source_path: str | Path,
        crop_plan: CropPlan,
        output_path: str | Path,
        *,
        duration_seconds: float,
        blurred_background: bool = False,
    ) -> ReframeRenderResult:
        source = Path(source_path).resolve()
        output = Path(output_path).resolve()
        validate_source_video(source)

        if not crop_plan.frames:
            raise ReframeRenderError("Cannot render an empty crop plan")

        output.parent.mkdir(parents=True, exist_ok=True)
        render_fps = self.settings.reframe_render_fps
        interpolated = interpolate_crop_frames(
            crop_plan.frames,
            duration_seconds=duration_seconds,
            render_fps=render_fps,
        )
        segments = merge_crop_segments(
            interpolated,
            merge_threshold=self.settings.reframe_segment_merge_threshold,
        )
        if not segments:
            raise ReframeRenderError("Failed to build render segments from crop plan")

        logger.info(
            "Rendering {} segments from {} crop keyframes to {}",
            len(segments),
            len(crop_plan.frames),
            output.name,
        )

        window = _fixed_crop_window(interpolated)
        if window is not None and not blurred_background:
            self._render_panning_pass(
                source,
                output,
                interpolated,
                crop_plan=crop_plan,
                window=window,
            )
            return ReframeRenderResult(
                source_path=str(source),
                output_path=str(output),
                width=crop_plan.target_width,
                height=crop_plan.target_height,
                segment_count=1,
                crop_keyframe_count=len(crop_plan.frames),
                blurred_background=blurred_background,
                render_fps=render_fps,
            )

        if len(segments) == 1:
            self._render_segment(
                source,
                output,
                segments[0],
                crop_plan=crop_plan,
                blurred_background=blurred_background,
            )
        else:
            self._render_multi_segment(
                source,
                output,
                segments,
                crop_plan=crop_plan,
                blurred_background=blurred_background,
                duration_seconds=duration_seconds,
            )

        return ReframeRenderResult(
            source_path=str(source),
            output_path=str(output),
            width=crop_plan.target_width,
            height=crop_plan.target_height,
            segment_count=len(segments),
            crop_keyframe_count=len(crop_plan.frames),
            blurred_background=blurred_background,
            render_fps=render_fps,
        )

    def _render_segment(
        self,
        source: Path,
        output: Path,
        segment: CropSegment,
        *,
        crop_plan: CropPlan,
        blurred_background: bool,
    ) -> None:
        if blurred_background:
            filter_complex = build_segment_blur_filter(
                segment,
                target_width=crop_plan.target_width,
                target_height=crop_plan.target_height,
                blur_strength=self.settings.vertical_blur_strength,
            )
            args = [
                "-y",
                "-i",
                str(source),
                "-filter_complex",
                filter_complex,
                "-map",
                "[vout]",
                "-map",
                "0:a?",
                "-c:v",
                "libx264",
                "-preset",
                self.settings.reframe_render_preset,
                "-crf",
                str(self.settings.reframe_render_crf),
                "-c:a",
                "copy",
                str(output),
            ]
        else:
            video_filter = build_segment_crop_filter(
                segment,
                target_width=crop_plan.target_width,
                target_height=crop_plan.target_height,
            )
            args = [
                "-y",
                "-i",
                str(source),
                "-vf",
                video_filter,
                "-c:v",
                "libx264",
                "-preset",
                self.settings.reframe_render_preset,
                "-crf",
                str(self.settings.reframe_render_crf),
                "-c:a",
                "copy",
                str(output),
            ]

        run_ffmpeg(args, settings=self.settings)

    def _render_panning_pass(
        self,
        source: Path,
        output: Path,
        frames: list,
        *,
        crop_plan: CropPlan,
        window: tuple[int, int],
    ) -> None:
        """Render a pan-only crop plan in a single ffmpeg pass."""
        width, height = window
        first = min(frames, key=lambda frame: frame.timestamp)
        start_x = max(0, int(round(first.x)))
        start_y = max(0, int(round(first.y)))

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as handle:
            sendcmd_path = Path(handle.name)

        try:
            _write_sendcmd(sendcmd_path, frames, width, height)
            logger.info(
                "Rendering pan-only reframe in a single pass ({}x{} window, {} keyframes)",
                width,
                height,
                len(frames),
            )
            video_filter = (
                f"sendcmd=f={sendcmd_path.as_posix()},"
                f"crop={width}:{height}:{start_x}:{start_y},"
                f"scale={crop_plan.target_width}:{crop_plan.target_height}:flags=lanczos"
            )
            run_ffmpeg(
                [
                    "-y",
                    "-i",
                    str(source),
                    "-vf",
                    video_filter,
                    "-c:v",
                    "libx264",
                    "-preset",
                    self.settings.reframe_render_preset,
                    "-crf",
                    str(self.settings.reframe_render_crf),
                    "-c:a",
                    "copy",
                    str(output),
                ],
                settings=self.settings,
            )
        finally:
            sendcmd_path.unlink(missing_ok=True)

    def _render_multi_segment(
        self,
        source: Path,
        output: Path,
        segments: list[CropSegment],
        *,
        crop_plan: CropPlan,
        blurred_background: bool,
        duration_seconds: float,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="reframe_segments_") as temp_dir:
            temp_path = Path(temp_dir)
            segment_paths: list[Path] = []

            for index, segment in enumerate(segments):
                segment_output = temp_path / f"segment_{index:04d}.mp4"
                start = max(0.0, segment.start_time)
                end = max(start + 0.05, segment.end_time)
                if index == len(segments) - 1:
                    end = max(end, duration_seconds)
                args = self._segment_args(
                    source,
                    segment_output,
                    segment,
                    crop_plan=crop_plan,
                    blurred_background=blurred_background,
                    start_time=start,
                    end_time=end,
                )
                run_ffmpeg(args, settings=self.settings)
                segment_paths.append(segment_output)

            concat_file = temp_path / "concat.txt"
            concat_file.write_text(
                "".join(f"file '{path.as_posix()}'\n" for path in segment_paths),
                encoding="utf-8",
            )
            run_ffmpeg(
                [
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(concat_file),
                    "-c",
                    "copy",
                    str(output),
                ],
                settings=self.settings,
            )

    def _segment_args(
        self,
        source: Path,
        output: Path,
        segment: CropSegment,
        *,
        crop_plan: CropPlan,
        blurred_background: bool,
        start_time: float,
        end_time: float,
    ) -> list[str]:
        if blurred_background:
            filter_complex = build_segment_blur_filter(
                segment,
                target_width=crop_plan.target_width,
                target_height=crop_plan.target_height,
                blur_strength=self.settings.vertical_blur_strength,
            )
            return [
                "-y",
                "-ss",
                f"{start_time:.3f}",
                "-to",
                f"{end_time:.3f}",
                "-i",
                str(source),
                "-filter_complex",
                filter_complex,
                "-map",
                "[vout]",
                "-map",
                "0:a?",
                "-c:v",
                "libx264",
                "-preset",
                self.settings.reframe_render_preset,
                "-crf",
                str(self.settings.reframe_render_crf),
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                str(output),
            ]

        video_filter = build_segment_crop_filter(
            segment,
            target_width=crop_plan.target_width,
            target_height=crop_plan.target_height,
        )
        return [
            "-y",
            "-ss",
            f"{start_time:.3f}",
            "-to",
            f"{end_time:.3f}",
            "-i",
            str(source),
            "-vf",
            video_filter,
            "-c:v",
            "libx264",
            "-preset",
            self.settings.reframe_render_preset,
            "-crf",
            str(self.settings.reframe_render_crf),
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            str(output),
        ]


def _fixed_crop_window(frames: list) -> tuple[int, int] | None:
    """Return crop dimensions when every frame uses the same fixed window."""
    if not frames:
        return None

    width, height = even_crop_dimensions(
        int(round(frames[0].width)),
        int(round(frames[0].height)),
    )
    for frame in frames[1:]:
        next_width, next_height = even_crop_dimensions(
            int(round(frame.width)),
            int(round(frame.height)),
        )
        if next_width != width or next_height != height:
            return None
    return width, height


def _write_sendcmd(path: Path, frames: list, width: int, height: int) -> None:
    """Write ffmpeg sendcmd instructions for a panning crop window."""
    del width, height  # Dimensions are fixed in the initial crop filter.
    lines: list[str] = []
    previous_x: int | None = None
    previous_y: int | None = None
    for frame in sorted(frames, key=lambda item: item.timestamp):
        x = max(0, int(round(frame.x)))
        y = max(0, int(round(frame.y)))
        timestamp = f"{frame.timestamp:.3f}"
        if x != previous_x:
            lines.append(f"{timestamp} crop x {x};")
            previous_x = x
        if y != previous_y:
            lines.append(f"{timestamp} crop y {y};")
            previous_y = y
    path.write_text("\n".join(lines), encoding="utf-8")
