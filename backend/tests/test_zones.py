import numpy as np
import pandas as pd


def make_candles_with_swing(n=200):
    """Creates data with a clear swing high/low for Fibonacci."""
    rng = np.random.default_rng(42)
    # Go up to ~150, then retrace to ~130
    close = np.concatenate([
        100 + np.arange(100) * 0.5 + rng.normal(0, 0.3, 100),  # up to ~150
        150 - np.arange(100) * 0.2 + rng.normal(0, 0.3, 100),  # retrace to ~130
    ])
    high = close + rng.uniform(0.5, 1.5, n)
    low = close - rng.uniform(0.5, 1.5, n)
    return pd.DataFrame({
        "open": close,
        "high": high,
        "low": low,
        "close": close,
        "volume": rng.uniform(1000, 5000, n),
    })


class TestZoneIdentifier:
    def test_finds_fibonacci_zones(self):
        from app.engine.layers.trend import Trend, TrendResult
        from app.engine.layers.zones import ZoneIdentifier
        zi = ZoneIdentifier()
        candles = make_candles_with_swing()
        trend = TrendResult(direction=Trend.BULLISH, strength=0.01)
        zones = zi.find_zones(candles, trend)
        assert len(zones) > 0
        assert any(z.zone_type == "fibonacci_golden" for z in zones)

    def test_zones_have_upper_greater_equal_lower(self):
        from app.engine.layers.trend import Trend, TrendResult
        from app.engine.layers.zones import ZoneIdentifier
        zi = ZoneIdentifier()
        candles = make_candles_with_swing()
        trend = TrendResult(direction=Trend.BULLISH, strength=0.01)
        zones = zi.find_zones(candles, trend)
        for z in zones:
            assert z.upper >= z.lower, f"Zone {z.zone_type}: upper={z.upper} < lower={z.lower}"

    def test_vwap_zones_returned(self):
        from app.engine.layers.trend import Trend, TrendResult
        from app.engine.layers.zones import ZoneIdentifier
        zi = ZoneIdentifier()
        candles = make_candles_with_swing()
        trend = TrendResult(direction=Trend.BULLISH, strength=0.01)
        zones = zi.find_zones(candles, trend)
        assert any(z.zone_type.startswith("vwap") for z in zones)

    def test_fibonacci_golden_zone_has_levels(self):
        from app.engine.layers.trend import Trend, TrendResult
        from app.engine.layers.zones import ZoneIdentifier
        zi = ZoneIdentifier()
        candles = make_candles_with_swing()
        trend = TrendResult(direction=Trend.BULLISH, strength=0.01)
        zones = zi.find_zones(candles, trend)
        fib_zones = [z for z in zones if z.zone_type == "fibonacci_golden"]
        assert len(fib_zones) == 1
        assert fib_zones[0].levels is not None
        assert 0.382 in fib_zones[0].levels
        assert 0.618 in fib_zones[0].levels

    def test_bearish_trend_also_produces_zones(self):
        from app.engine.layers.trend import Trend, TrendResult
        from app.engine.layers.zones import ZoneIdentifier
        zi = ZoneIdentifier()
        candles = make_candles_with_swing()
        trend = TrendResult(direction=Trend.BEARISH, strength=0.01)
        zones = zi.find_zones(candles, trend)
        assert len(zones) > 0

    def test_zone_to_dict(self):
        from app.engine.layers.zones import EntryZone
        zone = EntryZone(
            zone_type="fibonacci_golden",
            upper=150.0,
            lower=130.0,
            strength=0.7,
        )
        d = zone.to_dict()
        assert d["zone_type"] == "fibonacci_golden"
        assert d["upper"] == 150.0
        assert d["lower"] == 130.0
        assert d["strength"] == 0.7
