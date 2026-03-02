import numpy as np
import pandas as pd


def make_bullish_candles(n=250):
    """Price trending up with aligned EMAs."""
    rng = np.random.default_rng(42)
    close = 100 + np.arange(n) * 0.5 + rng.normal(0, 0.3, n)
    high = close + rng.uniform(0.5, 1.5, n)
    low = close - rng.uniform(0.5, 1.5, n)
    return pd.DataFrame({
        "open": close + 0.1,
        "high": high,
        "low": low,
        "close": close,
        "volume": np.ones(n) * 5000,
    })


def make_bearish_candles(n=250):
    """Price trending down with aligned EMAs."""
    rng = np.random.default_rng(42)
    close = 200 - np.arange(n) * 0.5 + rng.normal(0, 0.3, n)
    high = close + rng.uniform(0.5, 1.5, n)
    low = close - rng.uniform(0.5, 1.5, n)
    return pd.DataFrame({
        "open": close + 0.1,
        "high": high,
        "low": low,
        "close": close,
        "volume": np.ones(n) * 5000,
    })


def make_ranging_candles(n=250):
    """Price oscillating around 100 -- no clear trend."""
    rng = np.random.default_rng(42)
    close = 100 + rng.normal(0, 2, n)
    high = close + rng.uniform(0.5, 1.5, n)
    low = close - rng.uniform(0.5, 1.5, n)
    return pd.DataFrame({
        "open": close + 0.1,
        "high": high,
        "low": low,
        "close": close,
        "volume": np.ones(n) * 5000,
    })


class TestTrendFilter:
    def test_bullish_trend_detected(self):
        from app.engine.layers.trend import Trend, TrendFilter
        tf = TrendFilter()
        result = tf.evaluate(make_bullish_candles())
        assert result.direction == Trend.BULLISH
        assert result.strength > 0

    def test_bearish_trend_detected(self):
        from app.engine.layers.trend import Trend, TrendFilter
        tf = TrendFilter()
        result = tf.evaluate(make_bearish_candles())
        assert result.direction == Trend.BEARISH
        assert result.strength > 0

    def test_ranging_market_undetermined(self):
        from app.engine.layers.trend import Trend, TrendFilter
        tf = TrendFilter()
        result = tf.evaluate(make_ranging_candles())
        assert result.direction == Trend.UNDETERMINED

    def test_insufficient_data_undetermined(self):
        from app.engine.layers.trend import Trend, TrendFilter
        tf = TrendFilter()
        # Only 100 candles, need 200
        small = make_bullish_candles(100)
        result = tf.evaluate(small)
        assert result.direction == Trend.UNDETERMINED
        assert result.strength == 0

    def test_result_has_vwap_aligned(self):
        from app.engine.layers.trend import TrendFilter
        tf = TrendFilter()
        result = tf.evaluate(make_bullish_candles())
        # For a bullish trend, vwap_aligned should be a boolean
        assert isinstance(result.vwap_aligned, bool)

    def test_lower_slope_threshold_more_permissive(self):
        from app.engine.layers.trend import Trend, TrendFilter
        strict = TrendFilter(slope_threshold=0.01)
        loose = TrendFilter(slope_threshold=0.0001)
        candles = make_bullish_candles()
        r_strict = strict.evaluate(candles)
        r_loose = loose.evaluate(candles)
        # Loose threshold should still detect the trend
        assert r_loose.direction == Trend.BULLISH
        # If strict fails to detect, that confirms the threshold matters
        if r_strict.direction == Trend.UNDETERMINED:
            assert r_loose.direction != Trend.UNDETERMINED

    def test_impossible_slope_threshold_rejects(self):
        from app.engine.layers.trend import Trend, TrendFilter
        # A slope threshold of 10.0 (1000%) should be impossible to meet
        tf = TrendFilter(slope_threshold=10.0)
        result = tf.evaluate(make_bullish_candles())
        assert result.direction == Trend.UNDETERMINED
