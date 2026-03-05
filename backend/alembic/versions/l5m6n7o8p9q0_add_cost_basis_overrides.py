"""Add cost_basis_overrides table.

Revision ID: l5m6n7o8p9q0
Revises: k4l5m6n7o8p9
Create Date: 2026-03-05
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "l5m6n7o8p9q0"
down_revision = "k4l5m6n7o8p9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cost_basis_overrides",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("purchase_price", sa.Float(), nullable=False),
        sa.Column("notes", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "symbol", name="uq_cost_basis_user_symbol"),
    )
    op.create_index("ix_cost_basis_overrides_user_id", "cost_basis_overrides", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_cost_basis_overrides_user_id", table_name="cost_basis_overrides")
    op.drop_table("cost_basis_overrides")
