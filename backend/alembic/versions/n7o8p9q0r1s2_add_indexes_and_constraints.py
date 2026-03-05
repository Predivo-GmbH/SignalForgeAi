"""Add missing indexes and check constraints.

Revision ID: n7o8p9q0r1s2
Revises: m6n7o8p9q0r1
Create Date: 2026-03-05 12:00:00.000000
"""
from alembic import op

revision = "n7o8p9q0r1s2"
down_revision = "m6n7o8p9q0r1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add index on broker_connections.user_id for faster user-scoped queries
    op.create_index(
        "ix_broker_connections_user_id",
        "broker_connections",
        ["user_id"],
    )

    # Add composite index on orders for status+time queries
    op.create_index(
        "ix_orders_status_created",
        "orders",
        ["status", "created_at"],
    )

    # Add check constraints for data validation
    op.create_check_constraint(
        "ck_positions_quantity_positive",
        "positions",
        "quantity > 0",
    )
    op.create_check_constraint(
        "ck_positions_entry_price_positive",
        "positions",
        "entry_price > 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_positions_entry_price_positive", "positions", type_="check")
    op.drop_constraint("ck_positions_quantity_positive", "positions", type_="check")
    op.drop_index("ix_orders_status_created", "orders")
    op.drop_index("ix_broker_connections_user_id", "broker_connections")
