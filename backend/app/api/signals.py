"""Signals REST API — list, get, and on-demand generation."""

import re
import uuid

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.data.storage import CandleStorage
from app.engine.pipeline import SignalPipeline
from app.models.signal import Signal

router = APIRouter(prefix="/signals", tags=["signals"])


# ---------- Schemas ----------


class GenerateRequest(BaseModel):
    symbol: str = Field(default="BTC/USDT", max_length=20)
    timeframe: str = Field(default="1h", max_length=5)
    account_equity: float = 10000.0

    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        if not re.match(r'^[A-Z0-9]{1,10}(/[A-Z0-9]{1,10})?$', v.upper()):
            raise ValueError('Invalid symbol format. Expected format: BTC/USDT or AAPL')
        return v.upper()


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
    triggers: list[str] | None
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
    rng = np.random.default_rng(42)
    dates = pd.date_range(end=pd.Timestamp.now(), periods=n, freq="1h")
    close = 100 + np.cumsum(rng.standard_normal(n) * 0.5)
    high = close + np.abs(rng.standard_normal(n) * 0.3)
    low = close - np.abs(rng.standard_normal(n) * 0.3)
    open_ = close + rng.standard_normal(n) * 0.1
    volume = rng.integers(100, 10000, size=n).astype(float)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


# ---------- Routes ----------


@router.post("/generate", response_model=GenerateSignalResponse)
@limiter.limit("5/minute")
async def generate_signal(
    request: Request,
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
@limiter.limit("60/minute")
async def get_signal(
    request: Request,
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


_SORT_COLUMNS = {
    "created_at": Signal.created_at,
    "symbol": Signal.symbol,
    "direction": Signal.direction,
    "confluence_score": Signal.confluence_score,
    "entry_price": Signal.entry_price,
    "status": Signal.status,
    "regime": Signal.regime,
    "ai_quality_score": Signal.ai_quality_score,
}


@router.get("", response_model=SignalListResponse)
@limiter.limit("60/minute")
async def list_signals(
    request: Request,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    strategy_id: uuid.UUID | None = Query(default=None),
    symbol: str | None = Query(default=None),
    direction: str | None = Query(default=None),
    signal_status: str | None = Query(default=None, alias="status"),
    sort_by: str = Query(default="created_at"),
    sort_dir: str = Query(default="desc"),
):
    """List signals with pagination, filtering, and sorting."""
    uid = uuid.UUID(user_id)
    filters = [Signal.user_id == uid]
    if strategy_id:
        filters.append(Signal.strategy_id == strategy_id)
    if symbol:
        filters.append(Signal.symbol.ilike(f"%{symbol}%"))
    if direction:
        filters.append(func.upper(Signal.direction) == direction.upper())
    if signal_status:
        filters.append(func.lower(Signal.status) == signal_status.lower())

    count_q = select(func.count()).select_from(Signal)
    data_q = select(Signal)
    for f in filters:
        count_q = count_q.where(f)
        data_q = data_q.where(f)

    count_result = await db.execute(count_q)
    total = count_result.scalar() or 0

    sort_col = _SORT_COLUMNS.get(sort_by, Signal.created_at)
    order = sort_col.asc() if sort_dir == "asc" else sort_col.desc()

    result = await db.execute(
        data_q.order_by(order).limit(limit).offset(offset)
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
