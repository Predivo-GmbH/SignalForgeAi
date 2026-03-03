"""Fix FK ondelete clauses and column widths.

Revision ID: f1x2a3b4c5d6
Revises: e5f6a7b8c9d0
Create Date: 2026-03-03
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "f1x2a3b4c5d6"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade():
    # Fix feedback_rules.strategy_id to be nullable
    op.alter_column("feedback_rules", "strategy_id", nullable=True)

    # Widen positions.direction
    op.alter_column("positions", "direction", type_=sa.String(10))

    # Fix FK ondelete for ai_insights
    op.drop_constraint("ai_insights_signal_id_fkey", "ai_insights", type_="foreignkey")
    op.create_foreign_key(
        "ai_insights_signal_id_fkey", "ai_insights", "signals",
        ["signal_id"], ["id"], ondelete="SET NULL",
    )

    op.drop_constraint("ai_insights_strategy_id_fkey", "ai_insights", type_="foreignkey")
    op.create_foreign_key(
        "ai_insights_strategy_id_fkey", "ai_insights", "strategies",
        ["strategy_id"], ["id"], ondelete="SET NULL",
    )

    op.drop_constraint("ai_insights_user_id_fkey", "ai_insights", type_="foreignkey")
    op.create_foreign_key(
        "ai_insights_user_id_fkey", "ai_insights", "users",
        ["user_id"], ["id"], ondelete="CASCADE",
    )

    # Fix FK ondelete for feedback_rules
    op.drop_constraint("feedback_rules_strategy_id_fkey", "feedback_rules", type_="foreignkey")
    op.create_foreign_key(
        "feedback_rules_strategy_id_fkey", "feedback_rules", "strategies",
        ["strategy_id"], ["id"], ondelete="SET NULL",
    )

    op.drop_constraint("feedback_rules_user_id_fkey", "feedback_rules", type_="foreignkey")
    op.create_foreign_key(
        "feedback_rules_user_id_fkey", "feedback_rules", "users",
        ["user_id"], ["id"], ondelete="CASCADE",
    )

    # Fix FK ondelete for signals.user_id
    op.drop_constraint("fk_signals_user_id", "signals", type_="foreignkey")
    op.create_foreign_key(
        "fk_signals_user_id", "signals", "users",
        ["user_id"], ["id"], ondelete="CASCADE",
    )


def downgrade():
    # Revert positions.direction
    op.alter_column("positions", "direction", type_=sa.String(4))

    # Revert feedback_rules.strategy_id to not nullable
    op.alter_column("feedback_rules", "strategy_id", nullable=False)

    # Revert FK constraints (drop and recreate without ondelete)
    # ai_insights
    op.drop_constraint("ai_insights_signal_id_fkey", "ai_insights", type_="foreignkey")
    op.create_foreign_key(
        "ai_insights_signal_id_fkey", "ai_insights", "signals",
        ["signal_id"], ["id"],
    )

    op.drop_constraint("ai_insights_strategy_id_fkey", "ai_insights", type_="foreignkey")
    op.create_foreign_key(
        "ai_insights_strategy_id_fkey", "ai_insights", "strategies",
        ["strategy_id"], ["id"],
    )

    op.drop_constraint("ai_insights_user_id_fkey", "ai_insights", type_="foreignkey")
    op.create_foreign_key(
        "ai_insights_user_id_fkey", "ai_insights", "users",
        ["user_id"], ["id"],
    )

    # feedback_rules
    op.drop_constraint("feedback_rules_strategy_id_fkey", "feedback_rules", type_="foreignkey")
    op.create_foreign_key(
        "feedback_rules_strategy_id_fkey", "feedback_rules", "strategies",
        ["strategy_id"], ["id"],
    )

    op.drop_constraint("feedback_rules_user_id_fkey", "feedback_rules", type_="foreignkey")
    op.create_foreign_key(
        "feedback_rules_user_id_fkey", "feedback_rules", "users",
        ["user_id"], ["id"],
    )

    # signals
    op.drop_constraint("fk_signals_user_id", "signals", type_="foreignkey")
    op.create_foreign_key(
        "fk_signals_user_id", "signals", "users",
        ["user_id"], ["id"],
    )
