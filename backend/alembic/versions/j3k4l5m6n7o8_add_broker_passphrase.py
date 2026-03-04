"""Add api_passphrase_enc to broker_connections.

Revision ID: j3k4l5m6n7o8
Revises: i2j3k4l5m6n7
Create Date: 2026-03-04
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "j3k4l5m6n7o8"
down_revision = "i2j3k4l5m6n7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "broker_connections",
        sa.Column("api_passphrase_enc", sa.LargeBinary(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("broker_connections", "api_passphrase_enc")
