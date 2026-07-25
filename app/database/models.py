"""SQLAlchemy ORM models for project persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


def utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(UTC)


class ProjectRecord(Base):
    """Persistent YouTube video project."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    video_id: Mapped[str] = mapped_column(String(11), unique=True, index=True)
    youtube_url: Mapped[str] = mapped_column(String(2048))
    title: Mapped[str] = mapped_column(String(512))
    channel: Mapped[str | None] = mapped_column(String(256), nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    webpage_url: Mapped[str] = mapped_column(String(2048))
    thumbnail_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript_language: Mapped[str | None] = mapped_column(String(32), nullable=True)
    transcript_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    jobs: Mapped[list[AnalysisJobRecord]] = relationship(back_populates="project")
    clips: Mapped[list[ClipRecord]] = relationship(back_populates="project")


class AnalysisJobRecord(Base):
    """Persistent analysis job state."""

    __tablename__ = "analysis_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("projects.id"),
        nullable=True,
        index=True,
    )
    youtube_url: Mapped[str] = mapped_column(String(2048))
    video_id: Mapped[str | None] = mapped_column(String(11), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(64))
    top_n: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    progress_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript_segments: Mapped[int | None] = mapped_column(Integer, nullable=True)
    candidate_windows: Mapped[int | None] = mapped_column(Integer, nullable=True)
    llm_windows_analyzed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    clips_analyzed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    clips_ranked: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped[ProjectRecord | None] = relationship(back_populates="jobs")
    clips: Mapped[list[ClipRecord]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )


class ClipRecord(Base):
    """Persistent ranked clip from an analysis job."""

    __tablename__ = "clips"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_jobs.id"), index=True)
    rank: Mapped[int] = mapped_column(Integer)
    start: Mapped[str] = mapped_column(String(32))
    end: Mapped[str] = mapped_column(String(32))
    start_seconds: Mapped[float] = mapped_column(Float)
    end_seconds: Mapped[float] = mapped_column(Float)
    duration_seconds: Mapped[float] = mapped_column(Float)
    viral_score: Mapped[float] = mapped_column(Float)
    rank_score: Mapped[float] = mapped_column(Float)
    emotion: Mapped[str] = mapped_column(String(64))
    hook: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)

    project: Mapped[ProjectRecord] = relationship(back_populates="clips")
    job: Mapped[AnalysisJobRecord] = relationship(back_populates="clips")
