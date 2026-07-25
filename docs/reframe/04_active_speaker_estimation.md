# Module 4 — Active Speaker Estimation

Module 4 estimates who is speaking at each moment by fusing transcript timing, mouth movement, face orientation, and audio energy.

## Why this module exists

Center cropping fails when the editor does not know who is talking. Active speaker estimation gives later modules a stable answer to:

- Who should the virtual camera follow?
- When did the conversation switch speakers?
- Which face deserves attention during overlapping dialogue?

## Architecture

```
TrackingResult (Module 2)
  +
Transcript segments (optional)
  +
Video audio (optional)
  ↓
Signal providers
  ├── Transcript timing
  ├── Mouth movement
  ├── Face orientation
  └── Audio energy
  ↓
FusionActiveSpeakerEstimator
  ↓
SpeakerEstimationResult
  ├── ActiveSpeaker[]   (merged time spans)
  └── FrameSpeakerConfidence[]   (per-frame scores)
```

## Package layout

| Path | Purpose |
|------|---------|
| `app/reframe/models/speakers.py` | `ActiveSpeaker`, `SpeakerEstimationResult` |
| `app/reframe/speakers/base.py` | `ActiveSpeakerEstimator` interface |
| `app/reframe/speakers/signals/` | Individual signal providers |
| `app/reframe/speakers/fusion.py` | Weighted multi-signal fusion |
| `app/reframe/speakers/factory.py` | Estimator factory |
| `app/reframe/speakers/service.py` | `ActiveSpeakerEstimationService` |

## Output schema

### `ActiveSpeaker`

```json
{
  "track_id": "person_1",
  "confidence": 0.82,
  "start_time": 12.5,
  "end_time": 18.0,
  "speaker_label": null
}
```

### `SpeakerEstimationResult`

```json
{
  "segments": [
    {"track_id": "person_1", "confidence": 0.82, "start_time": 12.5, "end_time": 18.0}
  ],
  "frames": [
    {
      "frame_number": 25,
      "timestamp": 12.5,
      "active_track_id": "person_1",
      "track_scores": {"person_1": 0.84, "person_2": 0.31},
      "signal_breakdown": {
        "person_1": [
          {"signal_type": "mouth_movement", "score": 0.95},
          {"signal_type": "transcript_timing", "score": 1.0}
        ]
      }
    }
  ]
}
```

## Usage

```python
from app.reframe import estimate_active_speakers, track_faces_in_video

tracking = track_faces_in_video("episode.mp4")
result = estimate_active_speakers(
    tracking,
    transcript_segments=segments,
    video_path="episode.mp4",
)

for segment in result.segments:
    print(segment.track_id, segment.start_time, segment.end_time, segment.confidence)
```

## Signals

| Signal | What it measures | Notes |
|--------|------------------|-------|
| `transcript_timing` | Dialogue-active windows | Strong when one face is visible |
| `mouth_movement` | Mouth landmark motion | Primary differentiator in multi-face frames |
| `face_orientation` | Frontal, screen-dominant faces | Helps when mouths are ambiguous |
| `audio_energy` | RMS loudness windows | Boosts visible tracks during speech |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SPEAKER_ESTIMATOR` | `fusion` | Estimator backend |
| `SPEAKER_WEIGHT_TRANSCRIPT` | `0.25` | Transcript timing weight |
| `SPEAKER_WEIGHT_MOUTH` | `0.35` | Mouth movement weight |
| `SPEAKER_WEIGHT_ORIENTATION` | `0.20` | Face orientation weight |
| `SPEAKER_WEIGHT_AUDIO` | `0.20` | Audio energy weight |
| `SPEAKER_MIN_CONFIDENCE` | `0.4` | Minimum fused score to call a speaker active |
| `SPEAKER_MIN_SEGMENT_SECONDS` | `0.3` | Minimum merged segment duration |
| `SPEAKER_AUDIO_WINDOW_SECONDS` | `0.25` | Audio RMS window size |

## Future extension points

- Speaker diarization to map transcript labels to `track_id`
- Lip-sync models for higher mouth-confidence accuracy
- Voice activity detection without transcript dependency
- Per-speaker audio embeddings for multi-mic content

## Tradeoffs

- Without diarization, transcript timing cannot uniquely identify a face in group shots; mouth movement carries most of the discrimination burden.
- Audio energy is global, so it boosts all visible faces during loud speech and relies on mouth/orientation to pick the winner.
- Confidence thresholds are configurable because Mafia-style table footage varies widely in face count and camera distance.
