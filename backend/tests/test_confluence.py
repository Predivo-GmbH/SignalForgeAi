import numpy as np
import pandas as pd
import pytest


def make_candles(n=200):
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


class TestConfluenceScorer:
    def test_score_returns_int_0_to_100(self):
        from app.engine.layers.confluence import ConfluenceScorer
        from app.engine.layers.trend import Trend, TrendResult
        from app.engine.layers.zones import EntryZone

        scorer = ConfluenceScorer()
        zone = EntryZone(zone_type="fibonacci_golden", upper=110, lower=105, strength=0.7)
        trend = TrendResult(direction=Trend.BULLISH, strength=0.01)
        score = scorer.score(zone, make_candles(), trend)
        assert isinstance(score, int)
        assert 0 <= score <= 100

    def test_fibonacci_zone_gets_base_points(self):
        from app.engine.layers.confluence import ConfluenceScorer
        from app.engine.layers.trend import Trend, TrendResult
        from app.engine.layers.zones import EntryZone

        scorer = ConfluenceScorer()
        fib_zone = EntryZone(
            zone_type="fibonacci_golden", upper=110, lower=105, strength=0.7
        )
        non_fib = EntryZone(zone_type="vwap_1sigma", upper=110, lower=105, strength=0.5)
        trend = TrendResult(direction=Trend.BULLISH, strength=0.01)
        candles = make_candles()
        fib_score = scorer.score(fib_zone, candles, trend)
        non_fib_score = scorer.score(non_fib, candles, trend)
        assert fib_score >= non_fib_score  # Fib zone should score at least as high

    def test_weights_sum_to_100(self):
        from app.engine.layers.confluence import ConfluenceScorer

        scorer = ConfluenceScorer()
        assert sum(scorer.WEIGHTS.values()) == 100

    def test_score_details_returned(self):
        from app.engine.layers.confluence import ConfluenceScorer
        from app.engine.layers.trend import Trend, TrendResult
        from app.engine.layers.zones import EntryZone

        scorer = ConfluenceScorer()
        zone = EntryZone(zone_type="fibonacci_golden", upper=110, lower=105, strength=0.7)
        trend = TrendResult(direction=Trend.BULLISH, strength=0.01)
        score, details = scorer.score_with_details(zone, make_candles(), trend)
        assert isinstance(details, dict)
        assert isinstance(score, int)
