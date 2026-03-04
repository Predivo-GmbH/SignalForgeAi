"""Add purpose column to broker_connections.

Revision ID: h1i2j3k4l5m6
Revises: g1h2o3l4d5s6
Create Date: 2026-03-04
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "h1i2j3k4l5m6"
down_revision = "g1h2o3l4d5s6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "broker_connections",
        sa.Column("purpose", sa.String(10), nullable=False, server_default="read"),
    )


def downgrade() -> None:
    op.drop_column("broker_connections", "purpose")
