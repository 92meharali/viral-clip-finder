# Analysis Jobs API

The analysis jobs API accepts a YouTube URL, runs the ingestion and AI pipeline asynchronously, and exposes job status for polling.

## Flow

```
POST /analyze
    → job created (pending)
    → background worker runs pipeline
        1. YouTube ingestion (metadata + transcript)
        2. Candidate window generation
        3. AI clip analysis
        4. Ranking and deduplication
    → GET /analyze/{job_id} returns status + results
```

Jobs are stored in an in-memory store for now. The `AnalysisJobStore` protocol is designed so Redis or SQLAlchemy backends can replace it without changing route handlers.

## Endpoints

### `POST /analyze`

Queue a new analysis job.

**Request**

```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "provider": "openai",
  "top_n": 10
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `url` | yes | YouTube watch URL, short URL, or video ID |
| `provider` | no | `cursor`, `openai`, or `gemini` (defaults to `API_AI_PROVIDER`, usually `gemini`) |
| `top_n` | no | Maximum ranked clips to return |

**Response** `202 Accepted`

```json
{
  "id": "uuid",
  "status": "pending",
  "video_id": "VIDEO_ID",
  "provider": "openai",
  "result": null
}
```

### `GET /analyze/{job_id}`

Poll job status and retrieve results when complete.

**Statuses**

| Status | Meaning |
|--------|---------|
| `pending` | Queued, not started |
| `running` | Pipeline in progress |
| `completed` | Finished successfully |
| `failed` | Pipeline error (see `error`) |

While running, `stage` reports the current pipeline step:

- `ingesting`
- `generating_windows`
- `analyzing`
- `ranking`
- `finalizing`

Completed results include `llm_windows_analyzed` — the number of overlapping transcript windows sent to the LLM. See [llm_windowing.md](llm_windowing.md).

## Example

```bash
# Start analysis
curl -s -X POST http://localhost:8000/analyze \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ","provider":"openai"}'

# Poll job status
curl -s http://localhost:8000/analyze/<job_id>
```

## Provider notes

- **`openai`** — fully automated when `OPENAI_API_KEY` is configured.
- **`cursor`** — requires a pre-generated `analysis_response.json`. API jobs will fail with a clear error until manual analysis JSON is available.

For API-driven workflows, use the `openai` provider.

## Architecture

```
app/services/analysis/
  models.py     # AnalysisJob, AnalysisJobResult
  store.py      # AnalysisJobStore protocol + in-memory implementation
  pipeline.py   # ingestion → windows → analyze → rank
  service.py    # job lifecycle + background execution hook
```

Background execution uses FastAPI `BackgroundTasks` today. The `run_job` method is synchronous and can be moved to Celery/RQ workers later without API changes.
