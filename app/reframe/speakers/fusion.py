"""Multi-signal fusion active speaker estimator."""

from __future__ import annotations

from pathlib import Path

from app.core.config import Settings, get_settings
from app.models.transcript import TranscriptSegment
from app.reframe.models.speakers import (
    ActiveSpeaker,
    FrameSpeakerConfidence,
    SignalContribution,
    SpeakerEstimationResult,
)
from app.reframe.models.tracking import TrackingResult
from app.reframe.speakers.base import ActiveSpeakerEstimator
from app.reframe.speakers.signals.audio import AudioEnergySignal
from app.reframe.speakers.signals.mouth import MouthMovementSignal
from app.reframe.speakers.signals.orientation import FaceOrientationSignal
from app.reframe.speakers.signals.transcript import TranscriptTimingSignal


class FusionActiveSpeakerEstimator(ActiveSpeakerEstimator):
    """Fuse transcript, mouth, orientation, and audio signals."""

    estimator_name = "fusion"

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        transcript_signal: TranscriptTimingSignal | None = None,
        mouth_signal: MouthMovementSignal | None = None,
        orientation_signal: FaceOrientationSignal | None = None,
        audio_signal: AudioEnergySignal | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._transcript_signal = transcript_signal or TranscriptTimingSignal()
        self._mouth_signal = mouth_signal or MouthMovementSignal()
        self._orientation_signal = orientation_signal or FaceOrientationSignal()
        self._audio_signal = audio_signal or AudioEnergySignal(
            settings=self.settings,
            window_seconds=self.settings.speaker_audio_window_seconds,
        )

    def estimate(
        self,
        tracking: TrackingResult,
        *,
        transcript_segments: list[TranscriptSegment] | None = None,
        video_path: Path | None = None,
        video_duration: float | None = None,
    ) -> SpeakerEstimationResult:
        if not tracking.frames:
            return SpeakerEstimationResult()

        resolved_duration = video_duration
        if resolved_duration is None and tracking.frames:
            resolved_duration = tracking.frames[-1].timestamp

        signal_maps = {
            self._transcript_signal.signal_type: self._transcript_signal.score_frames(
                tracking,
                transcript_segments=transcript_segments,
                video_path=video_path,
                video_duration=resolved_duration,
            ),
            self._mouth_signal.signal_type: self._mouth_signal.score_frames(
                tracking,
                transcript_segments=transcript_segments,
                video_path=video_path,
                video_duration=resolved_duration,
            ),
            self._orientation_signal.signal_type: self._orientation_signal.score_frames(
                tracking,
                transcript_segments=transcript_segments,
                video_path=video_path,
                video_duration=resolved_duration,
            ),
            self._audio_signal.signal_type: self._audio_signal.score_frames(
                tracking,
                transcript_segments=transcript_segments,
                video_path=video_path,
                video_duration=resolved_duration,
            ),
        }

        weights = {
            "transcript_timing": self.settings.speaker_weight_transcript,
            "mouth_movement": self.settings.speaker_weight_mouth,
            "face_orientation": self.settings.speaker_weight_orientation,
            "audio_energy": self.settings.speaker_weight_audio,
        }

        frame_results: list[FrameSpeakerConfidence] = []
        for frame in tracking.frames:
            track_ids = {face.track_id for face in frame.faces}
            track_scores: dict[str, float] = {}
            breakdown: dict[str, list[SignalContribution]] = {}

            for track_id in track_ids:
                contributions: list[SignalContribution] = []
                weighted_total = 0.0
                weight_sum = 0.0

                for signal_type, frame_map in signal_maps.items():
                    signal_score = frame_map.get(frame.frame_number, {}).get(track_id, 0.0)
                    weight = weights[signal_type]
                    contributions.append(
                        SignalContribution(signal_type=signal_type, score=signal_score)
                    )
                    weighted_total += weight * signal_score
                    weight_sum += weight

                final_score = weighted_total / weight_sum if weight_sum > 0 else 0.0
                track_scores[track_id] = final_score
                breakdown[track_id] = contributions

            active_track_id = _pick_active_track(
                track_scores,
                min_confidence=self.settings.speaker_min_confidence,
            )
            frame_results.append(
                FrameSpeakerConfidence(
                    frame_number=frame.frame_number,
                    timestamp=frame.timestamp,
                    active_track_id=active_track_id,
                    track_scores=track_scores,
                    signal_breakdown=breakdown,
                )
            )

        segments = _merge_segments(
            frame_results,
            min_segment_seconds=self.settings.speaker_min_segment_seconds,
        )
        return SpeakerEstimationResult(frames=frame_results, segments=segments)


def _pick_active_track(
    track_scores: dict[str, float],
    *,
    min_confidence: float,
) -> str | None:
    if not track_scores:
        return None

    track_id, score = max(track_scores.items(), key=lambda item: item[1])
    if score < min_confidence:
        return None
    return track_id


def _merge_segments(
    frames: list[FrameSpeakerConfidence],
    *,
    min_segment_seconds: float,
) -> list[ActiveSpeaker]:
    if not frames:
        return []

    segments: list[ActiveSpeaker] = []
    current_track: str | None = None
    current_start = 0.0
    current_end = 0.0
    confidence_values: list[float] = []

    for frame in frames:
        if frame.active_track_id is None:
            if current_track is not None:
                segments.append(
                    _build_segment(
                        current_track,
                        current_start,
                        current_end,
                        confidence_values,
                        min_segment_seconds=min_segment_seconds,
                    )
                )
                current_track = None
                confidence_values = []
            continue

        score = frame.track_scores.get(frame.active_track_id, 0.0)
        if current_track is None:
            current_track = frame.active_track_id
            current_start = frame.timestamp
            current_end = frame.timestamp
            confidence_values = [score]
            continue

        if frame.active_track_id == current_track:
            current_end = frame.timestamp
            confidence_values.append(score)
            continue

        segments.append(
            _build_segment(
                current_track,
                current_start,
                current_end,
                confidence_values,
                min_segment_seconds=min_segment_seconds,
            )
        )
        current_track = frame.active_track_id
        current_start = frame.timestamp
        current_end = frame.timestamp
        confidence_values = [score]

    if current_track is not None:
        segments.append(
            _build_segment(
                current_track,
                current_start,
                current_end,
                confidence_values,
                min_segment_seconds=min_segment_seconds,
            )
        )

    return segments


def _build_segment(
    track_id: str,
    start_time: float,
    end_time: float,
    confidence_values: list[float],
    *,
    min_segment_seconds: float,
) -> ActiveSpeaker:
    duration = max(0.0, end_time - start_time)
    if duration < min_segment_seconds:
        end_time = start_time + min_segment_seconds

    mean_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
    if end_time <= start_time:
        end_time = start_time + min_segment_seconds

    return ActiveSpeaker(
        track_id=track_id,
        confidence=mean_confidence,
        start_time=start_time,
        end_time=end_time,
    )
