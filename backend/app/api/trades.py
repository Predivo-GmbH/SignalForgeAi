"""Trades REST API — list, get, and aggregate stats."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.models.signal import Signal
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
    strategy_id: uuid.UUID | None = Query(default=None),
):
    """Aggregate trade statistics for the authenticated user."""
    uid = uuid.UUID(user_id)

    # Total trade count (including open)
    count_q = select(func.count()).select_from(Trade).where(Trade.user_id == uid)
    if strategy_id:
        count_q = count_q.join(Signal, Trade.signal_id == Signal.id).where(
            Signal.strategy_id == strategy_id
        )
    count_result = await db.execute(count_q)
    total = count_result.scalar() or 0

    # SQL aggregates for closed trades (pnl IS NOT NULL)
    agg_q = select(
        func.count(Trade.id).label("closed_count"),
        func.sum(case((Trade.pnl > 0, 1), else_=0)).label("wins"),
        func.sum(case((Trade.pnl > 0, Trade.pnl), else_=0)).label("gross_profit"),
        func.sum(case((Trade.pnl < 0, func.abs(Trade.pnl)), else_=0)).label("gross_loss"),
        func.max(Trade.pnl).label("best"),
        func.min(Trade.pnl).label("worst"),
        func.sum(Trade.pnl).label("total_pnl"),
    ).where(
        Trade.user_id == uid,
        Trade.pnl.isnot(None),
    )
    if strategy_id:
        agg_q = agg_q.join(Signal, Trade.signal_id == Signal.id).where(
            Signal.strategy_id == strategy_id
        )

    result = await db.execute(agg_q)
    row = result.one()

    closed_count = row.closed_count or 0
    if closed_count == 0:
        return TradeStatsResponse(
            total_trades=total,
            win_rate=0.0,
            profit_factor=0.0,
            total_pnl=0.0,
            avg_pnl=0.0,
            best_trade=0.0,
            worst_trade=0.0,
        )

    wins = row.wins or 0
    gross_profit = float(row.gross_profit or 0)
    gross_loss = float(row.gross_loss or 0)
    total_pnl = float(row.total_pnl or 0)
    best = float(row.best or 0)
    worst = float(row.worst or 0)

    win_rate = round(wins / closed_count * 100, 2)
    profit_factor = (
        round(gross_profit / gross_loss, 2) if gross_loss > 0
        else 999.99 if gross_profit > 0
        else 0.0
    )

    return TradeStatsResponse(
        total_trades=total,
        win_rate=win_rate,
        profit_factor=profit_factor,
        total_pnl=round(total_pnl, 2),
        avg_pnl=round(total_pnl / closed_count, 2),
        best_trade=round(best, 2),
        worst_trade=round(worst, 2),
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
    strategy_id: uuid.UUID | None = Query(default=None),
):
    """List trades for the authenticated user with pagination."""
    uid = uuid.UUID(user_id)

    count_q = select(func.count()).select_from(Trade).where(Trade.user_id == uid)
    data_q = select(Trade).where(Trade.user_id == uid)

    if strategy_id:
        count_q = count_q.join(Signal, Trade.signal_id == Signal.id).where(
            Signal.strategy_id == strategy_id
        )
        data_q = data_q.join(Signal, Trade.signal_id == Signal.id).where(
            Signal.strategy_id == strategy_id
        )

    count_result = await db.execute(count_q)
    total = count_result.scalar() or 0

    result = await db.execute(
        data_q.order_by(Trade.created_at.desc()).limit(limit).offset(offset)
    )
    trades = result.scalars().all()

    return TradeListResponse(
        trades=[_trade_to_response(t) for t in trades],
        total=total,
        limit=limit,
        offset=offset,
    )
