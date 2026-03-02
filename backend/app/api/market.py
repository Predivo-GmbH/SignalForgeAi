"""Market data and engine status endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.data.storage import CandleStorage

router = APIRouter(tags=["market"])

SUPPORTED_SYMBOLS = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "EUR/USD",
    "GBP/USD",
    "USD/JPY",
    "SPY",
    "QQQ",
    "AAPL",
]

SUPPORTED_TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"]


@router.get("/market/symbols")
async def list_symbols():
    """Return list of supported trading symbols."""
    return SUPPORTED_SYMBOLS


@router.get("/market/candles/{symbol}/{timeframe}")
async def get_candles(
    symbol: str,
    timeframe: str,
    limit: int = Query(default=200, ge=1, le=5000),
    _user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return candle data for a symbol/timeframe pair.

    Symbol uses dash in URL path (BTC-USDT) and is normalised to slash (BTC/USDT).
    """
    symbol = symbol.replace("-", "/")
    candles = await CandleStorage.load_candles_db(db, symbol, timeframe, limit=limit)
    return {"symbol": symbol, "timeframe": timeframe, "candles": candles, "count": len(candles)}


@router.get("/engine/status")
async def engine_status(_user_id: str = Depends(get_current_user)):
    """Return current signal engine status."""
    return {
        "active": True,
        "layers": ["regime", "trend", "zones", "confluence", "triggers", "risk"],
        "supported_symbols": SUPPORTED_SYMBOLS,
        "supported_timeframes": SUPPORTED_TIMEFRAMES,
    }
