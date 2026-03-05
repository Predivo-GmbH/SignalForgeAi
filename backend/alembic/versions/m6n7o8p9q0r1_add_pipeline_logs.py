"""Add pipeline_logs table for engine monitoring.

Revision ID: m6n7o8p9q0r1
Revises: l5m6n7o8p9q0
Create Date: 2026-03-05
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "m6n7o8p9q0r1"
down_revision = "l5m6n7o8p9q0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pipeline_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("strategy_id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("timeframe", sa.String(10), nullable=False),
        sa.Column("action", sa.String(10), nullable=False),
        sa.Column("block_reason", sa.String(40), nullable=True),
        sa.Column("confluence_score", sa.Integer(), nullable=True),
        sa.Column("regime", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pipeline_logs_strategy_created", "pipeline_logs", ["strategy_id", "created_at"])
    op.create_index("ix_pipeline_logs_created_at", "pipeline_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_pipeline_logs_created_at", table_name="pipeline_logs")
    op.drop_index("ix_pipeline_logs_strategy_created", table_name="pipeline_logs")
    op.drop_table("pipeline_logs")
