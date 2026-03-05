"""PipelineLog model — stores every pipeline decision for monitoring."""

import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class PipelineLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "pipeline_logs"
    __table_args__ = (
        Index("ix_pipeline_logs_strategy_created", "strategy_id", "created_at"),
        Index("ix_pipeline_logs_created_at", "created_at"),
    )

    strategy_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False,
    )
    symbol: Mapped[str] = mapped_column(String(20))
    timeframe: Mapped[str] = mapped_column(String(10))
    action: Mapped[str] = mapped_column(String(10))  # BUY, SELL, NO_TRADE
    block_reason: Mapped[str | None] = mapped_column(String(40), nullable=True)
    confluence_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    regime: Mapped[str | None] = mapped_column(String(20), nullable=True)
