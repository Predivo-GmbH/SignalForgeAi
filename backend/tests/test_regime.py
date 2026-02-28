import numpy as np
import pandas as pd


def make_trending_candles(n=200):
    """Strong trend — ADX should be high."""
    rng = np.random.default_rng(42)
    close = 100 + np.arange(n) * 0.8 + rng.normal(0, 0.5, n)
    high = close + rng.uniform(0.5, 2, n)
    low = close - rng.uniform(0.5, 2, n)
    return pd.DataFrame(
        {
            "open": close + 0.1,
            "high": high,
            "low": low,
            "close": close,
            "volume": rng.uniform(1000, 5000, n),
        }
    )


def make_ranging_candles(n=200):
    """Sideways chop — ADX should be low."""
    rng = np.random.default_rng(42)
    close = 100 + rng.normal(0, 0.5, n)
    high = close + rng.uniform(0.3, 0.8, n)
    low = close - rng.uniform(0.3, 0.8, n)
    return pd.DataFrame(
        {
            "open": close,
            "high": high,
            "low": low,
            "close": close,
            "volume": rng.uniform(1000, 5000, n),
        }
    )


def make_chaotic_candles(n=200):
    """Wild volatility swings — ATR in extreme percentile."""
    rng = np.random.default_rng(42)
    close = 100 + np.cumsum(rng.normal(0, 5, n))
    high = close + rng.uniform(3, 10, n)
    low = close - rng.uniform(3, 10, n)
    return pd.DataFrame(
        {
            "open": close,
            "high": high,
            "low": low,
            "close": close,
            "volume": rng.uniform(1000, 5000, n),
        }
    )


class TestRegimeDetector:
    def test_trending_regime(self):
        from app.engine.layers.regime import Regime, RegimeDetector

        rd = RegimeDetector()
        result = rd.detect(make_trending_candles())
        assert result in (Regime.TRENDING_BULL, Regime.TRENDING_BEAR, Regime.TRENDING)

    def test_ranging_regime(self):
        from app.engine.layers.regime import Regime, RegimeDetector

        rd = RegimeDetector()
        result = rd.detect(make_ranging_candles())
        assert result in (Regime.RANGING, Regime.TRANSITIONING)

    def test_returns_regime_enum(self):
        from app.engine.layers.regime import Regime, RegimeDetector

        rd = RegimeDetector()
        result = rd.detect(make_trending_candles())
        assert isinstance(result, Regime)

    def test_atr_percentile_calculation(self):
        from app.engine.layers.regime import RegimeDetector

        rd = RegimeDetector()
        candles = make_trending_candles()
        pct = rd._atr_percentile(candles, lookback=100)
        assert 0 <= pct <= 100

    def test_adx_regime_thresholds(self):
        from app.engine.layers.regime import Regime, RegimeDetector

        rd = RegimeDetector()
        assert rd._adx_regime(30) == Regime.TRENDING
        assert rd._adx_regime(15) == Regime.RANGING
        assert rd._adx_regime(22) == Regime.TRANSITIONING
