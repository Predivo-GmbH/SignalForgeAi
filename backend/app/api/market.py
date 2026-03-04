"""Market data and engine status endpoints."""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.data.storage import CandleStorage

logger = logging.getLogger(__name__)

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
    limit: int = Query(default=200, ge=1, le=1000),
    _user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return candle data for a symbol/timeframe pair.

    Symbol uses dash in URL path (BTC-USDT) and is normalised to slash (BTC/USDT).
    """
    symbol = symbol.replace("-", "/")
    candles = await CandleStorage.load_candles_db(db, symbol, timeframe, limit=limit)

    # If DB has no data, try fetching live via CCXT (Binance → KuCoin → Kraken)
    if not candles and "/" in symbol:
        from app.data.ingestion import CCXTIngestion

        for exchange_id in ("binance", "kucoin", "kraken", "mexc", "gateio"):
            try:
                ingestion = CCXTIngestion(exchange_id)
                df = ingestion.fetch_candles(symbol, timeframe, limit=limit)
                if not df.empty:
                    candles = [
                        {
                            "time": row["time"].isoformat(),
                            "open": row["open"],
                            "high": row["high"],
                            "low": row["low"],
                            "close": row["close"],
                            "volume": row["volume"],
                        }
                        for _, row in df.iterrows()
                    ]
                    break
            except Exception:
                logger.debug("Live candle fetch from %s failed for %s", exchange_id, symbol)

    # Final fallback: CoinGecko OHLC (covers virtually every listed coin)
    if not candles and "/" in symbol:
        try:
            from app.data.coingecko import fetch_ohlc

            base_symbol = symbol.split("/")[0]
            candles = await fetch_ohlc(base_symbol, timeframe)
        except Exception:
            logger.debug("CoinGecko OHLC fallback failed for %s", symbol)

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
