from datetime import datetime, timezone

import pandas as pd

from app.data.storage import CandleStorage


def _make_candles(count: int, start_hour: int = 0, close_base: float = 100.0) -> pd.DataFrame:
    """Helper: generate a DataFrame of synthetic candles."""
    rows = []
    for i in range(count):
        rows.append(
            {
                "time": datetime(2026, 1, 1, start_hour + i, 0, 0, tzinfo=timezone.utc),
                "open": close_base + i,
                "high": close_base + i + 5,
                "low": close_base + i - 5,
                "close": close_base + i + 1,
                "volume": 1000.0 + i * 100,
                "symbol": "BTC/USDT",
                "exchange": "binance",
                "timeframe": "1h",
            }
        )
    return pd.DataFrame(rows)


def test_save_and_load_candles():
    """Save 5 candles, load them back, verify count and last close value."""
    storage = CandleStorage()
    candles = _make_candles(5)
    saved = storage.save_candles(candles)

    assert saved == 5

    loaded = storage.load_candles("BTC/USDT", "1h")
    assert len(loaded) == 5
    # Last candle (hour 4) has close = 100.0 + 4 + 1 = 105.0
    assert loaded.iloc[-1]["close"] == 105.0


def test_load_with_limit():
    """Save 10 candles, load with limit=3, verify only 3 returned (most recent)."""
    storage = CandleStorage()
    candles = _make_candles(10)
    storage.save_candles(candles)

    loaded = storage.load_candles("BTC/USDT", "1h", limit=3)
    assert len(loaded) == 3
    # Most recent 3 should be hours 7, 8, 9
    # Hour 9 close = 100.0 + 9 + 1 = 110.0
    assert loaded.iloc[-1]["close"] == 110.0
    # Hour 7 close = 100.0 + 7 + 1 = 108.0
    assert loaded.iloc[0]["close"] == 108.0


def test_upsert_dedup():
    """Save candles, save overlapping candles with updated values, verify dedup."""
    storage = CandleStorage()

    # First batch: hours 0-4
    batch1 = _make_candles(5, start_hour=0, close_base=100.0)
    storage.save_candles(batch1)

    # Second batch: hours 3-7 (overlaps at hours 3, 4) with different close_base
    batch2 = _make_candles(5, start_hour=3, close_base=200.0)
    storage.save_candles(batch2)

    loaded = storage.load_candles("BTC/USDT", "1h")
    # Should have 8 unique hours: 0, 1, 2, 3, 4, 5, 6, 7
    assert len(loaded) == 8

    # Hours 3 and 4 should have the UPDATED values from batch2
    hour3 = loaded[loaded["time"] == datetime(2026, 1, 1, 3, 0, 0, tzinfo=timezone.utc)]
    assert len(hour3) == 1
    # batch2 hour 3: close_base=200, offset=0 → close = 200 + 0 + 1 = 201.0
    assert hour3.iloc[0]["close"] == 201.0

    hour4 = loaded[loaded["time"] == datetime(2026, 1, 1, 4, 0, 0, tzinfo=timezone.utc)]
    assert len(hour4) == 1
    # batch2 hour 4: close_base=200, offset=1 → close = 200 + 1 + 1 = 202.0
    assert hour4.iloc[0]["close"] == 202.0


def test_load_empty():
    """Load from non-existent symbol returns empty DataFrame."""
    storage = CandleStorage()
    loaded = storage.load_candles("DOGE/USDT", "1h")
    assert isinstance(loaded, pd.DataFrame)
    assert len(loaded) == 0


def test_load_with_since_filter():
    """Save 5 candles, load with since filter, verify only candles after since are returned."""
    storage = CandleStorage()
    candles = _make_candles(5)
    storage.save_candles(candles)

    since = datetime(2026, 1, 1, 2, 0, 0, tzinfo=timezone.utc)
    loaded = storage.load_candles("BTC/USDT", "1h", since=since)
    # Should return hours 2, 3, 4
    assert len(loaded) == 3
    assert loaded.iloc[0]["time"] == datetime(2026, 1, 1, 2, 0, 0, tzinfo=timezone.utc)
