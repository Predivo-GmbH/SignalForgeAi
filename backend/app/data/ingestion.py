"""CCXT-based OHLCV candle ingestion.

Wraps the ``ccxt`` library to fetch historical candle data from any supported
exchange and return it as a pandas DataFrame ready for ``CandleStorage``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import ccxt
import pandas as pd

logger = logging.getLogger(__name__)

# OHLCV column order returned by ccxt
_OHLCV_COLUMNS = ["time", "open", "high", "low", "close", "volume"]


class CCXTIngestion:
    """Fetch OHLCV candles from a CCXT-supported exchange.

    Parameters
    ----------
    exchange_id:
        CCXT exchange identifier, e.g. ``"binance"``, ``"bybit"``.
    """

    def __init__(self, exchange_id: str = "binance") -> None:
        exchange_class = getattr(ccxt, exchange_id, None)
        if exchange_class is None:
            raise ValueError(f"Unknown exchange: {exchange_id}")

        self.exchange: ccxt.Exchange = exchange_class(
            {
                "enableRateLimit": True,
            }
        )
        self.exchange_id = exchange_id

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_candles(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 500,
        since: datetime | None = None,
    ) -> pd.DataFrame:
        """Fetch OHLCV data and return a typed DataFrame.

        Parameters
        ----------
        symbol:
            Trading pair, e.g. ``"BTC/USDT"``.
        timeframe:
            Candle interval, e.g. ``"1m"``, ``"5m"``, ``"1h"``, ``"1d"``.
        limit:
            Maximum number of candles to retrieve (exchange may cap this).
        since:
            Fetch candles starting from this UTC datetime.  When *None* the
            exchange returns the most recent candles.

        Returns
        -------
        pd.DataFrame
            Columns: ``time`` (datetime UTC), ``open``, ``high``, ``low``,
            ``close``, ``volume``, ``symbol``, ``exchange``, ``timeframe``.
        """
        since_ms: int | None = None
        if since is not None:
            since_ms = int(since.timestamp() * 1000)

        logger.info(
            "Fetching %s %s candles for %s (limit=%d, since=%s)",
            self.exchange_id,
            timeframe,
            symbol,
            limit,
            since,
        )

        raw: list[list] = self.exchange.fetch_ohlcv(
            symbol,
            timeframe=timeframe,
            limit=limit,
            since=since_ms,
        )

        if not raw:
            logger.warning("No candles returned for %s %s", symbol, timeframe)
            return pd.DataFrame(
                columns=[*_OHLCV_COLUMNS, "symbol", "exchange", "timeframe"]
            )

        df = pd.DataFrame(raw, columns=_OHLCV_COLUMNS)

        # Convert millisecond timestamps to timezone-aware UTC datetimes
        df["time"] = pd.to_datetime(df["time"], unit="ms", utc=True).dt.to_pydatetime()
        df["time"] = [t.replace(tzinfo=timezone.utc) if t.tzinfo is None else t for t in df["time"]]

        # Attach metadata columns
        df["symbol"] = symbol
        df["exchange"] = self.exchange_id
        df["timeframe"] = timeframe

        logger.info("Fetched %d candles for %s %s", len(df), symbol, timeframe)
        return df
