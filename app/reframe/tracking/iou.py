"""IoU-based greedy face tracker."""

from __future__ import annotations

from dataclasses import dataclass, field

from loguru import logger

from app.core.config import Settings, get_settings
from app.reframe.models.faces import DetectedFace, FrameFaces
from app.reframe.models.tracking import FrameTracks, TrackedFace, TrackingResult, TrackSummary
from app.reframe.tracking.base import FaceTracker
from app.reframe.tracking.geometry import center_distance, intersection_over_union


@dataclass
class _ActiveTrack:
    """Internal track state maintained across frames."""

    track_id: str
    last_face: DetectedFace
    last_frame: int
    last_timestamp: float
    hits: int = 1
    misses: int = 0
    max_consecutive_misses: int = 0
    first_frame: int = 0
    first_timestamp: float = 0.0


@dataclass
class _MatchCandidate:
    """A candidate association between a track and a detection."""

    track_index: int
    detection_index: int
    score: float


@dataclass
class IoUFaceTracker(FaceTracker):
    """Associate detections across frames using IoU and center-distance matching.

    Tracks survive temporary occlusions up to ``tracking_max_age`` missed frames.
    This is a lightweight default tracker with no external model dependencies.
    """

    settings: Settings = field(default_factory=get_settings)
    _tracks: list[_ActiveTrack] = field(default_factory=list, init=False, repr=False)
    _next_track_number: int = field(default=1, init=False, repr=False)

    @property
    def tracker_name(self) -> str:
        return "iou"

    def reset(self) -> None:
        """Clear all active tracks."""
        self._tracks.clear()
        self._next_track_number = 1

    def track(self, frames: list[FrameFaces]) -> TrackingResult:
        if not frames:
            return TrackingResult()

        logger.info("Tracking faces across {} frames with IoU matcher", len(frames))
        output_frames: list[FrameTracks] = []
        summaries: dict[str, TrackSummary] = {}

        for frame in frames:
            output_frames.append(self._track_frame(frame, summaries))

        logger.info(
            "Tracking complete: {} frames, {} unique tracks",
            len(output_frames),
            len(summaries),
        )
        return TrackingResult(frames=output_frames, tracks=summaries)

    def _track_frame(
        self,
        frame: FrameFaces,
        summaries: dict[str, TrackSummary],
    ) -> FrameTracks:
        detections = frame.faces
        matches = self._match_detections(detections)

        matched_tracks: set[int] = set()
        matched_detections: set[int] = set()
        tracked_faces: list[TrackedFace] = []

        for candidate in matches:
            if candidate.track_index in matched_tracks:
                continue
            if candidate.detection_index in matched_detections:
                continue

            track = self._tracks[candidate.track_index]
            detection = detections[candidate.detection_index]
            self._update_track(track, detection, frame)
            self._record_summary(track, summaries)
            matched_tracks.add(candidate.track_index)
            matched_detections.add(candidate.detection_index)

            tracked_faces.append(
                TrackedFace(
                    track_id=track.track_id,
                    bounding_box=detection.bounding_box,
                    detection_confidence=detection.confidence,
                    association_score=candidate.score,
                    landmarks=detection.landmarks,
                )
            )

        for index, track in enumerate(self._tracks):
            if index in matched_tracks:
                continue
            track.misses += 1
            track.max_consecutive_misses = max(track.max_consecutive_misses, track.misses)

        self._tracks = [
            track for track in self._tracks if track.misses <= self._max_age()
        ]
        for track in self._tracks:
            self._record_summary(track, summaries)

        for detection_index, detection in enumerate(detections):
            if detection_index in matched_detections:
                continue
            track = self._create_track(detection, frame)
            self._tracks.append(track)
            self._record_summary(track, summaries)
            tracked_faces.append(
                TrackedFace(
                    track_id=track.track_id,
                    bounding_box=detection.bounding_box,
                    detection_confidence=detection.confidence,
                    association_score=1.0,
                    landmarks=detection.landmarks,
                )
            )

        return FrameTracks(
            frame_number=frame.frame_number,
            timestamp=frame.timestamp,
            image_width=frame.image_width,
            image_height=frame.image_height,
            faces=tracked_faces,
            active_track_ids=[face.track_id for face in tracked_faces],
        )

    def _match_detections(self, detections: list[DetectedFace]) -> list[_MatchCandidate]:
        if not self._tracks or not detections:
            return []

        candidates: list[_MatchCandidate] = []
        iou_threshold = self.settings.tracking_iou_threshold
        max_distance = self.settings.tracking_max_center_distance

        for track_index, track in enumerate(self._tracks):
            for detection_index, detection in enumerate(detections):
                iou = intersection_over_union(track.last_face.bounding_box, detection.bounding_box)
                distance = center_distance(track.last_face.bounding_box, detection.bounding_box)

                if iou < iou_threshold and distance > max_distance:
                    continue

                distance_score = max(0.0, 1.0 - distance / max_distance)
                score = max(iou, distance_score * 0.5)
                candidates.append(
                    _MatchCandidate(
                        track_index=track_index,
                        detection_index=detection_index,
                        score=score,
                    )
                )

        candidates.sort(key=lambda item: item.score, reverse=True)
        return candidates

    def _create_track(self, detection: DetectedFace, frame: FrameFaces) -> _ActiveTrack:
        track_id = f"person_{self._next_track_number}"
        self._next_track_number += 1
        return _ActiveTrack(
            track_id=track_id,
            last_face=detection,
            last_frame=frame.frame_number,
            last_timestamp=frame.timestamp,
            first_frame=frame.frame_number,
            first_timestamp=frame.timestamp,
        )

    def _update_track(
        self,
        track: _ActiveTrack,
        detection: DetectedFace,
        frame: FrameFaces,
    ) -> None:
        track.last_face = detection
        track.last_frame = frame.frame_number
        track.last_timestamp = frame.timestamp
        track.hits += 1
        track.misses = 0

    def _max_age(self) -> int:
        return self.settings.tracking_max_age

    def _record_summary(
        self,
        track: _ActiveTrack,
        summaries: dict[str, TrackSummary],
    ) -> None:
        summaries[track.track_id] = TrackSummary(
            track_id=track.track_id,
            first_frame=track.first_frame,
            last_frame=track.last_frame,
            first_timestamp=track.first_timestamp,
            last_timestamp=track.last_timestamp,
            total_detections=track.hits,
            max_consecutive_misses=track.max_consecutive_misses,
        )
