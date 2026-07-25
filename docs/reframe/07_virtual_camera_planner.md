# Module 7 — Virtual Camera Planner

Module 7 converts composition targets into a continuous virtual camera path with bounded pan and zoom motion.

## Why this module exists

Jumping directly to each composition target would feel robotic. The virtual camera planner simulates how a human operator would:

- Pan toward the next subject
- Zoom wider for group moments
- Reset cleanly at scene cuts
- Avoid instantaneous position jumps

## Architecture

```
CompositionResult
  +
SceneDetectionResult (optional)
  ↓
PursuitCameraPlanner
  ↓
CameraPath
  └── VirtualCameraFrame[]
```

## Output schema

### `VirtualCameraFrame`

```json
{
  "frame_number": 12,
  "timestamp": 6.0,
  "center_x": 920.5,
  "center_y": 540.0,
  "zoom": 1180.0,
  "crop_height": 2098.0,
  "velocity_x": 42.0,
  "velocity_y": -8.0,
  "zoom_velocity": 15.0
}
```

`zoom` is the crop width in source pixels. Larger values mean a wider field of view.

## Usage

```python
from app.reframe import plan_camera_path, plan_composition, score_importance, track_faces_in_video

tracking = track_faces_in_video("episode.mp4")
importance = score_importance(tracking)
composition = plan_composition(tracking, importance)
camera_path = plan_camera_path(composition)

for frame in camera_path.frames:
    print(frame.timestamp, frame.center_x, frame.zoom, frame.velocity_x)
```

## Planner behavior

The default `pursuit` planner:

1. Starts each path at the first composition target
2. Moves toward subsequent targets with max pan/zoom speed caps
3. Resets instantly at scene boundaries when `CAMERA_SCENE_RESET=true`
4. Computes velocity and acceleration from frame-to-frame deltas

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CAMERA_PLANNER` | `pursuit` | Planner backend |
| `CAMERA_MAX_PAN_SPEED` | `450` | Max pan speed in px/s |
| `CAMERA_MAX_ZOOM_SPEED` | `500` | Max crop-width change in px/s |
| `CAMERA_SMOOTHING` | `0.35` | Interpolation factor toward targets |
| `CAMERA_SCENE_RESET` | `true` | Reset at scene boundaries |
| `CAMERA_SCENE_BOUNDARY_TOLERANCE` | `0.15` | Boundary reset window in seconds |

## Future extension points

- Module 8 temporal smoothing can post-process this path
- Scene-type-specific motion profiles
- Anticipatory camera movement before speaker changes

## Tradeoffs

- Pursuit smoothing is lightweight and deterministic; Module 8 adds stronger anti-jitter filtering.
- Scene-boundary resets are instant by design so pans never bleed across hard cuts.
