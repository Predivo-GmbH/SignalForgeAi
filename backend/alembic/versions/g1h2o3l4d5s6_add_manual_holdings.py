"""Add manual_holdings table.

Revision ID: g1h2o3l4d5s6
Revises: f1x2a3b4c5d6
Create Date: 2026-03-04
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "g1h2o3l4d5s6"
down_revision = "f1x2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "manual_holdings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("purchase_price", sa.Float(), nullable=True),
        sa.Column("notes", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_manual_holdings_user_id", "manual_holdings", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_manual_holdings_user_id", table_name="manual_holdings")
    op.drop_table("manual_holdings")
