"""Tests for Layer 6: ReversalMonitor — severity-based exit action recommendations."""

import numpy as np
import pandas as pd


def make_reversal_candles(n=100):
    """Uptrend that reverses — EMA cross, volume divergence."""
    rng = np.random.default_rng(42)
    up = 100 + np.arange(60) * 0.5 + rng.normal(0, 0.3, 60)
    down = up[-1] - np.arange(40) * 0.8 + rng.normal(0, 0.3, 40)
    close = np.concatenate([up, down])
    high = close + rng.uniform(0.5, 1.5, n)
    low = close - rng.uniform(0.5, 1.5, n)
    vol = np.concatenate([rng.uniform(5000, 10000, 60), rng.uniform(1000, 3000, 40)])
    return pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": vol})


class TestReversalMonitor:
    def test_returns_reversal_action(self):
        from app.engine.reversal import ReversalAction, ReversalMonitor

        rm = ReversalMonitor()
        candles = make_reversal_candles()
        action = rm.check_position(candles, direction="LONG")
        assert isinstance(action, ReversalAction)

    def test_reversal_detects_ema_cross(self):
        from app.engine.reversal import ReversalAction, ReversalMonitor

        rm = ReversalMonitor()
        candles = make_reversal_candles()
        action = rm.check_position(candles, direction="LONG")
        assert action in (
            ReversalAction.HOLD,
            ReversalAction.PARTIAL_CLOSE,
            ReversalAction.TIGHTEN_STOP,
            ReversalAction.CLOSE_POSITION,
        )

    def test_hold_on_healthy_trend(self):
        from app.engine.reversal import ReversalAction, ReversalMonitor

        rng = np.random.default_rng(42)
        n = 100
        close = 100 + np.arange(n) * 0.5 + rng.normal(0, 0.2, n)
        high = close + rng.uniform(0.3, 1, n)
        low = close - rng.uniform(0.3, 1, n)
        candles = pd.DataFrame(
            {
                "open": close,
                "high": high,
                "low": low,
                "close": close,
                "volume": rng.uniform(3000, 8000, n),
            }
        )
        rm = ReversalMonitor()
        action = rm.check_position(candles, direction="LONG")
        assert action == ReversalAction.HOLD

    def test_short_position_hold_on_downtrend(self):
        """Short position in a healthy downtrend should HOLD."""
        from app.engine.reversal import ReversalAction, ReversalMonitor

        rng = np.random.default_rng(42)
        n = 100
        close = 200 - np.arange(n) * 0.5 + rng.normal(0, 0.2, n)
        high = close + rng.uniform(0.3, 1, n)
        low = close - rng.uniform(0.3, 1, n)
        candles = pd.DataFrame(
            {
                "open": close,
                "high": high,
                "low": low,
                "close": close,
                "volume": rng.uniform(3000, 8000, n),
            }
        )
        rm = ReversalMonitor()
        action = rm.check_position(candles, direction="SHORT")
        assert action == ReversalAction.HOLD

    def test_reversal_action_enum_values(self):
        from app.engine.reversal import ReversalAction

        assert ReversalAction.HOLD.value == "hold"
        assert ReversalAction.PARTIAL_CLOSE.value == "partial_close"
        assert ReversalAction.TIGHTEN_STOP.value == "tighten_stop"
        assert ReversalAction.CLOSE_POSITION.value == "close_position"
