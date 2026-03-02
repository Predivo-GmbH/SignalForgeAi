"""add AI enrichment columns to signals

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-02
"""

import sqlalchemy as sa

from alembic import op

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "signals",
        sa.Column("ai_quality_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "signals",
        sa.Column("ai_reasoning", sa.Text(), nullable=True),
    )
    op.add_column(
        "signals",
        sa.Column("ai_recommendation", sa.String(20), nullable=True),
    )
    op.add_column(
        "signals",
        sa.Column("mtf_confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "signals",
        sa.Column("mtf_alignment", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("signals", "mtf_alignment")
    op.drop_column("signals", "mtf_confidence")
    op.drop_column("signals", "ai_recommendation")
    op.drop_column("signals", "ai_reasoning")
    op.drop_column("signals", "ai_quality_score")
