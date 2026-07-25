# YouTube Ingestion

Fetch video metadata and transcripts from YouTube URLs using [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Overview

The ingestion service is the first step in the analysis pipeline:

```
YouTube URL → metadata + transcript segments → candidate windows → AI analysis
```

It normalizes all subtitle formats into the shared `TranscriptSegment` model used by the rest of the application.

## Usage

### Python API

```python
from app.services.youtube import ingest_youtube_url

result = ingest_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

print(result.metadata.title)
print(result.metadata.duration_seconds)
print(len(result.segments))
print(result.segments[0].text)
```

### Supported URLs

- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/shorts/VIDEO_ID`
- `https://www.youtube.com/live/VIDEO_ID`
- Bare 11-character video IDs

## Subtitle selection

1. **Manual subtitles** are preferred over auto-generated captions.
2. Languages are matched using `YOUTUBE_PREFERRED_LANGUAGES` (default: `en,en-US,en-GB`).
3. Formats are chosen using `YOUTUBE_SUBTITLE_FORMAT_PRIORITY` (default: `vtt,srv3,json3,ttml`).

Supported subtitle parsers:

| Format | Parser |
|--------|--------|
| VTT | Existing transcript parser |
| JSON3 | Dedicated YouTube JSON3 parser |
| SRV3 / TTML | Routed through transcript parser |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `YOUTUBE_PREFERRED_LANGUAGES` | `en,en-US,en-GB` | Ordered subtitle language list |
| `YOUTUBE_SUBTITLE_FORMAT_PRIORITY` | `vtt,srv3,json3,ttml` | Preferred subtitle formats |

## Errors

| Exception | When |
|-----------|------|
| `YouTubeIngestionError` | Invalid URL, network failure, or missing metadata |
| `YouTubeTranscriptUnavailableError` | Video has no subtitles in requested languages |

## Testing

Tests use a fake client — no network calls are made in CI:

```bash
uv run pytest tests/test_youtube_ingestion.py -q
```

## Architecture

```
app/services/youtube/
  client.py       # yt-dlp wrapper (injectable)
  models.py       # YouTubeVideoMetadata, YouTubeIngestionResult
  service.py      # orchestration
  transcript.py   # subtitle parsing + track selection
  urls.py         # URL / video ID helpers
```

The `YouTubeClient` protocol allows mocking in tests and future caching layers without changing the service API.
