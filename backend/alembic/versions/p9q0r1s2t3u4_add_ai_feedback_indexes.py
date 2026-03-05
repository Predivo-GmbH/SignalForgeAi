"""Add missing indexes on ai_insights, feedback_rules, backtest_results FK columns

Revision ID: p9q0r1s2t3u4
Revises: o8p9q0r1s2t3
Create Date: 2026-03-05
"""
from alembic import op

revision = "p9q0r1s2t3u4"
down_revision = "o8p9q0r1s2t3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ai_insights FK indexes
    op.create_index("ix_ai_insights_signal_id", "ai_insights", ["signal_id"])
    op.create_index("ix_ai_insights_strategy_id", "ai_insights", ["strategy_id"])
    op.create_index("ix_ai_insights_user_id", "ai_insights", ["user_id"])
    # ix_ai_insights_created defined in model but missing from prior migrations
    op.create_index(
        "ix_ai_insights_created", "ai_insights", ["created_at"],
        if_not_exists=True,
    )

    # feedback_rules FK indexes
    op.create_index("ix_feedback_rules_strategy_id", "feedback_rules", ["strategy_id"])
    op.create_index("ix_feedback_rules_user_id", "feedback_rules", ["user_id"])

    # backtest_results FK index
    op.create_index("ix_backtest_results_strategy_id", "backtest_results", ["strategy_id"])


def downgrade() -> None:
    op.drop_index("ix_backtest_results_strategy_id", "backtest_results")
    op.drop_index("ix_feedback_rules_user_id", "feedback_rules")
    op.drop_index("ix_feedback_rules_strategy_id", "feedback_rules")
    op.drop_index("ix_ai_insights_user_id", "ai_insights")
    op.drop_index("ix_ai_insights_strategy_id", "ai_insights")
    op.drop_index("ix_ai_insights_signal_id", "ai_insights")
