"""Audio energy signal for active speaker estimation."""

from __future__ import annotations

import math
import struct
import subprocess
import wave
from io import BytesIO
from pathlib import Path

from loguru import logger

from app.core.config import Settings, get_settings
from app.core.exceptions import SpeakerEstimationError
from app.models.transcript import TranscriptSegment
from app.reframe.models.tracking import TrackingResult
from app.video.ffmpeg import ensure_ffmpeg_available


def _normalize_energy_samples(samples: list[float]) -> list[float]:
    if not samples:
        return []

    peak = max(samples)
    if peak <= 0:
        return [0.0 for _ in samples]

    return [min(1.0, sample / peak) for sample in samples]


def _extract_audio_rms_windows(
    video_path: Path,
    *,
    settings: Settings,
    window_seconds: float,
) -> list[tuple[float, float]]:
    """Extract mono PCM via ffmpeg and compute RMS per window."""
    ensure_ffmpeg_available(settings)
    sample_rate = 8000
    cmd = [
        settings.ffmpeg_path,
        "-v",
        "error",
        "-i",
        str(video_path),
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-f",
        "wav",
        "pipe:1",
    ]

    try:
        completed = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace")
        raise SpeakerEstimationError(
            f"Failed to extract audio for speaker estimation: {stderr.strip()}"
        ) from exc

    with wave.open(BytesIO(completed.stdout), "rb") as wav_file:
        sample_width = wav_file.getsampwidth()
        frame_count = wav_file.getnframes()
        raw_audio = wav_file.readframes(frame_count)

    if sample_width != 2:
        raise SpeakerEstimationError(
            f"Unsupported WAV sample width for speaker estimation: {sample_width}"
        )

    total_samples = len(raw_audio) // 2
    samples = struct.unpack(f"<{total_samples}h", raw_audio)
    window_size = max(1, int(sample_rate * window_seconds))

    windows: list[tuple[float, float]] = []
    for index in range(0, total_samples, window_size):
        chunk = samples[index : index + window_size]
        if not chunk:
            continue
        mean_square = sum(value * value for value in chunk) / len(chunk)
        rms = math.sqrt(mean_square) / 32768.0
        timestamp = index / sample_rate
        windows.append((timestamp, rms))

    normalized = _normalize_energy_samples([value for _, value in windows])
    return [(timestamp, energy) for (timestamp, _), energy in zip(windows, normalized, strict=True)]


def _energy_at_timestamp(timestamp: float, windows: list[tuple[float, float]]) -> float:
    if not windows:
        return 0.0

    closest = min(windows, key=lambda window: abs(window[0] - timestamp))
    return closest[1]


class AudioEnergySignal:
    """Boost visible tracks during high audio-energy windows."""

    signal_type = "audio_energy"

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        window_seconds: float = 0.25,
        energy_cache: list[tuple[float, float]] | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.window_seconds = window_seconds
        self._energy_cache = energy_cache

    def score_frames(
        self,
        tracking: TrackingResult,
        *,
        transcript_segments: list[TranscriptSegment] | None = None,
        video_path: Path | None = None,
        video_duration: float | None = None,
    ) -> dict[int, dict[str, float]]:
        energy_windows = self._energy_cache
        if energy_windows is None and video_path is not None:
            try:
                energy_windows = _extract_audio_rms_windows(
                    video_path,
                    settings=self.settings,
                    window_seconds=self.window_seconds,
                )
            except SpeakerEstimationError as exc:
                logger.warning("Audio energy unavailable for speaker estimation: {}", exc)
                energy_windows = []

        energy_windows = energy_windows or []
        scores: dict[int, dict[str, float]] = {}

        for frame in tracking.frames:
            energy = _energy_at_timestamp(frame.timestamp, energy_windows)
            if not frame.faces:
                scores[frame.frame_number] = {}
                continue

            scores[frame.frame_number] = {
                face.track_id: energy for face in frame.faces
            }

        return scores
