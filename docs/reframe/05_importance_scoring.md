# Module 5 — Importance Scoring

Module 5 decides which tracked faces deserve attention at each moment by fusing speaking status, expression, screen presence, and reaction heuristics.

## Why this module exists

Active speaker estimation answers who is talking, but composition also needs to weigh:

- Who is reacting dramatically while someone else speaks?
- Who still deserves attention right after they spoke?
- Who dominates the frame visually?
- Who is centered in the conversation layout?

Importance scoring turns those signals into a ranked attention model for shot composition.

## Architecture

```
TrackingResult (Module 2)
  +
SpeakerEstimationResult (Module 4, optional)
  ↓
Factor providers
  ├── Currently speaking
  ├── Facial expression
  ├── Detection confidence
  ├── Frame center
  ├── Screen presence
  ├── Recent speaker
  └── Reaction target
  ↓
FusionImportanceScorer
  ↓
ImportanceScoringResult
  └── FrameImportance[]   (ranked ImportanceScore per frame)
```

## Package layout

| Path | Purpose |
|------|---------|
| `app/reframe/models/importance.py` | `ImportanceScore`, `ImportanceScoringResult` |
| `app/reframe/importance/base.py` | `ImportanceScorer` interface |
| `app/reframe/importance/factors/` | Individual factor providers |
| `app/reframe/importance/fusion.py` | Weighted multi-factor fusion |
| `app/reframe/importance/factory.py` | Scorer factory |
| `app/reframe/importance/service.py` | `ImportanceScoringService` |

## Output schema

### `ImportanceScore`

```json
{
  "track_id": "person_1",
  "score": 0.78,
  "reasoning": "currently speaking; large screen presence",
  "factors": [
    {"factor_type": "currently_speaking", "score": 0.95},
    {"factor_type": "screen_presence", "score": 0.82}
  ]
}
```

### `ImportanceScoringResult`

```json
{
  "frames": [
    {
      "frame_number": 25,
      "timestamp": 12.5,
      "scores": [
        {
          "track_id": "person_1",
          "score": 0.78,
          "reasoning": "currently speaking; large screen presence"
        },
        {
          "track_id": "person_2",
          "score": 0.41,
          "reasoning": "recent speaker"
        }
      ]
    }
  ]
}
```

## Usage

```python
from app.reframe import estimate_active_speakers, score_importance, track_faces_in_video

tracking = track_faces_in_video("episode.mp4")
speakers = estimate_active_speakers(tracking, transcript_segments=segments, video_path="episode.mp4")
importance = score_importance(tracking, speaker_result=speakers)

for frame in importance.frames:
    top = frame.scores[0]
    print(frame.timestamp, top.track_id, top.score, top.reasoning)
```

## Factors

| Factor | What it measures | Notes |
|--------|------------------|-------|
| `currently_speaking` | Active speaker confidence | Strongest signal when available |
| `facial_expression` | Mouth movement intensity | Proxy until emotion models are added |
| `detection_confidence` | Face detector confidence | Down-weights uncertain detections |
| `frame_center` | Horizontal centrality | Helps Mafia table layouts |
| `screen_presence` | Relative face size | Larger faces score higher |
| `recent_speaker` | Time since last speech | Exponential decay |
| `reaction_target` | Central listener while others animate | Supports silent reaction shots |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `IMPORTANCE_SCORER` | `fusion` | Scorer backend |
| `IMPORTANCE_WEIGHT_SPEAKING` | `0.30` | Currently speaking weight |
| `IMPORTANCE_WEIGHT_EXPRESSION` | `0.15` | Facial expression weight |
| `IMPORTANCE_WEIGHT_DETECTION` | `0.10` | Detection confidence weight |
| `IMPORTANCE_WEIGHT_CENTER` | `0.10` | Frame center weight |
| `IMPORTANCE_WEIGHT_PRESENCE` | `0.15` | Screen presence weight |
| `IMPORTANCE_WEIGHT_RECENT_SPEAKER` | `0.10` | Recent speaker weight |
| `IMPORTANCE_WEIGHT_REACTION` | `0.10` | Reaction target weight |
| `IMPORTANCE_RECENT_SPEAKER_DECAY_SECONDS` | `3.0` | Recent speaker decay window |

## Future extension points

- Emotion recognition scores plug in as a new factor provider
- Gaze estimation can refine reaction-target scoring
- Speaker diarization can boost transcript-linked tracks directly
- Scene type heuristics (vote reveal, group laugh) can reweight factors

## Tradeoffs

- Expression scoring currently uses mouth movement as a stand-in for true emotion detection.
- Reaction targeting is heuristic and works best with 2–4 visible faces.
- Without speaker estimation, speaking and recent-speaker factors contribute zero and other factors carry the ranking.
