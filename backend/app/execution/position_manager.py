"""DB-backed position manager — replaces the old in-memory PositionManager.

All methods are static and take an ``AsyncSession`` so callers control the
transaction boundary (commit / rollback).  On close, a ``Trade`` row is
created automatically so the trade journal stays in sync.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.position import Position
from app.models.trade import Trade


class PositionManagerDB:
    """Database-backed position manager."""

    # ------------------------------------------------------------------
    # Open
    # ------------------------------------------------------------------
    @staticmethod
    async def open_position(
        db: AsyncSession,
        user_id: str,
        symbol: str,
        direction: str,
        quantity: float,
        entry_price: float,
        stop_loss: float | None,
        take_profit: float | None,
        broker: str,
        order_id: str | None = None,
        strategy_id: str | None = None,
    ) -> Position:
        """Create a new open position in the database."""
        pos = Position(
            user_id=uuid.UUID(user_id),
            order_id=uuid.UUID(order_id) if order_id else None,
            strategy_id=uuid.UUID(strategy_id) if strategy_id else None,
            symbol=symbol,
            direction=direction,
            quantity=quantity,
            entry_price=entry_price,
            current_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            original_stop_loss=stop_loss,
            unrealized_pnl=0.0,
            broker=broker,
            is_open=True,
        )
        db.add(pos)
        await db.flush()
        return pos

    # ------------------------------------------------------------------
    # Close  (also creates a Trade row)
    # ------------------------------------------------------------------
    @staticmethod
    async def close_position(
        db: AsyncSession,
        position_id: str,
        exit_price: float,
        reason: str = "manual",
    ) -> dict:
        """Close a position, update it, and create a Trade row.

        Returns a summary dict with position_id, pnl, and reason.
        Raises ``ValueError`` if no matching open position exists.
        """
        result = await db.execute(
            select(Position).where(
                Position.id == uuid.UUID(position_id),
                Position.is_open == True,  # noqa: E712
            )
        )
        pos = result.scalar_one_or_none()
        if not pos:
            raise ValueError(f"No open position found with id {position_id}")

        # --- PnL ---
        if pos.direction == "BUY":
            pnl = (exit_price - pos.entry_price) * pos.quantity
        else:
            pnl = (pos.entry_price - exit_price) * pos.quantity

        pnl = round(pnl, 2)

        # --- Close the position ---
        pos.is_open = False
        pos.closed_at = datetime.now(timezone.utc)
        pos.current_price = exit_price
        pos.unrealized_pnl = 0.0

        # --- Create a Trade record ---
        # Trade.position_size maps to the position's quantity.
        # confluence_score defaults to 0 when created from the position manager
        # (it is not available at close-time; the signal pipeline sets it).
        trade = Trade(
            user_id=pos.user_id,
            signal_id=None,
            symbol=pos.symbol,
            direction=pos.direction,
            entry_price=pos.entry_price,
            exit_price=exit_price,
            position_size=pos.quantity,
            stop_loss=pos.stop_loss or 0.0,
            take_profit=pos.take_profit or 0.0,
            pnl=pnl,
            pnl_pct=(
                round(pnl / (pos.entry_price * pos.quantity) * 100, 4)
                if pos.entry_price and pos.quantity
                else None
            ),
            confluence_score=0,
            entry_time=pos.opened_at,
            exit_time=pos.closed_at,
            exit_reason=reason,
        )
        db.add(trade)
        await db.flush()

        return {"position_id": str(pos.id), "pnl": pnl, "reason": reason}

    # ------------------------------------------------------------------
    # Trail stop
    # ------------------------------------------------------------------
    @staticmethod
    async def trail_stop(
        db: AsyncSession,
        position_id: str,
        new_stop: float,
    ) -> None:
        """Update the stop-loss on an open position."""
        result = await db.execute(
            select(Position).where(
                Position.id == uuid.UUID(position_id),
                Position.is_open == True,  # noqa: E712
            )
        )
        pos = result.scalar_one_or_none()
        if pos:
            pos.stop_loss = new_stop

    # ------------------------------------------------------------------
    # Price update
    # ------------------------------------------------------------------
    @staticmethod
    async def update_price(
        db: AsyncSession,
        position_id: str,
        current_price: float,
    ) -> None:
        """Update the current price and unrealized PnL for a position."""
        result = await db.execute(
            select(Position).where(Position.id == uuid.UUID(position_id))
        )
        pos = result.scalar_one_or_none()
        if pos and pos.is_open:
            pos.current_price = current_price
            if pos.direction == "BUY":
                pos.unrealized_pnl = round(
                    (current_price - pos.entry_price) * pos.quantity, 2
                )
            else:
                pos.unrealized_pnl = round(
                    (pos.entry_price - current_price) * pos.quantity, 2
                )

    # ------------------------------------------------------------------
    # List open
    # ------------------------------------------------------------------
    @staticmethod
    async def list_open(db: AsyncSession, user_id: str) -> list[Position]:
        """List all open positions for a user."""
        result = await db.execute(
            select(Position).where(
                Position.user_id == uuid.UUID(user_id),
                Position.is_open == True,  # noqa: E712
            )
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Get single position
    # ------------------------------------------------------------------
    @staticmethod
    async def get_position(db: AsyncSession, position_id: str) -> Position | None:
        """Fetch a single position by ID (open or closed)."""
        result = await db.execute(
            select(Position).where(Position.id == uuid.UUID(position_id))
        )
        return result.scalar_one_or_none()
