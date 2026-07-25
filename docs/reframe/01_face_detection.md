# Module 1 — Face Detection

Phase X introduces an intelligent reframing pipeline to replace simple center cropping. Module 1 detects faces in every sampled video frame.

## Why this module exists

Vertical cropping cannot make composition decisions without knowing where faces are. Face detection is the foundation for tracking, speaker estimation, shot composition, and virtual camera planning.

## Architecture

```
Video
  ↓
FrameExtractor (ffmpeg fps sampling)
  ↓
FaceDetector (swappable backend)
  ↓
FrameFaces[]
```

## Package layout

| Path | Purpose |
|------|---------|
| `app/reframe/models/faces.py` | `BoundingBox`, `DetectedFace`, `FrameFaces`, `VideoFrame` |
| `app/reframe/detection/base.py` | `FaceDetector` abstract interface |
| `app/reframe/detection/mediapipe.py` | MediaPipe implementation |
| `app/reframe/detection/factory.py` | Detector factory |
| `app/reframe/detection/service.py` | `FaceDetectionService` orchestrator |
| `app/reframe/frames/extractor.py` | FFmpeg frame extraction |
| `app/reframe/future/vision.py` | Future vision module interfaces |

## Output schema

### `FrameFaces`

```json
{
  "frame_number": 12,
  "timestamp": 6.0,
  "image_width": 1920,
  "image_height": 1080,
  "faces": [
    {
      "id": "frame12_face0",
      "bounding_box": {"x": 640, "y": 120, "width": 180, "height": 220},
      "confidence": 0.94,
      "landmarks": {
        "left_eye": [710, 180],
        "right_eye": [780, 182],
        "nose": [745, 210],
        "mouth": [742, 250]
      }
    }
  ]
}
```

Each face includes:

- `id` — temporary per-frame id (persistent tracking arrives in Module 2)
- `bounding_box` — pixel coordinates
- `center` — derived from bounding box
- `confidence` — detector score
- `landmarks` — eye and mouth positions when available

## Usage

```python
from app.reframe import FaceDetectionService, detect_faces_in_video

# Full video analysis
results = detect_faces_in_video("clip1.mp4")

for frame in results:
    print(frame.timestamp, frame.face_count)
    for face in frame.faces:
        print(face.center, face.confidence)

# Single frame
service = FaceDetectionService()
frame = service.detect_frame("frame_000001.jpg")
```

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `FACE_DETECTOR` | `mediapipe` | Detector backend |
| `FACE_DETECTION_MIN_CONFIDENCE` | `0.5` | Minimum confidence |
| `FACE_EXTRACTION_FPS` | `2.0` | Frames sampled per second |
| `MINIMUM_FACE_SIZE` | `40` | Minimum bbox size in pixels |

Install vision dependencies:

```bash
uv sync --extra vision
```

## Swappable detectors

Implement `FaceDetector` and register in `app/reframe/detection/factory.py`.

Planned backends:

- MediaPipe (implemented)
- YOLO (future)
- RetinaFace (future)

The pipeline only depends on `FaceDetector.detect()` — not on any specific SDK.

## Future extension points

`app/reframe/future/vision.py` defines interfaces for:

- Emotion recognition
- Gaze estimation
- Hand gesture detection
- Object detection
- Micro-expression detection

These will feed importance scoring in later modules.

## Tradeoffs

| Decision | Rationale |
|----------|-----------|
| FFmpeg frame extraction | Reuses existing video stack; no OpenCV dependency |
| MediaPipe first | Fast CPU inference, good landmarks, easy local install |
| Optional `vision` extra | Keeps base install lightweight |
| 2 fps default sampling | Balance between accuracy and processing time |

## Next module

**Module 2 — Face Tracking** will assign persistent track IDs across frames using DeepSORT, ByteTrack, or optical flow.
