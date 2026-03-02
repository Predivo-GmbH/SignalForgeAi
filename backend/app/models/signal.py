"""Signal model — stores generated trading signals from the pipeline."""

import uuid

from sqlalchemy import JSON, Float, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Signal(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "signals"
    __table_args__ = (
        Index("ix_signals_user_id", "user_id"),
        Index("ix_signals_strategy_id", "strategy_id"),
        Index("ix_signals_status", "status"),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    strategy_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True
    )
    symbol: Mapped[str] = mapped_column(String(20))
    timeframe: Mapped[str] = mapped_column(String(10))
    direction: Mapped[str] = mapped_column(String(10))  # BUY, SELL
    entry_price: Mapped[float] = mapped_column(Float)
    stop_loss: Mapped[float] = mapped_column(Float)
    take_profit_1: Mapped[float] = mapped_column(Float)
    take_profit_2: Mapped[float | None] = mapped_column(Float, nullable=True)
    position_size: Mapped[float | None] = mapped_column(Float, nullable=True)
    confluence_score: Mapped[int] = mapped_column(Integer)
    regime: Mapped[str] = mapped_column(String(20))
    triggers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending, active, closed, cancelled

    # AI enrichment fields
    ai_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_recommendation: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # strong_confirm, confirm, caution, reject
    mtf_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    mtf_alignment: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # aligned, mixed, conflicting
