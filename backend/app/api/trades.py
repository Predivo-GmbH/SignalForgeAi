"""Trades REST API — list, get, and aggregate stats."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.models.trade import Trade

router = APIRouter(prefix="/trades", tags=["trades"])


# ---------- Schemas ----------


class TradeResponse(BaseModel):
    id: str
    signal_id: str | None
    user_id: str
    symbol: str
    direction: str
    entry_price: float
    exit_price: float | None
    position_size: float
    stop_loss: float
    take_profit: float
    pnl: float | None
    pnl_pct: float | None
    risk_reward: float | None
    confluence_score: int
    entry_time: str | None
    exit_time: str | None
    exit_reason: str | None
    broker_order_id: str | None
    metadata_json: dict | None
    created_at: str

    model_config = {"from_attributes": True}


class TradeListResponse(BaseModel):
    trades: list[TradeResponse]
    total: int
    limit: int
    offset: int


class TradeStatsResponse(BaseModel):
    total_trades: int
    win_rate: float
    profit_factor: float
    total_pnl: float
    avg_pnl: float
    best_trade: float
    worst_trade: float


# ---------- Helpers ----------


def _trade_to_response(t: Trade) -> TradeResponse:
    return TradeResponse(
        id=str(t.id),
        signal_id=str(t.signal_id) if t.signal_id else None,
        user_id=str(t.user_id),
        symbol=t.symbol,
        direction=t.direction,
        entry_price=t.entry_price,
        exit_price=t.exit_price,
        position_size=t.position_size,
        stop_loss=t.stop_loss,
        take_profit=t.take_profit,
        pnl=t.pnl,
        pnl_pct=t.pnl_pct,
        risk_reward=t.risk_reward,
        confluence_score=t.confluence_score,
        entry_time=t.entry_time.isoformat() if t.entry_time else None,
        exit_time=t.exit_time.isoformat() if t.exit_time else None,
        exit_reason=t.exit_reason,
        broker_order_id=t.broker_order_id,
        metadata_json=t.metadata_json,
        created_at=t.created_at.isoformat() if t.created_at else "",
    )


# ---------- Routes ----------


@router.get("/stats", response_model=TradeStatsResponse)
async def trade_stats(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate trade statistics for the authenticated user."""
    uid = uuid.UUID(user_id)

    # Get all closed trades (those with pnl set)
    result = await db.execute(
        select(Trade).where(Trade.user_id == uid, Trade.pnl.isnot(None))
    )
    closed_trades = result.scalars().all()

    # Also count total trades (including open)
    count_result = await db.execute(
        select(func.count()).select_from(Trade).where(Trade.user_id == uid)
    )
    total = count_result.scalar() or 0

    if not closed_trades:
        return TradeStatsResponse(
            total_trades=total,
            win_rate=0.0,
            profit_factor=0.0,
            total_pnl=0.0,
            avg_pnl=0.0,
            best_trade=0.0,
            worst_trade=0.0,
        )

    pnls = [t.pnl for t in closed_trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    total_pnl = sum(pnls)
    win_rate = round(len(wins) / len(closed_trades) * 100, 2) if closed_trades else 0.0
    profit_factor = (
        round(sum(wins) / abs(sum(losses)), 2) if losses else float("inf") if wins else 0.0
    )

    return TradeStatsResponse(
        total_trades=total,
        win_rate=win_rate,
        profit_factor=profit_factor,
        total_pnl=round(total_pnl, 2),
        avg_pnl=round(total_pnl / len(closed_trades), 2),
        best_trade=round(max(pnls), 2),
        worst_trade=round(min(pnls), 2),
    )


@router.get("/{trade_id}", response_model=TradeResponse)
async def get_trade(
    trade_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single trade by ID, scoped to the authenticated user."""
    uid = uuid.UUID(user_id)
    result = await db.execute(
        select(Trade).where(Trade.id == trade_id, Trade.user_id == uid)
    )
    trade = result.scalar_one_or_none()
    if not trade:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found")
    return _trade_to_response(trade)


@router.get("", response_model=TradeListResponse)
async def list_trades(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List trades for the authenticated user with pagination."""
    uid = uuid.UUID(user_id)

    count_result = await db.execute(
        select(func.count()).select_from(Trade).where(Trade.user_id == uid)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Trade)
        .where(Trade.user_id == uid)
        .order_by(Trade.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    trades = result.scalars().all()

    return TradeListResponse(
        trades=[_trade_to_response(t) for t in trades],
        total=total,
        limit=limit,
        offset=offset,
    )
