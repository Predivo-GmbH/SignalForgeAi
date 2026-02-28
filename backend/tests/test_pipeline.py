"""Tests for SignalPipeline orchestrator and SessionFilter."""

from datetime import datetime, timezone

import numpy as np
import pandas as pd


def make_trending_candles(n=300):
    rng = np.random.default_rng(42)
    close = 100 + np.arange(n) * 0.3 + rng.normal(0, 0.5, n)
    high = close + rng.uniform(0.5, 2, n)
    low = close - rng.uniform(0.5, 2, n)
    return pd.DataFrame(
        {
            "open": close,
            "high": high,
            "low": low,
            "close": close,
            "volume": rng.uniform(1000, 5000, n),
        }
    )


class TestSignalPipeline:
    def test_process_returns_signal(self):
        from app.engine.pipeline import Signal, SignalPipeline

        pipeline = SignalPipeline()
        result = pipeline.process("TEST/USD", "1h", make_trending_candles())
        assert isinstance(result, Signal)

    def test_signal_has_required_fields(self):
        from app.engine.pipeline import SignalPipeline

        pipeline = SignalPipeline()
        result = pipeline.process("TEST/USD", "1h", make_trending_candles())
        assert hasattr(result, "action")
        assert hasattr(result, "symbol")
        assert hasattr(result, "confluence_score")
        assert hasattr(result, "regime")

    def test_no_trade_is_valid_result(self):
        from app.engine.pipeline import SignalPipeline

        pipeline = SignalPipeline()
        # Ranging data should produce NO_TRADE
        rng = np.random.default_rng(42)
        n = 300
        close = 100 + rng.normal(0, 0.5, n)
        high = close + 0.5
        low = close - 0.5
        candles = pd.DataFrame(
            {
                "open": close,
                "high": high,
                "low": low,
                "close": close,
                "volume": np.ones(n) * 5000,
            }
        )
        result = pipeline.process("TEST/USD", "1h", candles)
        assert result.action == "NO_TRADE"

    def test_signal_symbol_and_timeframe_propagated(self):
        from app.engine.pipeline import SignalPipeline

        pipeline = SignalPipeline()
        result = pipeline.process("BTC/USDT", "4h", make_trending_candles())
        assert result.symbol == "BTC/USDT"
        assert result.timeframe == "4h"

    def test_signal_has_timestamp(self):
        from app.engine.pipeline import SignalPipeline

        pipeline = SignalPipeline()
        result = pipeline.process("ETH/USD", "1h", make_trending_candles())
        assert result.timestamp is not None
        # Should be ISO format string
        datetime.fromisoformat(result.timestamp)

    def test_no_trade_has_block_reason(self):
        from app.engine.pipeline import SignalPipeline

        pipeline = SignalPipeline()
        rng = np.random.default_rng(42)
        n = 300
        close = 100 + rng.normal(0, 0.5, n)
        high = close + 0.5
        low = close - 0.5
        candles = pd.DataFrame(
            {
                "open": close,
                "high": high,
                "low": low,
                "close": close,
                "volume": np.ones(n) * 5000,
            }
        )
        result = pipeline.process("TEST/USD", "1h", candles)
        assert result.action == "NO_TRADE"
        assert result.block_reason is not None


class TestSessionFilter:
    def test_london_session_active(self):
        from app.engine.filters import SessionFilter

        sf = SessionFilter()
        # Tuesday 10:00 UTC — London session
        ts = datetime(2026, 2, 24, 10, 0, tzinfo=timezone.utc)
        assert sf.is_active_session(ts) is True

    def test_ny_session_active(self):
        from app.engine.filters import SessionFilter

        sf = SessionFilter()
        # Tuesday 15:00 UTC — NY session (overlap)
        ts = datetime(2026, 2, 24, 15, 0, tzinfo=timezone.utc)
        assert sf.is_active_session(ts) is True

    def test_weekend_blocked(self):
        from app.engine.filters import SessionFilter

        sf = SessionFilter()
        # Saturday 12:00 UTC
        ts = datetime(2026, 2, 28, 12, 0, tzinfo=timezone.utc)
        assert sf.is_active_session(ts) is False

    def test_off_hours_blocked(self):
        from app.engine.filters import SessionFilter

        sf = SessionFilter()
        # Tuesday 03:00 UTC — outside all sessions
        ts = datetime(2026, 2, 24, 3, 0, tzinfo=timezone.utc)
        assert sf.is_active_session(ts) is False

    def test_overlap_session_active(self):
        from app.engine.filters import SessionFilter

        sf = SessionFilter()
        # Tuesday 14:00 UTC — London/NY overlap
        ts = datetime(2026, 2, 24, 14, 0, tzinfo=timezone.utc)
        assert sf.is_active_session(ts) is True

    def test_sunday_blocked(self):
        from app.engine.filters import SessionFilter

        sf = SessionFilter()
        # Sunday 10:00 UTC
        ts = datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc)
        assert sf.is_active_session(ts) is False
