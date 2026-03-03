"""AI Insight and Feedback Rule models."""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class AIInsight(Base, UUIDMixin, TimestampMixin):
    """Audit trail for all AI-generated analysis."""

    __tablename__ = "ai_insights"
    __table_args__ = (
        Index("ix_ai_insights_created", "created_at"),
    )

    insight_type: Mapped[str] = mapped_column(String(50))
    # Types: signal_quality, risk_tuning, trade_feedback,
    #        multi_tf_analysis, pattern_aggregation

    # Context references (nullable — not all types need all)
    signal_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("signals.id", ondelete="SET NULL"), nullable=True
    )
    strategy_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    symbol: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # AI output
    model_used: Mapped[str] = mapped_column(String(50))
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Metrics
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)


class FeedbackRule(Base, UUIDMixin, TimestampMixin):
    """Learned trading rules synthesized from trade history analysis."""

    __tablename__ = "feedback_rules"

    strategy_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE")
    )
    rule_type: Mapped[str] = mapped_column(String(50))
    # Types: avoid_pattern, prefer_pattern, adjust_param, filter_condition
    description: Mapped[str] = mapped_column(Text)
    conditions_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    source_trade_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
