"""add risk management columns to positions

Revision ID: a1b2c3d4e5f6
Revises: 23e8e2f4176c
Create Date: 2026-03-02
"""

from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "23e8e2f4176c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "positions",
        sa.Column(
            "strategy_id",
            sa.Uuid(),
            sa.ForeignKey("strategies.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "positions",
        sa.Column("original_stop_loss", sa.Float(), nullable=True),
    )
    op.add_column(
        "positions",
        sa.Column(
            "break_even_applied",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "positions",
        sa.Column(
            "trailing_activated",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("positions", "trailing_activated")
    op.drop_column("positions", "break_even_applied")
    op.drop_column("positions", "original_stop_loss")
    op.drop_column("positions", "strategy_id")
