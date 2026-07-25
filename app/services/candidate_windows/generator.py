"""Candidate window generation from enrichment signals."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from app.core.config import Settings, get_settings
from app.models.candidate_window import CandidateWindow, CandidateWindowResult
from app.models.transcript import TranscriptSegment
from app.services.enrichment.adapters.scene import ReframeSceneEnrichment
from app.services.enrichment.adapters.transcript import TranscriptEnrichment
from app.services.enrichment.base import EnrichmentModule, EnrichmentSignal


@dataclass(frozen=True)
class _MergedWindow:
    start_seconds: float
    end_seconds: float
    score: float
    labels: tuple[str, ...]
    signal_types: tuple[str, ...]
    details: str


class CandidateWindowGenerator:
    """Merge enrichment signals into ranked candidate clip windows."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        modules: list[EnrichmentModule] | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._modules = modules or [
            TranscriptEnrichment(),
            ReframeSceneEnrichment(),
        ]

    def generate(
        self,
        segments: list[TranscriptSegment],
        *,
        video_path: str | Path | None = None,
        top_n: int | None = None,
    ) -> CandidateWindowResult:
        """Generate ranked candidate windows from transcript and optional video."""
        video_value = str(video_path) if video_path is not None else None
        signals: list[EnrichmentSignal] = []
        for module in self._modules:
            signals.extend(module.analyze(segments, video_path=video_value))

        merged = _merge_signals(
            signals,
            merge_gap=self.settings.candidate_window_merge_gap,
            min_duration=self.settings.candidate_window_min_duration,
            max_duration=self.settings.candidate_window_max_duration,
        )
        ranked = sorted(merged, key=lambda window: window.score, reverse=True)
        limit = top_n if top_n is not None else self.settings.max_clips
        windows = [
            CandidateWindow(
                start_seconds=window.start_seconds,
                end_seconds=window.end_seconds,
                score=min(10.0, window.score * 10.0),
                labels=list(window.labels),
                signal_types=list(window.signal_types),
                reasoning=window.details,
            )
            for window in ranked[:limit]
        ]

        logger.info(
            "Generated {} candidate windows from {} enrichment signals",
            len(windows),
            len(signals),
        )
        return CandidateWindowResult(windows=windows, signal_count=len(signals))


def generate_candidate_windows(
    segments: list[TranscriptSegment],
    *,
    video_path: str | Path | None = None,
    settings: Settings | None = None,
    top_n: int | None = None,
) -> CandidateWindowResult:
    """Convenience function to generate candidate windows."""
    return CandidateWindowGenerator(settings=settings).generate(
        segments,
        video_path=video_path,
        top_n=top_n,
    )


def _merge_signals(
    signals: list[EnrichmentSignal],
    *,
    merge_gap: float,
    min_duration: float,
    max_duration: float,
) -> list[_MergedWindow]:
    if not signals:
        return []

    sorted_signals = sorted(signals, key=lambda signal: signal.start_seconds)
    merged: list[_MergedWindow] = []
    current = _signal_to_window(sorted_signals[0])

    for signal in sorted_signals[1:]:
        if signal.start_seconds - current.end_seconds <= merge_gap:
            current = _MergedWindow(
                start_seconds=current.start_seconds,
                end_seconds=max(current.end_seconds, signal.end_seconds),
                score=max(current.score, signal.score),
                labels=tuple(dict.fromkeys((*current.labels, signal.label))),
                signal_types=tuple(dict.fromkeys((*current.signal_types, signal.signal_type))),
                details=current.details or signal.details,
            )
            continue

        merged.append(_clamp_window(current, min_duration=min_duration, max_duration=max_duration))
        current = _signal_to_window(signal)

    merged.append(_clamp_window(current, min_duration=min_duration, max_duration=max_duration))
    return merged


def _signal_to_window(signal: EnrichmentSignal) -> _MergedWindow:
    return _MergedWindow(
        start_seconds=signal.start_seconds,
        end_seconds=signal.end_seconds,
        score=signal.score,
        labels=(signal.label,),
        signal_types=(signal.signal_type,),
        details=signal.details,
    )


def _clamp_window(
    window: _MergedWindow,
    *,
    min_duration: float,
    max_duration: float,
) -> _MergedWindow:
    duration = window.end_seconds - window.start_seconds
    if duration < min_duration:
        end_seconds = window.start_seconds + min_duration
    elif duration > max_duration:
        end_seconds = window.start_seconds + max_duration
    else:
        end_seconds = window.end_seconds

    return _MergedWindow(
        start_seconds=window.start_seconds,
        end_seconds=end_seconds,
        score=window.score,
        labels=window.labels,
        signal_types=window.signal_types,
        details=window.details,
    )
