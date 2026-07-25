# Projects and Clips API

Read persisted analysis results from the database.

## Endpoints

### `GET /projects`

List analyzed YouTube projects, newest first.

| Query param | Default | Description |
|-------------|---------|-------------|
| `limit` | `20` | Page size (max 100) |
| `offset` | `0` | Pagination offset |

**Response** `200 OK`

```json
{
  "items": [
    {
      "id": "uuid",
      "video_id": "dQw4w9WgXcQ",
      "title": "Never Gonna Give You Up",
      "channel": "Rick Astley",
      "duration_seconds": 212.0,
      "webpage_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      "clip_count": 2,
      "latest_job_status": "completed",
      "created_at": "2026-07-25T00:00:00Z",
      "updated_at": "2026-07-25T00:05:00Z"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

### `GET /projects/{project_id}`

Return project metadata and ranked clips from the latest completed analysis job.

**Response** `404` if the project does not exist.

### `GET /clips`

List ranked clips with optional filters.

| Query param | Description |
|-------------|-------------|
| `project_id` | Filter by project |
| `job_id` | Filter by analysis job |
| `emotion` | Filter by emotion (case-insensitive) |
| `min_score` | Minimum viral score (0–10) |
| `limit` | Page size (default 50, max 200) |
| `offset` | Pagination offset |

## Example

```bash
curl http://localhost:8000/projects
curl http://localhost:8000/projects/<project_id>
curl "http://localhost:8000/clips?emotion=humor&min_score=7"
```

## Notes

- Projects are created when an analysis job completes successfully.
- Re-analyzing the same YouTube video updates the existing project (matched by `video_id`).
- Clip filters apply to stored database rows, not live transcript search.
