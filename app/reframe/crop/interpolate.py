"""Crop plan interpolation and segment merging."""

from __future__ import annotations

import math

from app.reframe.models.crop import CropFrame, CropSegment


def interpolate_crop_frames(
    frames: list[CropFrame],
    *,
    duration_seconds: float,
    render_fps: float,
) -> list[CropFrame]:
    """Upsample sparse crop keyframes to a uniform render timeline."""
    if not frames:
        return []

    if duration_seconds <= 0:
        return list(frames)

    sorted_frames = sorted(frames, key=lambda frame: frame.timestamp)
    fixed_width = sorted_frames[0].width
    fixed_height = sorted_frames[0].height
    fixed_window = all(
        abs(frame.width - fixed_width) < 0.5 and abs(frame.height - fixed_height) < 0.5
        for frame in sorted_frames
    )
    step = 1.0 / render_fps
    interpolated: list[CropFrame] = []
    frame_index = 0

    time = 0.0
    while time <= duration_seconds + 1e-6:
        while frame_index + 1 < len(sorted_frames) and sorted_frames[frame_index + 1].timestamp <= time:
            frame_index += 1

        current = sorted_frames[frame_index]
        if frame_index + 1 < len(sorted_frames):
            nxt = sorted_frames[frame_index + 1]
            span = nxt.timestamp - current.timestamp
            if span > 0 and time > current.timestamp:
                ratio = (time - current.timestamp) / span
                interpolated.append(
                    CropFrame(
                        frame_number=len(interpolated),
                        timestamp=time,
                        x=_lerp(current.x, nxt.x, ratio),
                        y=_lerp(current.y, nxt.y, ratio),
                        width=fixed_width if fixed_window else _lerp(current.width, nxt.width, ratio),
                        height=(
                            fixed_height if fixed_window else _lerp(current.height, nxt.height, ratio)
                        ),
                    )
                )
            else:
                interpolated.append(_copy_at_time(current, len(interpolated), time))
        else:
            interpolated.append(_copy_at_time(current, len(interpolated), time))

        time += step

    return interpolated


def merge_crop_segments(
    frames: list[CropFrame],
    *,
    merge_threshold: float,
) -> list[CropSegment]:
    """Merge consecutive frames with similar crops into render segments."""
    if not frames:
        return []

    sorted_frames = sorted(frames, key=lambda frame: frame.timestamp)
    segments: list[CropSegment] = []
    start = sorted_frames[0]
    current = sorted_frames[0]

    for frame in sorted_frames[1:]:
        if _crop_distance(current, frame) <= merge_threshold:
            current = frame
            continue

        segments.append(
            CropSegment(
                start_time=start.timestamp,
                end_time=frame.timestamp,
                crop=start,
            )
        )
        start = frame
        current = frame

    end_time = current.timestamp + 1.0 / max(1.0, len(sorted_frames))
    segments.append(
        CropSegment(
            start_time=start.timestamp,
            end_time=end_time,
            crop=start,
        )
    )
    return segments


def _lerp(start: float, end: float, ratio: float) -> float:
    return start + (end - start) * ratio


def _copy_at_time(frame: CropFrame, frame_number: int, timestamp: float) -> CropFrame:
    return CropFrame(
        frame_number=frame_number,
        timestamp=timestamp,
        x=frame.x,
        y=frame.y,
        width=frame.width,
        height=frame.height,
    )


def _crop_distance(left: CropFrame, right: CropFrame) -> float:
    position_distance = math.hypot(left.x - right.x, left.y - right.y)
    if abs(left.width - right.width) < 0.5 and abs(left.height - right.height) < 0.5:
        return position_distance
    return position_distance + abs(left.width - right.width)
