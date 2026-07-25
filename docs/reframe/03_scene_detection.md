# Module 3 — Scene Detection

Module 3 detects shot boundaries so later smoothing and virtual camera planning never bleed across hard cuts.

## Why this module exists

Mafia-style discussion videos often contain:

- Hard camera cuts between speakers
- Zoom changes during vote reveals
- Reaction shots inserted in post-production

A reframing system must know where shots change. Temporal smoothing or camera pans should **never** cross a scene boundary.

## Architecture

```
Video
  ↓
SceneDetector (swappable backend)
  ↓
SceneDetectionResult
  ├── boundaries[]   (cut timestamps)
  └── segments[]   (continuous shots)
```

## Package layout

| Path | Purpose |
|------|---------|
| `app/reframe/models/scenes.py` | `SceneBoundary`, `SceneSegment`, `SceneDetectionResult` |
| `app/reframe/scenes/base.py` | `SceneDetector` interface |
| `app/reframe/scenes/ffmpeg.py` | FFmpeg `scene` score detector |
| `app/reframe/scenes/histogram.py` | Histogram frame-difference detector |
| `app/reframe/scenes/segments.py` | Boundary merge + segment builder |
| `app/reframe/scenes/factory.py` | Detector factory |
| `app/reframe/scenes/service.py` | `SceneDetectionService` |

## Output schema

```json
{
  "source_path": "clip1.mp4",
  "duration_seconds": 40.0,
  "boundaries": [
    {"timestamp": 12.4, "confidence": 0.58, "boundary_type": "cut"}
  ],
  "segments": [
    {"index": 0, "start_seconds": 0.0, "end_seconds": 12.4, "duration_seconds": 12.4},
    {"index": 1, "start_seconds": 12.4, "end_seconds": 40.0, "duration_seconds": 27.6}
  ]
}
```

## Usage

```python
from app.reframe import detect_scenes

result = detect_scenes("clip1.mp4")

for segment in result.segments:
    print(segment.index, segment.start_seconds, segment.end_seconds)

# Check before smoothing across a timestamp
if result.is_near_boundary(12.35, tolerance=0.25):
    print("Do not smooth across this cut")
```

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `SCENE_DETECTOR` | `ffmpeg` | Backend: `ffmpeg` or `histogram` |
| `SCENE_DETECTION_THRESHOLD` | `0.35` | Sensitivity (higher = fewer cuts) |
| `SCENE_MIN_GAP_SECONDS` | `0.5` | Merge boundaries closer than this |
| `SCENE_EXTRACTION_FPS` | `4.0` | Sample rate for histogram detector |

## Backends

| Backend | Method | Best for |
|---------|--------|----------|
| `ffmpeg` | Built-in `scene` score via `showinfo` | Production use, full video |
| `histogram` | Grayscale histogram delta on sampled frames | Tests, environments without scene metadata |

## Downstream rules

Later modules must treat scene boundaries as hard stops:

- Reset virtual camera state at each boundary
- Do not interpolate crop paths across cuts
- Re-evaluate composition at the start of each segment

## Next module

**Module 4 — Active Speaker Estimation** will combine transcript timing, mouth movement, and face orientation to score who is speaking in each frame.
