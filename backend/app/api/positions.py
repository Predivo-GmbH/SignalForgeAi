"""Positions API — DB-backed position listing, closing, and account state."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.execution.position_manager import PositionManagerDB
from app.models.position import Position
from app.models.trade import Trade

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/positions", tags=["positions"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------
class ClosePositionRequest(BaseModel):
    exit_price: float = Field(..., gt=0, description="Exit price must be positive")
    reason: str = Field(default="manual_close", max_length=200)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("")
@limiter.limit("60/minute")
async def list_positions(
    request: Request,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all currently open positions for the authenticated user."""
    positions = await PositionManagerDB.list_open(db, user_id)
    return [_pos_to_dict(p) for p in positions]


@router.post("/{position_id}/close")
@limiter.limit("20/minute")
async def close_position(
    request: Request,
    position_id: str,
    body: ClosePositionRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Close an open position at the given exit price (scoped to user)."""
    try:
        result = await PositionManagerDB.close_position(
            db, position_id, body.exit_price, body.reason, user_id=user_id,
        )
        await db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/drawdown")
@limiter.limit("60/minute")
async def get_drawdown_state(
    request: Request,
    user_id: str = Depends(get_current_user),
):
    """Return current portfolio drawdown circuit breaker state."""
    try:
        from app.execution.drawdown_breaker import DrawdownBreaker

        breaker = DrawdownBreaker()
        state = await breaker.get_state(user_id)
        if state:
            return {
                "peak_equity": state.peak_equity,
                "current_equity": state.current_equity,
                "drawdown_pct": round(state.drawdown_pct * 100, 2),
                "level": state.level,
                "level_name": ["Normal", "Warning", "Halt", "Emergency"][
                    min(state.level, 3)
                ],
            }
    except Exception:
        logger.exception("Failed to compute drawdown state for user %s", user_id)
    return {
        "peak_equity": 0, "current_equity": 0,
        "drawdown_pct": 0, "level": 0, "level_name": "Normal",
    }


@router.get("/account")
@limiter.limit("60/minute")
async def account_state(
    request: Request,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return current account state aggregated from DB positions and trades.

    - **equity**: live portfolio value + sum of realised PnL from trades
    - **daily_pnl**: sum of PnL from trades closed today
    - **open_positions**: count of currently open positions
    """
    import uuid
    from datetime import date, datetime, timezone

    from app.api.holdings import (
        _enrich_holdings,
        _fetch_exchange_holdings,
        _fetch_manual_holdings,
        _fetch_prices,
    )

    uid = uuid.UUID(user_id)

    # Live portfolio value from holdings
    exchange = await _fetch_exchange_holdings(db, user_id)
    manual = await _fetch_manual_holdings(db, user_id)
    all_holdings = exchange + manual
    if all_holdings:
        unique_symbols = list({h.symbol.upper() for h in all_holdings})
        prices = await _fetch_prices(unique_symbols)
        _, portfolio_value = _enrich_holdings(all_holdings, prices)
    else:
        portfolio_value = 0.0

    # Realised PnL — lifetime sum of closed trades
    res = await db.execute(
        select(func.coalesce(func.sum(Trade.pnl), 0.0)).where(Trade.user_id == uid)
    )
    realized_pnl: float = res.scalar_one()

    # Daily PnL — trades closed today
    today_start = datetime.combine(date.today(), datetime.min.time(), tzinfo=timezone.utc)
    res = await db.execute(
        select(func.coalesce(func.sum(Trade.pnl), 0.0)).where(
            Trade.user_id == uid,
            Trade.exit_time >= today_start,
        )
    )
    daily_pnl: float = res.scalar_one()

    # Open position count
    res = await db.execute(
        select(func.count(Position.id)).where(
            Position.user_id == uid,
            Position.is_open == True,  # noqa: E712
        )
    )
    open_count: int = res.scalar_one()

    return {
        "equity": round(portfolio_value + realized_pnl, 2),
        "daily_pnl": round(daily_pnl, 2),
        "open_positions": open_count,
        "max_positions": 5,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _pos_to_dict(p: Position) -> dict:
    """Convert a Position ORM model to a JSON-serializable dict."""
    # Compute bracket_status from SL/TP presence
    if p.stop_loss and p.take_profit:
        bracket_status = "active"
    elif p.stop_loss or p.take_profit:
        bracket_status = "partial"
    else:
        bracket_status = "none"

    return {
        "id": str(p.id),
        "symbol": p.symbol,
        "direction": p.direction,
        "entry_price": p.entry_price,
        "quantity": p.quantity,
        "stop_loss": p.stop_loss,
        "take_profit": p.take_profit,
        "original_stop_loss": p.original_stop_loss,
        "is_open": p.is_open,
        "unrealized_pnl": p.unrealized_pnl,
        "current_price": p.current_price,
        "broker": p.broker,
        "bracket_status": bracket_status,
        "break_even_applied": p.break_even_applied,
        "trailing_activated": p.trailing_activated,
        "strategy_id": str(p.strategy_id) if p.strategy_id else None,
        "order_id": str(p.order_id) if p.order_id else None,
        "opened_at": p.opened_at.isoformat() if p.opened_at else None,
        "closed_at": p.closed_at.isoformat() if p.closed_at else None,
    }
