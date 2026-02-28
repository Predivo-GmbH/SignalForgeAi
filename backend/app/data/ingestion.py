"""
CCXT-based candle ingestion.
Fetches historical OHLCV data and converts to our DataFrame format.
"""

import ccxt
import pandas as pd


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
        ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)

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
