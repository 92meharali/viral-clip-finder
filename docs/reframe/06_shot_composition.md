# Module 6 — Shot Composition

Module 6 decides what should appear in the vertical frame by classifying each moment into a shot type and computing a safe framing target.

## Why this module exists

Importance scoring ranks faces, but composition must answer editorial questions:

- Should we show one speaker or a two-shot?
- When should we widen for a group laugh or vote reveal?
- How do we keep foreheads, mouths, and eyes inside the crop?

This module converts analysis into framing intent.

## Architecture

```
TrackingResult + ImportanceScoringResult
  +
SpeakerEstimationResult (optional)
  ↓
HeuristicCompositionPlanner
  ├── Shot classification
  └── Framing target builder
  ↓
CompositionResult
  └── FrameComposition[]
```

## Shot types

| Shot type | When it triggers |
|-----------|------------------|
| `single_speaker` | One dominant participant |
| `conversation` | Two similarly important participants |
| `group_reaction` | 3+ visible faces |
| `vote_reveal` | 4+ visible faces |
| `silent_reaction` | Reaction-focus importance on a non-speaker |
| `wide_table` | No visible faces |

## Package layout

| Path | Purpose |
|------|---------|
| `app/reframe/models/composition.py` | `ShotType`, `FramingTarget`, `CompositionResult` |
| `app/reframe/composition/framing.py` | Padding, union bbox, rule-of-thirds framing |
| `app/reframe/composition/heuristics.py` | Mafia-style shot classifier |
| `app/reframe/composition/service.py` | `CompositionService` |

## Usage

```python
from app.reframe import plan_composition, score_importance, track_faces_in_video

tracking = track_faces_in_video("episode.mp4")
importance = score_importance(tracking)
composition = plan_composition(tracking, importance)

print(composition.frames[0].shot_type, composition.frames[0].reasoning)
```

## Composition rules enforced

- Minimum padding around subjects
- Extra forehead padding above faces
- Rule-of-thirds eye-line offset
- Wider zoom multipliers for group and vote-reveal shots

## Configuration

See `.env.example` for `COMPOSITION_*` settings including zoom multipliers and face-count thresholds.

## Future extension points

- Scene-aware composition resets at hard cuts
- Emotion-driven reaction shot detection
- Configurable Mafia heuristics profiles per show format
