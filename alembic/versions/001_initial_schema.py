"""Initial project persistence schema."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("video_id", sa.String(length=11), nullable=False),
        sa.Column("youtube_url", sa.String(length=2048), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("channel", sa.String(length=256), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("webpage_url", sa.String(length=2048), nullable=False),
        sa.Column("thumbnail_url", sa.String(length=2048), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("transcript_language", sa.String(length=32), nullable=True),
        sa.Column("transcript_source", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("video_id"),
    )
    op.create_index("ix_projects_video_id", "projects", ["video_id"], unique=False)

    op.create_table(
        "analysis_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=True),
        sa.Column("youtube_url", sa.String(length=2048), nullable=False),
        sa.Column("video_id", sa.String(length=11), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("top_n", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=True),
        sa.Column("progress_message", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("transcript_segments", sa.Integer(), nullable=True),
        sa.Column("candidate_windows", sa.Integer(), nullable=True),
        sa.Column("llm_windows_analyzed", sa.Integer(), nullable=True),
        sa.Column("clips_analyzed", sa.Integer(), nullable=True),
        sa.Column("clips_ranked", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analysis_jobs_project_id", "analysis_jobs", ["project_id"], unique=False)
    op.create_index("ix_analysis_jobs_status", "analysis_jobs", ["status"], unique=False)
    op.create_index("ix_analysis_jobs_video_id", "analysis_jobs", ["video_id"], unique=False)

    op.create_table(
        "clips",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("start", sa.String(length=32), nullable=False),
        sa.Column("end", sa.String(length=32), nullable=False),
        sa.Column("start_seconds", sa.Float(), nullable=False),
        sa.Column("end_seconds", sa.Float(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("viral_score", sa.Float(), nullable=False),
        sa.Column("rank_score", sa.Float(), nullable=False),
        sa.Column("emotion", sa.String(length=64), nullable=False),
        sa.Column("hook", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["analysis_jobs.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clips_job_id", "clips", ["job_id"], unique=False)
    op.create_index("ix_clips_project_id", "clips", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_clips_project_id", table_name="clips")
    op.drop_index("ix_clips_job_id", table_name="clips")
    op.drop_table("clips")
    op.drop_index("ix_analysis_jobs_video_id", table_name="analysis_jobs")
    op.drop_index("ix_analysis_jobs_status", table_name="analysis_jobs")
    op.drop_index("ix_analysis_jobs_project_id", table_name="analysis_jobs")
    op.drop_table("analysis_jobs")
    op.drop_index("ix_projects_video_id", table_name="projects")
    op.drop_table("projects")
