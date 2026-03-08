"""Add paper portfolio tracking and USDT reserve policy to paper_simulations

Revision ID: q0r1s2t3u4v5
Revises: p9q0r1s2t3u4
Create Date: 2026-03-08
"""
from alembic import op
import sqlalchemy as sa

revision = "q0r1s2t3u4v5"
down_revision = "p9q0r1s2t3u4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "paper_simulations",
        sa.Column("paper_holdings", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "paper_simulations",
        sa.Column("usdt_reserve_pct", sa.Float(), nullable=False, server_default="0.0"),
    )
    op.add_column(
        "paper_simulations",
        sa.Column(
            "usdt_reserve_mode",
            sa.String(20),
            nullable=False,
            server_default="ai",
        ),
    )
    op.add_column(
        "paper_simulations",
        sa.Column("ai_suggested_reserve_pct", sa.Float(), nullable=True),
    )
    op.add_column(
        "paper_simulations",
        sa.Column("ai_reserve_reasoning", sa.String(2000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("paper_simulations", "ai_reserve_reasoning")
    op.drop_column("paper_simulations", "ai_suggested_reserve_pct")
    op.drop_column("paper_simulations", "usdt_reserve_mode")
    op.drop_column("paper_simulations", "usdt_reserve_pct")
    op.drop_column("paper_simulations", "paper_holdings")
