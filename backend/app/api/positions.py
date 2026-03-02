"""Positions API — DB-backed position listing, closing, and account state."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.execution.position_manager import PositionManagerDB
from app.models.position import Position
from app.models.trade import Trade

logger = logging.getLogger(__name__)

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
    """Close an open position at the given exit price (scoped to user)."""
    try:
        result = await PositionManagerDB.close_position(
            db, position_id, body.exit_price, body.reason, user_id=user_id,
        )
        await db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/correlations")
async def get_correlations(
    user_id: str = Depends(get_current_user),
):
    """Return current correlation matrix and alerts for open positions."""
    try:
        from app.execution.correlation_monitor import CorrelationMonitor

        monitor = CorrelationMonitor()
        result = await monitor.get_cached_result(user_id)
        if result:
            return {
                "matrix": result.matrix,
                "alerts": [
                    {
                        "symbol_a": a.symbol_a,
                        "symbol_b": a.symbol_b,
                        "correlation": a.correlation,
                        "risk_level": a.risk_level,
                    }
                    for a in result.alerts
                ],
                "max_correlation": result.max_correlation,
                "exposure_penalty": result.exposure_penalty,
            }
    except Exception:
        logger.exception("Failed to compute correlations for user %s", user_id)
    return {"matrix": {}, "alerts": [], "max_correlation": 0, "exposure_penalty": 1.0}


@router.get("/drawdown")
async def get_drawdown_state(
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


@router.get("/cppi")
async def get_cppi_state(
    user_id: str = Depends(get_current_user),
):
    """Return current CPPI (portfolio insurance) state."""
    try:
        from app.execution.cppi import CPPIManager

        cppi = CPPIManager()
        state = await cppi.get_state(user_id)
        if state:
            return {
                "floor": state.floor,
                "peak_equity": state.peak_equity,
                "exposure_pct": round(state.current_exposure_pct * 100, 2),
                "cushion": state.cushion,
                "multiplier": state.multiplier,
                "max_drawdown_pct": round(state.max_drawdown_pct * 100, 2),
            }
    except Exception:
        logger.exception("Failed to compute CPPI state for user %s", user_id)
    return {
        "floor": 0, "peak_equity": 0, "exposure_pct": 100,
        "cushion": 0, "multiplier": 3.0, "max_drawdown_pct": 15,
    }


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

    # Pull account equity from user's active strategy config, fallback to 10k
    from app.models.strategy import Strategy

    strat_res = await db.execute(
        select(Strategy.config).where(
            Strategy.user_id == uid, Strategy.is_active == True  # noqa: E712
        ).limit(1)
    )
    strat_cfg = strat_res.scalar_one_or_none() or {}
    initial_equity = float(strat_cfg.get("account_equity", 10_000.0))

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
