"""Database engine and session management."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.database.base import Base


def _prepare_sqlite_path(database_url: str) -> None:
    """Ensure local SQLite database directories exist."""
    if not database_url.startswith("sqlite:///"):
        return

    raw_path = database_url.removeprefix("sqlite:///")
    if raw_path in {":memory:", ""}:
        return

    db_path = Path(raw_path)
    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)


def create_engine_from_settings(settings: Settings | None = None) -> Engine:
    """Create a SQLAlchemy engine from application settings."""
    resolved = settings or get_settings()
    _prepare_sqlite_path(resolved.database_url)
    is_sqlite = resolved.database_url.startswith("sqlite")
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    return create_engine(
        resolved.database_url,
        echo=resolved.database_echo,
        future=True,
        connect_args=connect_args,
    )


class Database:
    """Application database wrapper."""

    def __init__(self, settings: Settings | None = None, *, engine: Engine | None = None) -> None:
        self.settings = settings or get_settings()
        self.engine = engine or create_engine_from_settings(self.settings)
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    def create_tables(self) -> None:
        """Create all tables (development and tests)."""
        Base.metadata.create_all(self.engine)

    def drop_tables(self) -> None:
        """Drop all tables (testing helper)."""
        Base.metadata.drop_all(self.engine)

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Provide a transactional database session."""
        db_session = self.session_factory()
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise
        finally:
            db_session.close()
