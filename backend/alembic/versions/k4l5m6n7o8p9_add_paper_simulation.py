"""Add paper_simulations and simulation_snapshots tables.

Revision ID: k4l5m6n7o8p9
Revises: j3k4l5m6n7o8
Create Date: 2026-03-04
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "k4l5m6n7o8p9"
down_revision = "j3k4l5m6n7o8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paper_simulations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("strategy_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("initial_holdings", sa.JSON(), nullable=False),
        sa.Column("initial_value_usd", sa.Float(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_paper_simulations_user_id", "paper_simulations", ["user_id"])

    op.create_table(
        "simulation_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("simulation_id", sa.Uuid(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("bh_value_usd", sa.Float(), nullable=False),
        sa.Column("sf_value_usd", sa.Float(), nullable=False),
        sa.Column("sf_cash_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("sf_positions_value", sa.Float(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["simulation_id"], ["paper_simulations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_simulation_snapshots_simulation_id", "simulation_snapshots", ["simulation_id"])


def downgrade() -> None:
    op.drop_index("ix_simulation_snapshots_simulation_id", table_name="simulation_snapshots")
    op.drop_table("simulation_snapshots")
    op.drop_index("ix_paper_simulations_user_id", table_name="paper_simulations")
    op.drop_table("paper_simulations")
