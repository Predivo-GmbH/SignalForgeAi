"""Market data and engine status endpoints."""

from fastapi import APIRouter

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
async def get_candles(symbol: str, timeframe: str, limit: int = 200):
    """Return candle data for a symbol/timeframe pair.

    For now returns empty candles -- real data comes from CCXT ingestion later.
    Symbol uses dash in URL path (BTC-USDT) and is normalised to slash (BTC/USDT).
    """
    symbol = symbol.replace("-", "/")
    return {"symbol": symbol, "timeframe": timeframe, "candles": [], "count": 0}


@router.get("/engine/status")
async def engine_status():
    """Return current signal engine status."""
    return {
        "active": True,
        "layers": ["regime", "trend", "zones", "confluence", "triggers", "risk"],
        "supported_symbols": SUPPORTED_SYMBOLS,
        "supported_timeframes": SUPPORTED_TIMEFRAMES,
    }
