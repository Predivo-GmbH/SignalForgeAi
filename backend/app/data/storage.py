"""In-memory candle storage for Phase 1.

Stores OHLCV DataFrames keyed by ``symbol:timeframe``.  Provides upsert-style
save (concat + dedup by time) and load with optional *limit* / *since* filters.

In Phase 3 this will be replaced by a TimescaleDB-backed implementation using
the ``Candle`` SQLAlchemy model.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd


class CandleStorage:
    """Dict-of-DataFrames candle store keyed by ``symbol:timeframe``."""

    def __init__(self) -> None:
        self._store: dict[str, pd.DataFrame] = {}

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def save_candles(self, candles: pd.DataFrame) -> int:
        """Persist *candles* with upsert semantics (dedup by time).

        Parameters
        ----------
        candles:
            DataFrame with at least the columns ``time``, ``symbol``,
            ``exchange``, ``timeframe``, and OHLCV columns.

        Returns
        -------
        int
            Number of rows in the store for the affected key **after** the
            upsert (i.e. the total unique candle count, not the delta).
        """
        if candles.empty:
            return 0

        # All rows in one call are expected to share symbol + timeframe.
        symbol = candles.iloc[0]["symbol"]
        timeframe = candles.iloc[0]["timeframe"]
        key = f"{symbol}:{timeframe}"

        existing = self._store.get(key)
        if existing is not None and not existing.empty:
            combined = pd.concat([existing, candles], ignore_index=True)
            # Keep the *last* occurrence so that newer data overwrites older.
            combined = combined.drop_duplicates(subset=["time"], keep="last")
        else:
            combined = candles.copy()

        combined = combined.sort_values("time").reset_index(drop=True)
        self._store[key] = combined
        return len(combined)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def load_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int | None = None,
        since: datetime | None = None,
    ) -> pd.DataFrame:
        """Load candles for *symbol* / *timeframe*.

        Parameters
        ----------
        symbol:
            Trading pair, e.g. ``"BTC/USDT"``.
        timeframe:
            OHLCV interval, e.g. ``"1h"``.
        limit:
            If given, return only the *limit* most-recent candles.
        since:
            If given, return only candles whose ``time >= since``.

        Returns
        -------
        pd.DataFrame
            Sorted ascending by ``time``.  Empty DataFrame when no data.
        """
        key = f"{symbol}:{timeframe}"
        df = self._store.get(key)

        if df is None or df.empty:
            return pd.DataFrame()

        result = df.copy()

        if since is not None:
            result = result[result["time"] >= since]

        if limit is not None:
            result = result.tail(limit)

        return result.reset_index(drop=True)
