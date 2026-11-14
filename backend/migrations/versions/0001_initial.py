"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-11-14

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "download_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("total_requests", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_download_tasks_status", "download_tasks", ["status"])

    op.create_table(
        "request_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("request_index", sa.Integer(), nullable=False),
        sa.Column("elapsed_seconds", sa.Float(), nullable=False),
        sa.Column("bytes_downloaded", sa.BigInteger(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["task_id"], ["download_tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_request_results_task_id", "request_results", ["task_id"])


def downgrade() -> None:
    op.drop_index("ix_request_results_task_id", table_name="request_results")
    op.drop_table("request_results")
    op.drop_index("ix_download_tasks_status", table_name="download_tasks")
    op.drop_table("download_tasks")
