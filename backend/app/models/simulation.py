"""Paper simulation models — B&H vs SignalForge live comparison.

Two portfolios tracked:
  - initial_holdings  (frozen B&H snapshot — never changes)
  - paper_holdings    (live paper portfolio — changes with every trade)

USDT reserve policy:
  - usdt_reserve_pct  controls what fraction of portfolio value stays as USDT
  - usdt_reserve_mode selects who decides: "ai" (AI Advisor), "manual", or "auto_accept"
"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class PaperSimulation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "paper_simulations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    initial_holdings: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    initial_value_usd: Mapped[float] = mapped_column(Float, nullable=False)

    # Paper portfolio — starts as copy of initial_holdings, diverges with trades.
    # Each entry: {"symbol": "BTC", "quantity": 0.5, "price_usd": 45000, "value_usd": 22500}
    paper_holdings: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)

    # USDT reserve policy
    usdt_reserve_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    usdt_reserve_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ai"
    )  # "ai" | "manual" | "auto_accept"

    # AI's latest recommendation (stored for display even when mode is "manual")
    ai_suggested_reserve_pct: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    ai_reserve_reasoning: Mapped[str | None] = mapped_column(
        String(2000), nullable=True
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    stopped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class SimulationSnapshot(Base, UUIDMixin):
    __tablename__ = "simulation_snapshots"
    __table_args__ = (
        Index("ix_simulation_snapshots_sim_time", "simulation_id", "timestamp"),
    )

    simulation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("paper_simulations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    bh_value_usd: Mapped[float] = mapped_column(Float, nullable=False)
    sf_value_usd: Mapped[float] = mapped_column(Float, nullable=False)
    sf_cash_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sf_positions_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
