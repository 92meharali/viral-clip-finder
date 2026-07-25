"""Speaker-driven pan targeting and temporal smoothing."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.reframe.crop.geometry import crop_from_center
from app.reframe.models.crop import CropFrame
from app.reframe.models.importance import FrameImportance
from app.reframe.models.speakers import FrameSpeakerConfidence
from app.reframe.models.tracking import FrameTracks, TrackedFace


def resolve_speaker_pan_center(
    tracked_frame: FrameTracks | None,
    speaker_frame: FrameSpeakerConfidence | None,
    importance_frame: FrameImportance | None,
    *,
    fallback_center_x: float,
    fallback_center_y: float,
    min_speaker_confidence: float,
    vertical_offset_ratio: float = 0.05,
) -> tuple[float, float]:
    """Pick a pan center that prioritizes the active speaker's face."""
    if tracked_frame is None or not tracked_frame.faces:
        return (fallback_center_x, fallback_center_y)

    face_by_track = {face.track_id: face for face in tracked_frame.faces}
    target_track: str | None = None

    if speaker_frame is not None and speaker_frame.active_track_id is not None:
        active = speaker_frame.active_track_id
        confidence = speaker_frame.track_scores.get(active, 0.0)
        if confidence >= min_speaker_confidence and active in face_by_track:
            target_track = active

    if target_track is None and importance_frame is not None:
        for score in importance_frame.scores:
            if score.track_id in face_by_track:
                target_track = score.track_id
                break

    if target_track is None:
        return (fallback_center_x, fallback_center_y)

    face = face_by_track[target_track]
    center_x, center_y = _face_framing_center(face, vertical_offset_ratio=vertical_offset_ratio)
    return (center_x, center_y)


def _face_framing_center(
    face: TrackedFace,
    *,
    vertical_offset_ratio: float,
) -> tuple[float, float]:
    bbox = face.bounding_box
    center_x = bbox.center_x
    center_y = bbox.center_y - bbox.height * vertical_offset_ratio
    return (center_x, center_y)


def smooth_pan_crop_frames(
    frames: list[CropFrame],
    *,
    settings: Settings | None = None,
    speaker_track_by_frame: dict[int, str | None] | None = None,
) -> list[CropFrame]:
    """Apply EMA smoothing to pan positions with deadband and speaker-switch easing."""
    if not frames:
        return []

    config = settings or get_settings()
    alpha = config.reframe_pan_smoothing_strength
    switch_alpha = config.reframe_pan_speaker_switch_smoothing
    deadband = config.reframe_pan_deadband_pixels

    sorted_frames = sorted(frames, key=lambda frame: frame.timestamp)
    smoothed: list[CropFrame] = []
    ema_center_x = sorted_frames[0].center_x
    ema_center_y = sorted_frames[0].center_y
    previous_track: str | None = None

    for frame in sorted_frames:
        target_x = frame.center_x
        target_y = frame.center_y
        active_track = (
            speaker_track_by_frame.get(frame.frame_number) if speaker_track_by_frame else None
        )
        frame_alpha = switch_alpha if active_track != previous_track and previous_track is not None else alpha
        previous_track = active_track

        if abs(target_x - ema_center_x) < deadband:
            target_x = ema_center_x
        if abs(target_y - ema_center_y) < deadband:
            target_y = ema_center_y

        ema_center_x = frame_alpha * target_x + (1.0 - frame_alpha) * ema_center_x
        ema_center_y = frame_alpha * target_y + (1.0 - frame_alpha) * ema_center_y

        half_width = frame.width / 2
        half_height = frame.height / 2
        smoothed.append(
            CropFrame(
                frame_number=frame.frame_number,
                timestamp=frame.timestamp,
                x=ema_center_x - half_width,
                y=ema_center_y - half_height,
                width=frame.width,
                height=frame.height,
            )
        )

    return smoothed


def rebuild_crop_at_center(frame: CropFrame, center_x: float, center_y: float) -> CropFrame:
    """Return a crop frame with the same size moved to a new center."""
    return CropFrame(
        frame_number=frame.frame_number,
        timestamp=frame.timestamp,
        x=center_x - frame.width / 2,
        y=center_y - frame.height / 2,
        width=frame.width,
        height=frame.height,
    )


def crop_from_speaker_center(
    *,
    frame_number: int,
    timestamp: float,
    center_x: float,
    center_y: float,
    crop_width: float,
    crop_height: float,
    source_width: int,
    source_height: int,
) -> CropFrame:
    """Build a pan-only crop centered on the active speaker."""
    return crop_from_center(
        frame_number=frame_number,
        timestamp=timestamp,
        center_x=center_x,
        center_y=center_y,
        crop_width=crop_width,
        crop_height=crop_height,
        source_width=source_width,
        source_height=source_height,
    )
