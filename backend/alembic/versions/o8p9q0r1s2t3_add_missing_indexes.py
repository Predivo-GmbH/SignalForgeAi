"""Add missing indexes and constraints

Revision ID: o8p9q0r1s2t3
Revises: n7o8p9q0r1s2
Create Date: 2026-03-05
"""
from alembic import op

revision = "o8p9q0r1s2t3"
down_revision = "n7o8p9q0r1s2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # FK indexes
    op.create_index("ix_orders_signal_id", "orders", ["signal_id"])
    op.create_index("ix_positions_strategy_id", "positions", ["strategy_id"])
    op.create_index("ix_trades_signal_id", "trades", ["signal_id"])

    # Composite indexes from model __table_args__ missing in migrations
    op.create_index("ix_trades_symbol", "trades", ["symbol"])
    op.create_index("ix_trades_user_exit", "trades", ["user_id", "exit_time"])
    op.create_index(
        "ix_signals_dedup", "signals",
        ["strategy_id", "symbol", "timeframe", "direction", "status"]
    )

    # SimulationSnapshot composite index
    op.create_index(
        "ix_simulation_snapshots_sim_time", "simulation_snapshots",
        ["simulation_id", "timestamp"]
    )

    # Unique constraint to prevent double position open from race condition
    op.create_unique_constraint("uq_position_order_id", "positions", ["order_id"])


def downgrade() -> None:
    op.drop_constraint("uq_position_order_id", "positions", type_="unique")
    op.drop_index("ix_simulation_snapshots_sim_time", "simulation_snapshots")
    op.drop_index("ix_signals_dedup", "signals")
    op.drop_index("ix_trades_user_exit", "trades")
    op.drop_index("ix_trades_symbol", "trades")
    op.drop_index("ix_trades_signal_id", "trades")
    op.drop_index("ix_positions_strategy_id", "positions")
    op.drop_index("ix_orders_signal_id", "orders")
