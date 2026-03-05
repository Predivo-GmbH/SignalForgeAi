"""
DB-backed candle storage using the Candle SQLAlchemy model.

Provides static async methods for saving/loading candles to/from the database.
Also retains a lightweight in-memory fallback for CLI and test use.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession


MAX_MEMORY_ENTRIES = 100


class CandleStorage:
    """Database-backed candle storage using the Candle model.

    All DB methods are static and require an ``AsyncSession``.
    The legacy in-memory interface is preserved for backward compatibility
    with tests and CLI tooling that instantiate ``CandleStorage()`` directly.
    """

    # ------------------------------------------------------------------
    # Legacy in-memory interface (backward-compat for tests / CLI)
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        self._store: dict[str, pd.DataFrame] = {}

    def _key(self, symbol: str, timeframe: str) -> str:
        return f"{symbol}:{timeframe}"

    def save_candles(self, candles: pd.DataFrame) -> int:
        """Save candles to in-memory store (legacy sync interface)."""
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

        # Evict oldest entries if over limit
        while len(self._store) > MAX_MEMORY_ENTRIES:
            oldest_key = next(iter(self._store))
            del self._store[oldest_key]

        return len(candles)

    def load_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int | None = None,
        since: datetime | None = None,
    ) -> pd.DataFrame:
        """Load candles from in-memory store (legacy sync interface)."""
        key = self._key(symbol, timeframe)
        if key not in self._store:
            return pd.DataFrame()

        df = self._store[key]

        if since:
            df = df[df["time"] >= since]

        if limit:
            df = df.tail(limit)

        return df.reset_index(drop=True)

    # ------------------------------------------------------------------
    # DB-backed async interface
    # ------------------------------------------------------------------

    @staticmethod
    async def save_candles_db(
        db: AsyncSession,
        symbol: str,
        timeframe: str,
        candles_df: pd.DataFrame,
        exchange: str = "default",
    ) -> int:
        """Bulk upsert candles into the Candle table.

        Args:
            db: async database session
            symbol: e.g. "BTC/USDT"
            timeframe: e.g. "1h"
            candles_df: DataFrame with columns [time, open, high, low, close, volume]
                        Optional columns: exchange, vwap, trades
            exchange: fallback exchange name when not in DataFrame

        Returns:
            Number of candles saved
        """
        from app.models.candle import Candle

        if candles_df.empty:
            return 0

        has_exchange_col = "exchange" in candles_df.columns
        has_vwap = "vwap" in candles_df.columns
        has_trades = "trades" in candles_df.columns

        rows = []
        for _, row in candles_df.iterrows():
            r = {
                "symbol": symbol,
                "timeframe": timeframe,
                "time": row["time"],
                "exchange": row["exchange"] if has_exchange_col else exchange,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
                "vwap": float(row["vwap"]) if has_vwap and pd.notna(row.get("vwap")) else None,
                "trades": (
                    int(row["trades"])
                    if has_trades and pd.notna(row.get("trades"))
                    else None
                ),
            }
            rows.append(r)

        stmt = pg_insert(Candle).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["time", "symbol", "exchange", "timeframe"],
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
                "vwap": stmt.excluded.vwap,
                "trades": stmt.excluded.trades,
            },
        )
        await db.execute(stmt)
        return len(rows)

    @staticmethod
    async def load_candles_db(
        db: AsyncSession,
        symbol: str,
        timeframe: str,
        limit: int = 500,
        since: datetime | None = None,
        exchange: str | None = None,
    ) -> list[dict]:
        """Query candles from DB, return as list of dicts.

        Returns list of dicts with keys:
            time, open, high, low, close, volume, exchange, vwap, trades
        Results are in chronological order (oldest first).
        """
        from app.models.candle import Candle

        query = (
            select(Candle)
            .where(Candle.symbol == symbol, Candle.timeframe == timeframe)
            .order_by(Candle.time.desc())
            .limit(limit)
        )

        if since is not None:
            query = query.where(Candle.time >= since)

        if exchange is not None:
            query = query.where(Candle.exchange == exchange)

        result = await db.execute(query)
        candles = result.scalars().all()

        return [
            {
                "time": c.time,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
                "exchange": c.exchange,
                "vwap": c.vwap,
                "trades": c.trades,
            }
            for c in reversed(candles)  # chronological order
        ]

    @staticmethod
    async def load_close_prices(
        db: AsyncSession,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 500,
        exchange: str | None = None,
    ) -> list[float]:
        """Load just close prices for a symbol (useful for correlation).

        Returns list of floats in chronological order.
        """
        from app.models.candle import Candle

        query = (
            select(Candle.close)
            .where(Candle.symbol == symbol, Candle.timeframe == timeframe)
            .order_by(Candle.time.desc())
            .limit(limit)
        )
        if exchange is not None:
            query = query.where(Candle.exchange == exchange)

        result = await db.execute(query)
        rows = result.all()
        return [float(r[0]) for r in reversed(rows)]
