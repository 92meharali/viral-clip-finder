"""Safe crop generator implementation."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.reframe.crop.base import CropGenerator
from app.reframe.crop.geometry import (
    crop_from_center,
    enforce_face_safety,
    max_vertical_crop_size,
    pan_fixed_crop_for_faces,
)
from app.reframe.crop.interpolate import merge_crop_segments
from app.reframe.crop.speaker_pan import resolve_speaker_pan_center, smooth_pan_crop_frames
from app.reframe.models.camera import CameraPath
from app.reframe.models.crop import CropFrame, CropPlan
from app.reframe.models.importance import ImportanceScoringResult
from app.reframe.models.speakers import SpeakerEstimationResult
from app.reframe.models.tracking import TrackingResult


class SafeCropGenerator(CropGenerator):
    """Generate clamped, face-safe crop rectangles."""

    generator_name = "safe"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def generate(
        self,
        camera_path: CameraPath,
        tracking: TrackingResult,
        *,
        speaker_result: SpeakerEstimationResult | None = None,
        importance: ImportanceScoringResult | None = None,
    ) -> CropPlan:
        tracking_by_frame = {frame.frame_number: frame for frame in tracking.frames}
        speaker_by_frame = (
            {frame.frame_number: frame for frame in speaker_result.frames}
            if speaker_result is not None
            else {}
        )
        importance_by_frame = (
            {frame.frame_number: frame for frame in importance.frames}
            if importance is not None
            else {}
        )
        target_width = self.settings.vertical_width
        target_height = self.settings.vertical_height
        target_aspect = camera_path.target_aspect

        crop_frames: list[CropFrame] = []
        pan_only = self.settings.reframe_pan_only
        fixed_width, fixed_height = max_vertical_crop_size(
            camera_path.source_width,
            camera_path.source_height,
            target_aspect,
        )
        speaker_track_by_frame: dict[int, str | None] = {}

        for camera_frame in camera_path.frames:
            tracked_frame = tracking_by_frame.get(camera_frame.frame_number)
            speaker_frame = speaker_by_frame.get(camera_frame.frame_number)
            importance_frame = importance_by_frame.get(camera_frame.frame_number)
            faces = tracked_frame.faces if tracked_frame is not None else []
            speaker_track_by_frame[camera_frame.frame_number] = (
                speaker_frame.active_track_id if speaker_frame is not None else None
            )

            if pan_only:
                center_x, center_y = resolve_speaker_pan_center(
                    tracked_frame,
                    speaker_frame,
                    importance_frame,
                    fallback_center_x=camera_frame.center_x,
                    fallback_center_y=camera_frame.center_y,
                    min_speaker_confidence=self.settings.speaker_min_confidence,
                )
                safe_crop = crop_from_center(
                    frame_number=camera_frame.frame_number,
                    timestamp=camera_frame.timestamp,
                    center_x=center_x,
                    center_y=center_y,
                    crop_width=fixed_width,
                    crop_height=fixed_height,
                    source_width=camera_path.source_width,
                    source_height=camera_path.source_height,
                )
                active_track = speaker_frame.active_track_id if speaker_frame else None
                if active_track is not None:
                    active_faces = [
                        face for face in faces if face.track_id == active_track
                    ]
                else:
                    active_faces = faces
                safe_crop = pan_fixed_crop_for_faces(
                    safe_crop,
                    active_faces,
                    source_width=camera_path.source_width,
                    source_height=camera_path.source_height,
                    face_padding=float(self.settings.crop_face_safety_padding),
                )
            else:
                from app.reframe.crop.geometry import (
                    camera_state_to_crop,
                    clamp_crop_to_source,
                )

                raw_crop = camera_state_to_crop(
                    frame_number=camera_frame.frame_number,
                    timestamp=camera_frame.timestamp,
                    center_x=camera_frame.center_x,
                    center_y=camera_frame.center_y,
                    crop_width=camera_frame.zoom,
                    crop_height=camera_frame.crop_height,
                )
                clamped = clamp_crop_to_source(
                    raw_crop,
                    source_width=camera_path.source_width,
                    source_height=camera_path.source_height,
                    target_aspect=target_aspect,
                )
                safe_crop = enforce_face_safety(
                    clamped,
                    faces,
                    source_width=camera_path.source_width,
                    source_height=camera_path.source_height,
                    target_aspect=target_aspect,
                    face_padding=float(self.settings.crop_face_safety_padding),
                )

            crop_frames.append(safe_crop)

        if pan_only:
            crop_frames = smooth_pan_crop_frames(
                crop_frames,
                settings=self.settings,
                speaker_track_by_frame=speaker_track_by_frame,
            )

        segments = merge_crop_segments(
            crop_frames,
            merge_threshold=self.settings.reframe_segment_merge_threshold,
        )

        return CropPlan(
            source_width=camera_path.source_width,
            source_height=camera_path.source_height,
            target_width=target_width,
            target_height=target_height,
            frames=crop_frames,
            segments=segments,
        )
