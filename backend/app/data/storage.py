"""
Candle storage -- writes to TimescaleDB in production, in-memory for tests/CLI.
"""

from datetime import datetime

import pandas as pd


class CandleStorage:
    """In-memory candle storage. Production version will use TimescaleDB via SQLAlchemy."""

    def __init__(self):
        self._store: dict[str, pd.DataFrame] = {}

    def _key(self, symbol: str, timeframe: str) -> str:
        return f"{symbol}:{timeframe}"

    def save_candles(self, candles: pd.DataFrame) -> int:
        if candles.empty:
            return 0

        symbol = candles["symbol"].iloc[0]
        timeframe = candles["timeframe"].iloc[0]
        key = self._key(symbol, timeframe)

        if key in self._store:
            existing = self._store[key]
            combined = pd.concat([existing, candles]).drop_duplicates(
                subset=["time"], keep="last"
            )
            combined = combined.sort_values("time").reset_index(drop=True)
            self._store[key] = combined
        else:
            self._store[key] = candles.sort_values("time").reset_index(drop=True)

        return len(candles)

    def load_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int | None = None,
        since: datetime | None = None,
    ) -> pd.DataFrame:
        key = self._key(symbol, timeframe)
        if key not in self._store:
            return pd.DataFrame()

        df = self._store[key]

        if since:
            df = df[df["time"] >= since]

        if limit:
            df = df.tail(limit)

        return df.reset_index(drop=True)
