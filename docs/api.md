# API Reference

The Viral Clip Finder exposes a REST API built with [FastAPI](https://fastapi.tiangolo.com/). Interactive OpenAPI documentation is available at `/docs` when the server is running.

## Running the server

```bash
# Development (auto-reload when api_reload=true in .env)
uv run viral-clip-api

# Or directly via uvicorn
uv run uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | Bind address |
| `API_PORT` | `8000` | Bind port |
| `API_RELOAD` | `false` | Enable uvicorn auto-reload |
| `LOG_LEVEL` | `INFO` | Logging level |

## Endpoints

### `GET /health`

Liveness probe for orchestrators and load balancers.

**Response** `200 OK`

```json
{
  "status": "ok",
  "service": "viral-clip-finder",
  "version": "0.1.0"
}
```

## Planned endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/analyze` | Start analysis for a YouTube URL |
| `GET` | `/projects` | List analysis projects |
| `GET` | `/projects/{id}` | Project detail and status |
| `GET` | `/clips` | List clips for a project |
| `GET` | `/report` | Download analysis report |
| `POST` | `/extract` | Extract MP4 clips (optional) |

See [ROADMAP.md](ROADMAP.md) for the full delivery plan.
