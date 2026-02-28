import numpy as np
import pandas as pd


def make_candles(n=200):
    rng = np.random.default_rng(42)
    close = 100 + np.arange(n) * 0.3 + rng.normal(0, 0.5, n)
    high = close + rng.uniform(0.5, 2, n)
    low = close - rng.uniform(0.5, 2, n)
    return pd.DataFrame({
        "open": close, "high": high, "low": low,
        "close": close, "volume": rng.uniform(1000, 5000, n),
    })


class TestRiskManager:
    def test_calculates_stop_loss_and_take_profit(self):
        from app.engine.layers.risk import RiskConfig, RiskManager
        from app.engine.layers.trend import Trend, TrendResult
        from app.engine.layers.zones import EntryZone
        rm = RiskManager(RiskConfig())
        zone = EntryZone(zone_type="fibonacci_golden", upper=110, lower=105, strength=0.7)
        trend = TrendResult(direction=Trend.BULLISH, strength=0.01)
        result = rm.calculate(
            make_candles(), zone, trend, confluence_score=75, account_equity=10000,
        )
        assert result.stop_loss > 0
        assert result.take_profit_1 > result.stop_loss
        assert result.position_size > 0

    def test_bullish_stop_below_entry(self):
        from app.engine.layers.risk import RiskConfig, RiskManager
        from app.engine.layers.trend import Trend, TrendResult
        from app.engine.layers.zones import EntryZone
        rm = RiskManager(RiskConfig())
        zone = EntryZone(zone_type="fibonacci_golden", upper=180, lower=150, strength=0.7)
        trend = TrendResult(direction=Trend.BULLISH, strength=0.01)
        candles = make_candles()
        entry = candles["close"].iloc[-1]
        result = rm.calculate(candles, zone, trend, confluence_score=75, account_equity=10000)
        assert result.stop_loss < entry

    def test_minimum_risk_reward_enforced(self):
        from app.engine.layers.risk import RiskConfig, RiskManager
        rm = RiskManager(RiskConfig(min_risk_reward=1.5))
        from app.engine.layers.trend import Trend, TrendResult
        from app.engine.layers.zones import EntryZone
        zone = EntryZone(zone_type="fibonacci_golden", upper=180, lower=150, strength=0.7)
        trend = TrendResult(direction=Trend.BULLISH, strength=0.01)
        result = rm.calculate(
            make_candles(), zone, trend, confluence_score=75, account_equity=10000,
        )
        assert result.rejected or result.risk_reward >= 1.5

    def test_confluence_score_scales_position(self):
        from app.engine.layers.risk import RiskConfig, RiskManager
        from app.engine.layers.trend import Trend, TrendResult
        from app.engine.layers.zones import EntryZone
        rm = RiskManager(RiskConfig())
        zone = EntryZone(zone_type="fibonacci_golden", upper=180, lower=150, strength=0.7)
        trend = TrendResult(direction=Trend.BULLISH, strength=0.01)
        candles = make_candles()
        low_score = rm.calculate(candles, zone, trend, confluence_score=50, account_equity=10000)
        high_score = rm.calculate(candles, zone, trend, confluence_score=100, account_equity=10000)
        if not low_score.rejected and not high_score.rejected:
            assert high_score.position_size >= low_score.position_size

    def test_risk_config_defaults(self):
        from app.engine.layers.risk import RiskConfig
        config = RiskConfig()
        assert config.max_risk_per_trade == 0.02
        assert config.max_daily_loss == 0.06
        assert config.atr_sl_multiplier == 2.0
        assert config.min_risk_reward == 1.5
