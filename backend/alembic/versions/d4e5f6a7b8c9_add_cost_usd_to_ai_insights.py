"""add cost_usd column to ai_insights

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-02
"""

import sqlalchemy as sa

from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ai_insights",
        sa.Column("cost_usd", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ai_insights", "cost_usd")
