"""Face orientation signal for active speaker estimation."""

from __future__ import annotations

import math
from pathlib import Path

from app.models.transcript import TranscriptSegment
from app.reframe.models.tracking import FrameTracks, TrackedFace, TrackingResult


def _frontal_score(track_face: TrackedFace, *, frame_area: float) -> float:
    landmarks = track_face.landmarks
    bbox = track_face.bounding_box

    orientation_score = 0.6
    if landmarks is not None and landmarks.left_eye is not None and landmarks.right_eye is not None:
        left_eye = landmarks.left_eye
        right_eye = landmarks.right_eye
        eye_distance = math.hypot(right_eye[0] - left_eye[0], right_eye[1] - left_eye[1])
        eye_tilt = abs(right_eye[1] - left_eye[1])
        if eye_distance > 0:
            frontal_ratio = max(0.0, 1.0 - (eye_tilt / eye_distance))
            orientation_score = 0.4 + 0.6 * frontal_ratio

    presence_ratio = min(1.0, bbox.area / max(frame_area * 0.08, 1.0))
    return float(min(1.0, 0.7 * orientation_score + 0.3 * presence_ratio))


class FaceOrientationSignal:
    """Prefer frontal, screen-dominant faces as likely speakers."""

    signal_type = "face_orientation"

    def score_frames(
        self,
        tracking: TrackingResult,
        *,
        transcript_segments: list[TranscriptSegment] | None = None,
        video_path: Path | None = None,
        video_duration: float | None = None,
    ) -> dict[int, dict[str, float]]:
        scores: dict[int, dict[str, float]] = {}

        for frame in tracking.frames:
            frame_area = float(frame.image_width * frame.image_height)
            scores[frame.frame_number] = {
                face.track_id: _frontal_score(face, frame_area=frame_area)
                for face in frame.faces
            }

        return scores
