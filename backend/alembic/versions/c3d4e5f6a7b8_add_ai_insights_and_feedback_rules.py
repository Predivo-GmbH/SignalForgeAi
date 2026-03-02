"""add ai_insights and feedback_rules tables

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-02
"""

import sqlalchemy as sa

from alembic import op

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_insights",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("insight_type", sa.String(50), nullable=False),
        sa.Column(
            "signal_id", sa.Uuid(),
            sa.ForeignKey("signals.id"), nullable=True,
        ),
        sa.Column(
            "strategy_id", sa.Uuid(),
            sa.ForeignKey("strategies.id"), nullable=True,
        ),
        sa.Column(
            "user_id", sa.Uuid(),
            sa.ForeignKey("users.id"), nullable=True,
        ),
        sa.Column("symbol", sa.String(20), nullable=True),
        sa.Column("model_used", sa.String(50), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
    )

    op.create_table(
        "feedback_rules",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "strategy_id", sa.Uuid(),
            sa.ForeignKey("strategies.id"), nullable=False,
        ),
        sa.Column(
            "user_id", sa.Uuid(),
            sa.ForeignKey("users.id"), nullable=False,
        ),
        sa.Column("rule_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("conditions_json", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), default=0.5),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("source_trade_ids", sa.JSON(), nullable=True),
        sa.Column(
            "expires_at", sa.DateTime(timezone=True), nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("feedback_rules")
    op.drop_table("ai_insights")
