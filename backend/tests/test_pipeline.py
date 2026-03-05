"""Tests for SignalPipeline orchestrator and SessionFilter."""

from datetime import datetime

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


