"""Signals REST API — list, get, and on-demand generation."""

import uuid

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.data.storage import CandleStorage
from app.engine.pipeline import SignalPipeline
from app.models.signal import Signal

router = APIRouter(prefix="/signals", tags=["signals"])


# ---------- Schemas ----------


class GenerateRequest(BaseModel):
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"
    account_equity: float = 10000.0


class SignalResponse(BaseModel):
    id: str
    symbol: str
    timeframe: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float | None
    position_size: float | None = None
    confluence_score: int
    regime: str
    triggers: dict | None
    status: str
    strategy_id: str | None = None
    created_at: str
    # AI enrichment fields
    ai_quality_score: float | None = None
    ai_reasoning: str | None = None
    ai_recommendation: str | None = None
    mtf_confidence: float | None = None
    mtf_alignment: str | None = None

    model_config = {"from_attributes": True}


class SignalListResponse(BaseModel):
    signals: list[SignalResponse]
    total: int
    limit: int
    offset: int


class GenerateSignalResponse(BaseModel):
    symbol: str
    timeframe: str
    action: str
    regime: str
    trend_direction: str
    trend_strength: float
    confluence_score: int
    triggers: list[str]
    stop_loss: float | None
    take_profit_1: float | None
    take_profit_2: float | None
    position_size: float | None
    risk_reward: float | None
    block_reason: str | None
    timestamp: str


# ---------- Helpers ----------


def _generate_synthetic_candles(n: int = 200) -> pd.DataFrame:
    """Generate synthetic OHLCV candles for pipeline testing."""
    np.random.seed(42)
    dates = pd.date_range(end=pd.Timestamp.now(), periods=n, freq="1h")
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    high = close + np.abs(np.random.randn(n) * 0.3)
    low = close - np.abs(np.random.randn(n) * 0.3)
    open_ = close + np.random.randn(n) * 0.1
    volume = np.random.randint(100, 10000, size=n).astype(float)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


# ---------- Routes ----------


@router.post("/generate", response_model=GenerateSignalResponse)
async def generate_signal(
    body: GenerateRequest | None = None,
    _user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run the SignalPipeline on real candle data and return the result.

    Uses candles from the database if available, falls back to synthetic data.
    """
    req = body or GenerateRequest()

    # Try real candles from DB first
    candle_rows = await CandleStorage.load_candles_db(
        db, req.symbol, req.timeframe, limit=300,
    )
    if len(candle_rows) >= 100:
        candles = pd.DataFrame(candle_rows)
        candles["time"] = pd.to_datetime(candles["time"])
        candles = candles.set_index("time")
    else:
        candles = _generate_synthetic_candles()

    pipeline = SignalPipeline()
    result = pipeline.process(
        symbol=req.symbol,
        timeframe=req.timeframe,
        candles=candles,
        account_equity=req.account_equity,
    )
    return GenerateSignalResponse(
        symbol=result.symbol,
        timeframe=result.timeframe,
        action=result.action,
        regime=result.regime,
        trend_direction=result.trend_direction,
        trend_strength=result.trend_strength,
        confluence_score=result.confluence_score,
        triggers=result.triggers,
        stop_loss=result.stop_loss,
        take_profit_1=result.take_profit_1,
        take_profit_2=result.take_profit_2,
        position_size=result.position_size,
        risk_reward=result.risk_reward,
        block_reason=result.block_reason,
        timestamp=result.timestamp,
    )


@router.get("/{signal_id}", response_model=SignalResponse)
async def get_signal(
    signal_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single signal by ID (scoped to the authenticated user)."""
    uid = uuid.UUID(user_id)
    result = await db.execute(
        select(Signal).where(Signal.id == signal_id, Signal.user_id == uid)
    )
    signal = result.scalar_one_or_none()
    if not signal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signal not found")
    return _signal_to_response(signal)


@router.get("", response_model=SignalListResponse)
async def list_signals(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    strategy_id: uuid.UUID | None = Query(default=None),
):
    """List signals with pagination, scoped to the authenticated user."""
    uid = uuid.UUID(user_id)
    filters = [Signal.user_id == uid]
    if strategy_id:
        filters.append(Signal.strategy_id == strategy_id)

    count_q = select(func.count()).select_from(Signal)
    data_q = select(Signal)
    for f in filters:
        count_q = count_q.where(f)
        data_q = data_q.where(f)

    count_result = await db.execute(count_q)
    total = count_result.scalar() or 0

    result = await db.execute(
        data_q.order_by(Signal.created_at.desc()).limit(limit).offset(offset)
    )
    signals = result.scalars().all()

    return SignalListResponse(
        signals=[_signal_to_response(s) for s in signals],
        total=total,
        limit=limit,
        offset=offset,
    )


def _signal_to_response(signal: Signal) -> SignalResponse:
    """Convert a Signal model to a SignalResponse."""
    return SignalResponse(
        id=str(signal.id),
        strategy_id=str(signal.strategy_id) if signal.strategy_id else None,
        symbol=signal.symbol,
        timeframe=signal.timeframe,
        direction=signal.direction,
        entry_price=signal.entry_price,
        stop_loss=signal.stop_loss,
        take_profit_1=signal.take_profit_1,
        take_profit_2=signal.take_profit_2,
        position_size=signal.position_size,
        confluence_score=signal.confluence_score,
        regime=signal.regime,
        triggers=signal.triggers,
        status=signal.status,
        created_at=signal.created_at.isoformat() if signal.created_at else "",
        ai_quality_score=signal.ai_quality_score,
        ai_reasoning=signal.ai_reasoning,
        ai_recommendation=signal.ai_recommendation,
        mtf_confidence=signal.mtf_confidence,
        mtf_alignment=signal.mtf_alignment,
    )
