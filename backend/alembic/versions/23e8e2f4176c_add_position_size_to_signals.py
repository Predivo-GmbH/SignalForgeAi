"""add position_size to signals

Revision ID: 23e8e2f4176c
Revises:
Create Date: 2026-03-02
"""

from alembic import op
import sqlalchemy as sa

revision = "23e8e2f4176c"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("signals", sa.Column("position_size", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("signals", "position_size")
