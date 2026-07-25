# Module 8 — Temporal Smoothing

Module 8 stabilizes the virtual camera path produced by Module 7.

## Goals

- Reduce camera jitter and shaking
- Limit rapid direction and zoom changes
- Damp zoom oscillation
- Never smooth across scene boundaries

## Architecture

```
CameraPath
  +
SceneDetectionResult (optional)
  ↓
EmaTemporalSmoother
  ↓
Smoothed CameraPath
```

## Algorithm

1. Split camera frames into scene segments using boundary tolerance
2. Within each segment, apply exponential moving average to center and zoom
3. Limit per-frame velocity changes using a max jerk threshold
4. Damp zoom updates when velocity sign flips

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `TEMPORAL_SMOOTHER` | `ema` | Smoother backend |
| `SMOOTHING_STRENGTH` | `0.25` | EMA factor toward new samples |
| `SMOOTHING_MAX_JERK` | `800` | Max velocity change per second |
| `SMOOTHING_ZOOM_OSCILLATION_DAMPING` | `0.5` | Zoom oscillation damping |
| `SMOOTHING_SCENE_BOUNDARY_TOLERANCE` | `0.15` | Scene split tolerance |

## Usage

```python
from app.reframe import plan_camera_path, smooth_camera_path

camera_path = plan_camera_path(composition, scene_result=scenes)
smoothed = smooth_camera_path(camera_path, scene_result=scenes)
```
