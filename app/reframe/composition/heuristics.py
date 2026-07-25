"""Mafia-style heuristic shot composition planner."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.reframe.composition.base import CompositionPlanner
from app.reframe.composition.framing import compute_framing_target
from app.reframe.models.composition import CompositionResult, FrameComposition, ShotType
from app.reframe.models.importance import FrameImportance, ImportanceScore, ImportanceScoringResult
from app.reframe.models.scenes import SceneDetectionResult
from app.reframe.models.speakers import FrameSpeakerConfidence, SpeakerEstimationResult
from app.reframe.models.tracking import FrameTracks, TrackingResult


class HeuristicCompositionPlanner(CompositionPlanner):
    """Classify shots and build framing targets using configurable heuristics."""

    planner_name = "heuristic"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def plan(
        self,
        tracking: TrackingResult,
        importance: ImportanceScoringResult,
        *,
        speaker_result: SpeakerEstimationResult | None = None,
        scene_result: SceneDetectionResult | None = None,
    ) -> CompositionResult:
        if not tracking.frames:
            return CompositionResult(
                source_width=1,
                source_height=1,
                target_aspect=self._target_aspect(),
            )

        importance_by_frame = {frame.frame_number: frame for frame in importance.frames}
        speaker_by_frame = (
            {frame.frame_number: frame for frame in speaker_result.frames}
            if speaker_result is not None
            else {}
        )
        rapid_discussion = _is_rapid_discussion(speaker_result, self.settings)

        frame_results: list[FrameComposition] = []
        for frame in tracking.frames:
            importance_frame = importance_by_frame.get(frame.frame_number)
            speaker_frame = speaker_by_frame.get(frame.frame_number)
            shot_type, target_track_ids, reasoning = _classify_shot(
                frame,
                importance_frame,
                speaker_frame,
                rapid_discussion=rapid_discussion,
                settings=self.settings,
            )
            zoom_multiplier = _zoom_multiplier_for_shot(shot_type, self.settings)
            framing = compute_framing_target(
                frame.faces,
                target_track_ids,
                image_width=frame.image_width,
                image_height=frame.image_height,
                target_aspect=self._target_aspect(),
                min_padding=float(self.settings.composition_min_padding),
                forehead_padding_ratio=self.settings.composition_forehead_padding_ratio,
                rule_of_thirds_offset=self.settings.composition_rule_of_thirds_offset,
                zoom_multiplier=zoom_multiplier,
            )
            frame_results.append(
                FrameComposition(
                    frame_number=frame.frame_number,
                    timestamp=frame.timestamp,
                    shot_type=shot_type,
                    target_track_ids=target_track_ids,
                    framing=framing,
                    zoom_multiplier=zoom_multiplier,
                    reasoning=reasoning,
                )
            )

        source = tracking.frames[0]
        return CompositionResult(
            source_width=source.image_width,
            source_height=source.image_height,
            target_aspect=self._target_aspect(),
            frames=frame_results,
        )

    def _target_aspect(self) -> float:
        return self.settings.vertical_width / self.settings.vertical_height


def _classify_shot(
    frame: FrameTracks,
    importance_frame: FrameImportance | None,
    speaker_frame: FrameSpeakerConfidence | None,
    *,
    rapid_discussion: bool,
    settings: Settings,
) -> tuple[ShotType, list[str], str]:
    visible_track_ids = [face.track_id for face in frame.faces]
    if not visible_track_ids:
        return (
            ShotType.WIDE_TABLE,
            [],
            "no visible faces; default wide framing",
        )

    if speaker_frame is not None and speaker_frame.active_track_id is not None:
        active_track = speaker_frame.active_track_id
        active_confidence = speaker_frame.track_scores.get(active_track, 0.0)
        if (
            active_track in visible_track_ids
            and active_confidence >= settings.speaker_min_confidence
        ):
            return (
                ShotType.SINGLE_SPEAKER,
                [active_track],
                "follow active speaker",
            )

    importance_scores = importance_frame.scores if importance_frame is not None else []
    ranked_track_ids = [score.track_id for score in importance_scores] or visible_track_ids
    top_score = importance_scores[0].score if importance_scores else 1.0
    second_score = importance_scores[1].score if len(importance_scores) > 1 else 0.0

    if len(visible_track_ids) >= settings.composition_vote_reveal_face_threshold:
        return (
            ShotType.VOTE_REVEAL,
            visible_track_ids,
            "many participants visible; show the full table",
        )

    if len(visible_track_ids) >= settings.composition_group_face_threshold:
        return (
            ShotType.GROUP_REACTION,
            _select_group_targets(importance_scores, visible_track_ids, settings),
            "group reaction; widen to include multiple faces",
        )

    reaction_track = _find_reaction_focus(importance_scores, speaker_frame)
    if reaction_track is not None:
        return (
            ShotType.SILENT_REACTION,
            [reaction_track],
            "silent reaction; prioritize the reacting participant",
        )

    if rapid_discussion and len(visible_track_ids) >= 2:
        return (
            ShotType.CONVERSATION,
            ranked_track_ids[:2],
            "rapid back-and-forth discussion; include both participants",
        )

    if (
        len(visible_track_ids) >= 2
        and (top_score - second_score) <= settings.composition_conversation_importance_gap
    ):
        return (
            ShotType.CONVERSATION,
            ranked_track_ids[:2],
            "balanced importance between two participants",
        )

    if len(visible_track_ids) >= 2 and second_score >= settings.composition_secondary_importance_min:
        return (
            ShotType.CONVERSATION,
            ranked_track_ids[:2],
            "secondary participant remains conversation-relevant",
        )

    return (
        ShotType.SINGLE_SPEAKER,
        [ranked_track_ids[0]],
        "single dominant speaker focus",
    )


def _select_group_targets(
    importance_scores: list[ImportanceScore],
    visible_track_ids: list[str],
    settings: Settings,
) -> list[str]:
    if not importance_scores:
        return visible_track_ids

    selected = [
        score.track_id
        for score in importance_scores
        if score.score >= settings.composition_group_importance_min
    ]
    return selected or visible_track_ids


def _find_reaction_focus(
    importance_scores: list[ImportanceScore],
    speaker_frame: FrameSpeakerConfidence | None,
) -> str | None:
    if not importance_scores:
        return None

    active_track_id = speaker_frame.active_track_id if speaker_frame is not None else None
    for score in importance_scores:
        if score.track_id == active_track_id:
            continue
        if "reaction focus" in score.reasoning:
            return score.track_id
    return None


def _is_rapid_discussion(
    speaker_result: SpeakerEstimationResult | None,
    settings: Settings,
) -> bool:
    if speaker_result is None or len(speaker_result.segments) < settings.composition_rapid_speaker_changes:
        return False

    segments = sorted(speaker_result.segments, key=lambda segment: segment.start_time)
    changes = 0
    previous_track: str | None = None
    window_start = segments[-1].end_time - settings.composition_rapid_discussion_seconds

    for segment in segments:
        if segment.end_time < window_start:
            continue
        if previous_track is not None and segment.track_id != previous_track:
            changes += 1
        previous_track = segment.track_id

    return changes >= settings.composition_rapid_speaker_changes - 1


def _zoom_multiplier_for_shot(shot_type: ShotType, settings: Settings) -> float:
    mapping = {
        ShotType.SINGLE_SPEAKER: settings.composition_zoom_single_speaker,
        ShotType.CONVERSATION: settings.composition_zoom_conversation,
        ShotType.GROUP_REACTION: settings.composition_zoom_group_reaction,
        ShotType.VOTE_REVEAL: settings.composition_zoom_vote_reveal,
        ShotType.MULTI_REACTION: settings.composition_zoom_group_reaction,
        ShotType.SILENT_REACTION: settings.composition_zoom_single_speaker,
        ShotType.WIDE_TABLE: settings.composition_zoom_vote_reveal,
    }
    return mapping.get(shot_type, 1.0)
