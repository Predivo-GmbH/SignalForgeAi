"""Audit: add user_id to signals, add missing indexes."""
from alembic import op
import sqlalchemy as sa

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("signals", sa.Column("user_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_signals_user_id", "signals", "users", ["user_id"], ["id"])
    op.create_index("ix_signals_user_id", "signals", ["user_id"])
    op.create_index("ix_signals_strategy_id", "signals", ["strategy_id"])
    op.create_index("ix_signals_status", "signals", ["status"])
    op.create_index("ix_trades_user_id", "trades", ["user_id"])
    op.create_index("ix_trades_exit_time", "trades", ["exit_time"])
    op.create_index("ix_orders_status", "orders", ["status"])


def downgrade() -> None:
    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_index("ix_trades_exit_time", table_name="trades")
    op.drop_index("ix_trades_user_id", table_name="trades")
    op.drop_index("ix_signals_status", table_name="signals")
    op.drop_index("ix_signals_strategy_id", table_name="signals")
    op.drop_index("ix_signals_user_id", table_name="signals")
    op.drop_constraint("fk_signals_user_id", "signals", type_="foreignkey")
    op.drop_column("signals", "user_id")
