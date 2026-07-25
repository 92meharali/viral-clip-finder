# Database

The Viral Clip Finder persists analysis jobs, projects, and ranked clips using SQLAlchemy. SQLite is the default for development; PostgreSQL is recommended for production.

## Schema

| Table | Purpose |
|-------|---------|
| `projects` | One row per YouTube video (metadata) |
| `analysis_jobs` | Job lifecycle and analysis statistics |
| `clips` | Ranked clip results linked to a project and job |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./data/viral_clip_finder.db` | SQLAlchemy connection URL |
| `DATABASE_ECHO` | `false` | Log SQL statements |
| `DATABASE_AUTO_CREATE` | `true` | Create tables automatically on API startup |

### Examples

```bash
# SQLite (development)
DATABASE_URL=sqlite:///./data/viral_clip_finder.db

# PostgreSQL (production)
DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/viral_clip_finder
```

## Migrations

Alembic manages schema migrations.

```bash
# Apply migrations
uv run alembic upgrade head

# Create a new migration after model changes
uv run alembic revision --autogenerate -m "describe change"
```

For local development, `DATABASE_AUTO_CREATE=true` will create tables on API startup without running Alembic.

## Architecture

```
app/database/
  base.py       # SQLAlchemy declarative base
  models.py     # ProjectRecord, AnalysisJobRecord, ClipRecord
  mappers.py    # Domain ↔ ORM conversion
  session.py    # Engine and session factory

app/services/analysis/sqlalchemy_store.py
```

The `AnalysisJobStore` protocol allows tests to continue using `InMemoryAnalysisJobStore` while production uses `SqlAlchemyAnalysisJobStore`.

## Testing

Persistence tests use an in-memory SQLite database:

```bash
uv run pytest tests/test_database_persistence.py -q
```
