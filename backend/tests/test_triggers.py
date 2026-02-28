import numpy as np
import pandas as pd


def make_macd_cross_up_candles(n=200):
    """Data where MACD crosses above signal near the end."""
    rng = np.random.default_rng(42)
    # Declining then sharply rising — triggers MACD cross up
    close = np.concatenate([
        100 - np.arange(150) * 0.1 + rng.normal(0, 0.2, 150),
        85 + np.arange(50) * 0.6 + rng.normal(0, 0.2, 50),
    ])
    high = close + rng.uniform(0.5, 1.5, n)
    low = close - rng.uniform(0.5, 1.5, n)
    return pd.DataFrame({
        "open": close, "high": high, "low": low,
        "close": close, "volume": rng.uniform(1000, 5000, n),
    })


class TestTriggerDetector:
    def test_returns_trigger_result(self):
        from app.engine.layers.trend import Trend, TrendResult
        from app.engine.layers.triggers import TriggerDetector, TriggerResult
        from app.engine.layers.zones import EntryZone
        td = TriggerDetector()
        zone = EntryZone(zone_type="fibonacci_golden", upper=110, lower=90, strength=0.7)
        trend = TrendResult(direction=Trend.BULLISH, strength=0.01)
        result = td.check(make_macd_cross_up_candles(), zone, trend)
        assert isinstance(result, TriggerResult)
        assert isinstance(result.confirmed, bool)
        assert isinstance(result.confirmations, list)

    def test_requires_two_confirmations(self):
        from app.engine.layers.trend import Trend, TrendResult
        from app.engine.layers.triggers import TriggerDetector
        from app.engine.layers.zones import EntryZone
        td = TriggerDetector()
        zone = EntryZone(zone_type="fibonacci_golden", upper=200, lower=0, strength=0.7)
        trend = TrendResult(direction=Trend.BULLISH, strength=0.01)
        result = td.check(make_macd_cross_up_candles(), zone, trend)
        if result.confirmed:
            assert len(result.confirmations) >= 2

    def test_confirmations_are_strings(self):
        from app.engine.layers.trend import Trend, TrendResult
        from app.engine.layers.triggers import TriggerDetector
        from app.engine.layers.zones import EntryZone
        td = TriggerDetector()
        zone = EntryZone(zone_type="fibonacci_golden", upper=200, lower=0, strength=0.7)
        trend = TrendResult(direction=Trend.BULLISH, strength=0.01)
        result = td.check(make_macd_cross_up_candles(), zone, trend)
        for c in result.confirmations:
            assert isinstance(c, str)
