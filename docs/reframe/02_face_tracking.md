# Module 2 — Face Tracking

Module 2 assigns persistent person identities across frames so later modules can follow speakers, reactions, and group dynamics over time.

## Why this module exists

Per-frame detection alone cannot answer:

- Who is speaking now vs. two seconds ago?
- Which face belongs to the same person after a head turn?
- Who left the frame temporarily during an occlusion?

Tracking bridges detection and composition.

## Architecture

```
FrameFaces[] (Module 1)
  ↓
FaceTracker (swappable backend)
  ↓
TrackingResult
  ├── FrameTracks[]   (per-frame tracked faces)
  └── TrackSummary{}  (per-person lifecycle)
```

## Package layout

| Path | Purpose |
|------|---------|
| `app/reframe/models/tracking.py` | `TrackedFace`, `FrameTracks`, `TrackingResult` |
| `app/reframe/tracking/base.py` | `FaceTracker` abstract interface |
| `app/reframe/tracking/iou.py` | IoU + center-distance greedy matcher |
| `app/reframe/tracking/geometry.py` | IoU and distance helpers |
| `app/reframe/tracking/factory.py` | Tracker factory |
| `app/reframe/tracking/service.py` | `FaceTrackingService` orchestrator |

## Output schema

### `TrackedFace`

```json
{
  "track_id": "person_3",
  "bounding_box": {"x": 640, "y": 120, "width": 180, "height": 220},
  "detection_confidence": 0.94,
  "association_score": 0.87,
  "landmarks": {"left_eye": [710, 180], "right_eye": [780, 182]}
}
```

### `TrackingResult`

```json
{
  "frames": [
    {
      "frame_number": 12,
      "timestamp": 6.0,
      "faces": [{"track_id": "person_1", "...": "..."}],
      "active_track_ids": ["person_1"]
    }
  ],
  "tracks": {
    "person_1": {
      "track_id": "person_1",
      "first_frame": 0,
      "last_frame": 48,
      "total_detections": 42,
      "max_consecutive_misses": 2
    }
  }
}
```

## Usage

```python
from app.reframe import detect_faces_in_video, track_faces_in_frames, track_faces_in_video

# End-to-end: detect + track
result = track_faces_in_video("clip1.mp4")

for frame in result.frames:
    for face in frame.faces:
        print(frame.timestamp, face.track_id, face.center)

# Or track precomputed detections
detections = detect_faces_in_video("clip1.mp4")
result = track_faces_in_frames(detections)
```

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `FACE_TRACKER` | `iou` | Tracker backend |
| `TRACKING_IOU_THRESHOLD` | `0.3` | Minimum IoU for association |
| `TRACKING_MAX_CENTER_DISTANCE` | `250` | Max center distance (px) fallback |
| `TRACKING_MAX_AGE` | `5` | Frames to keep a track alive without detection |

## Occlusion handling

The IoU tracker keeps a track alive for `TRACKING_MAX_AGE` frames after its last match. This tolerates:

- Brief head turns
- Partial occlusion
- Missed detections between sampled frames

When the face reappears within the max age window, it keeps the same `track_id`.

## Swappable trackers

Implement `FaceTracker` and register in `app/reframe/tracking/factory.py`.

| Backend | Status |
|---------|--------|
| `iou` | Implemented (default, no extra deps) |
| DeepSORT | Future |
| ByteTrack | Future |
| Optical flow | Future |

## Tradeoffs

| Decision | Rationale |
|----------|-----------|
| Greedy IoU matching | Simple, fast, no scipy/pytorch dependency |
| Center-distance fallback | Helps when bbox size changes between frames |
| Max-age occlusion window | Balances identity persistence vs. ghost tracks |
| Separate `TrackSummary` | Downstream modules need lifecycle stats |

## Next module

**Module 3 — Scene Detection** will identify shot boundaries so smoothing and camera planning do not bleed across hard cuts.
