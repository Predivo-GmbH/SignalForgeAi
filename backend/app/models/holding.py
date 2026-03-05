import uuid

from sqlalchemy import Float, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class ManualHolding(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "manual_holdings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    purchase_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)


class CostBasisOverride(Base, UUIDMixin, TimestampMixin):
    """Per-symbol cost basis override.

    Stores purchase price for any symbol (manual or exchange).
    Applied during holdings aggregation to compute P&L for exchange
    holdings that don't carry their own cost basis.
    """

    __tablename__ = "cost_basis_overrides"
    __table_args__ = (
        UniqueConstraint("user_id", "symbol", name="uq_cost_basis_user_symbol"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    purchase_price: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
