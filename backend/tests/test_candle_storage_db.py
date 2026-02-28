"""Tests for DB-backed CandleStorage."""

import inspect


def test_candle_storage_imports():
    """Verify CandleStorage can be imported."""
    from app.data.storage import CandleStorage

    assert hasattr(CandleStorage, "save_candles_db")
    assert hasattr(CandleStorage, "load_candles_db")
    assert hasattr(CandleStorage, "load_close_prices")


def test_candle_storage_db_methods_are_static():
    """Verify DB methods are static (no instance needed)."""
    from app.data.storage import CandleStorage

    assert isinstance(
        inspect.getattr_static(CandleStorage, "save_candles_db"), staticmethod
    )
    assert isinstance(
        inspect.getattr_static(CandleStorage, "load_candles_db"), staticmethod
    )
    assert isinstance(
        inspect.getattr_static(CandleStorage, "load_close_prices"), staticmethod
    )


def test_candle_storage_db_methods_are_async():
    """Verify DB methods are coroutine functions."""
    from app.data.storage import CandleStorage

    assert inspect.iscoroutinefunction(CandleStorage.save_candles_db)
    assert inspect.iscoroutinefunction(CandleStorage.load_candles_db)
    assert inspect.iscoroutinefunction(CandleStorage.load_close_prices)


def test_legacy_in_memory_interface_preserved():
    """Verify the legacy in-memory interface still works for backward compat."""
    from datetime import datetime, timezone

    import pandas as pd

    from app.data.storage import CandleStorage

    storage = CandleStorage()

    # Build test candles
    rows = []
    for i in range(3):
        rows.append(
            {
                "time": datetime(2026, 1, 1, i, 0, 0, tzinfo=timezone.utc),
                "open": 100.0 + i,
                "high": 105.0 + i,
                "low": 95.0 + i,
                "close": 101.0 + i,
                "volume": 1000.0,
                "symbol": "BTC/USDT",
                "exchange": "binance",
                "timeframe": "1h",
            }
        )
    candles = pd.DataFrame(rows)

    saved = storage.save_candles(candles)
    assert saved == 3

    loaded = storage.load_candles("BTC/USDT", "1h")
    assert len(loaded) == 3
    assert loaded.iloc[-1]["close"] == 103.0


def test_legacy_load_with_limit():
    """Legacy in-memory: load with limit returns most recent candles."""
    from datetime import datetime, timezone

    import pandas as pd

    from app.data.storage import CandleStorage

    storage = CandleStorage()

    rows = []
    for i in range(10):
        rows.append(
            {
                "time": datetime(2026, 1, 1, i, 0, 0, tzinfo=timezone.utc),
                "open": 100.0 + i,
                "high": 105.0 + i,
                "low": 95.0 + i,
                "close": 101.0 + i,
                "volume": 1000.0,
                "symbol": "ETH/USDT",
                "exchange": "binance",
                "timeframe": "1h",
            }
        )
    candles = pd.DataFrame(rows)
    storage.save_candles(candles)

    loaded = storage.load_candles("ETH/USDT", "1h", limit=3)
    assert len(loaded) == 3
    # Most recent 3 should be hours 7, 8, 9
    assert loaded.iloc[-1]["close"] == 110.0  # 101 + 9


def test_legacy_load_empty():
    """Legacy in-memory: load non-existent symbol returns empty DataFrame."""
    import pandas as pd

    from app.data.storage import CandleStorage

    storage = CandleStorage()
    loaded = storage.load_candles("DOGE/USDT", "1h")
    assert isinstance(loaded, pd.DataFrame)
    assert len(loaded) == 0
