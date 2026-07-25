"""Transcript-based enrichment adapter."""

from __future__ import annotations

import re

from app.models.transcript import TranscriptSegment
from app.services.enrichment.base import EnrichmentSignal, EnrichmentModule

_EMOTION_PATTERN = re.compile(
    r"\b(never|always|lie|lying|vote|kill|shocked|crazy|insane|wow|what)\b",
    re.IGNORECASE,
)


class TranscriptEnrichment(EnrichmentModule):
    """Generate candidate signals from transcript dialogue."""

    @property
    def module_name(self) -> str:
        return "transcript_analysis"

    def analyze(
        self,
        segments: list[TranscriptSegment],
        *,
        video_path: str | None = None,
    ) -> list[EnrichmentSignal]:
        if not segments:
            return []

        signals: list[EnrichmentSignal] = []
        sorted_segments = sorted(segments, key=lambda segment: segment.seconds)

        for index, segment in enumerate(sorted_segments):
            end_seconds = (
                sorted_segments[index + 1].seconds
                if index + 1 < len(sorted_segments)
                else segment.seconds + max(8.0, len(segment.text.split()) * 0.4)
            )
            score = _score_segment(segment)
            if score < 0.35:
                continue

            labels = ["dialogue_peak"]
            if segment.speaker:
                labels.append("speaker_turn")
            if _EMOTION_PATTERN.search(segment.text):
                labels.append("emotional_language")

            signals.append(
                EnrichmentSignal(
                    start_seconds=segment.seconds,
                    end_seconds=end_seconds,
                    signal_type="transcript_dialogue",
                    score=score,
                    label=labels[0],
                    details=segment.text[:120],
                )
            )

        return signals


def _score_segment(segment: TranscriptSegment) -> float:
    words = segment.text.split()
    word_score = min(1.0, len(words) / 18.0)
    punctuation_boost = 0.15 if "!" in segment.text or "?" in segment.text else 0.0
    emotion_boost = 0.2 if _EMOTION_PATTERN.search(segment.text) else 0.0
    return min(1.0, 0.35 + word_score * 0.35 + punctuation_boost + emotion_boost)
