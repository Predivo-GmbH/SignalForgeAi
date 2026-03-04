"""Add TOTP 2FA fields to users table.

Revision ID: i2j3k4l5m6n7
Revises: h1i2j3k4l5m6
Create Date: 2026-03-04
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "i2j3k4l5m6n7"
down_revision = "h1i2j3k4l5m6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("totp_secret_enc", sa.LargeBinary(), nullable=True))
    op.add_column(
        "users",
        sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("users", sa.Column("backup_codes_hash", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "backup_codes_hash")
    op.drop_column("users", "totp_enabled")
    op.drop_column("users", "totp_secret_enc")
