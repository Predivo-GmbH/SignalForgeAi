"""Positions API — DB-backed position listing, closing, and account state."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.execution.position_manager import PositionManagerDB
from app.models.position import Position
from app.models.trade import Trade

router = APIRouter(prefix="/positions", tags=["positions"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------
class ClosePositionRequest(BaseModel):
    exit_price: float
    reason: str = "manual"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("")
async def list_positions(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all currently open positions for the authenticated user."""
    positions = await PositionManagerDB.list_open(db, user_id)
    return [_pos_to_dict(p) for p in positions]


@router.post("/{position_id}/close")
async def close_position(
    position_id: str,
    body: ClosePositionRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Close an open position at the given exit price."""
    try:
        result = await PositionManagerDB.close_position(
            db, position_id, body.exit_price, body.reason,
        )
        await db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/account")
async def account_state(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return current account state aggregated from DB positions and trades.

    - **equity**: starting equity (10 000) + sum of realised PnL from trades
    - **daily_pnl**: sum of PnL from trades closed today
    - **open_positions**: count of currently open positions
    """
    import uuid
    from datetime import date, datetime, timezone

    uid = uuid.UUID(user_id)

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

    initial_equity = 10_000.0  # TODO: make per-user / configurable

    return {
        "equity": round(initial_equity + realized_pnl, 2),
        "daily_pnl": round(daily_pnl, 2),
        "open_positions": open_count,
        "max_positions": 5,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _pos_to_dict(p: Position) -> dict:
    """Convert a Position ORM model to a JSON-serializable dict."""
    return {
        "id": str(p.id),
        "symbol": p.symbol,
        "direction": p.direction,
        "entry_price": p.entry_price,
        "quantity": p.quantity,
        "stop_loss": p.stop_loss,
        "take_profit": p.take_profit,
        "is_open": p.is_open,
        "unrealized_pnl": p.unrealized_pnl,
        "current_price": p.current_price,
        "broker": p.broker,
        "order_id": str(p.order_id) if p.order_id else None,
        "opened_at": p.opened_at.isoformat() if p.opened_at else None,
        "closed_at": p.closed_at.isoformat() if p.closed_at else None,
    }
