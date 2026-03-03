"""
CCXT-based candle ingestion.
Fetches historical OHLCV data and converts to our DataFrame format.
"""

import logging

import ccxt
import pandas as pd

logger = logging.getLogger(__name__)


class CCXTIngestion:
    """Fetches candles from exchanges via CCXT."""

    def __init__(self, exchange_id: str = "binance"):
        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class({"enableRateLimit": True})

    def fetch_candles(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 500,
        since: int | None = None,
    ) -> pd.DataFrame:
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
        except Exception as e:
            logger.error("Failed to fetch candles for %s %s: %s", symbol, timeframe, e)
            raise

        if not ohlcv:
            return pd.DataFrame()

        df = pd.DataFrame(
            ohlcv, columns=["time", "open", "high", "low", "close", "volume"]
        )
        df["time"] = pd.to_datetime(df["time"], unit="ms", utc=True)
        df["symbol"] = symbol
        df["exchange"] = self.exchange.id
        df["timeframe"] = timeframe

        return df
