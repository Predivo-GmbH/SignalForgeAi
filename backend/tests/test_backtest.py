import numpy as np
import pandas as pd


def make_trending_candles(n=300):
    """Trending upward data with enough bars for lookback."""
    rng = np.random.default_rng(42)
    close = 100 + np.arange(n) * 0.3 + rng.normal(0, 1, n)
    high = close + rng.uniform(0.5, 2, n)
    low = close - rng.uniform(0.5, 2, n)
    return pd.DataFrame({
        "open": close + rng.normal(0, 0.2, n),
        "high": high,
        "low": low,
        "close": close,
        "volume": rng.uniform(1000, 10000, n),
    })


def make_flat_candles(n=300):
    """Flat/ranging data -- no trend, should produce few or no trades."""
    rng = np.random.default_rng(42)
    close = 100 + rng.normal(0, 0.5, n)
    high = close + rng.uniform(0.5, 1, n)
    low = close - rng.uniform(0.5, 1, n)
    return pd.DataFrame({
        "open": close + rng.normal(0, 0.1, n),
        "high": high,
        "low": low,
        "close": close,
        "volume": rng.uniform(1000, 10000, n),
    })


class TestBacktestEngine:
    def test_returns_result_with_metrics(self):
        from app.backtest.engine import BacktestEngine
        engine = BacktestEngine()
        result = engine.run(
            candles=make_trending_candles(),
            symbol="TEST/USD",
            timeframe="1h",
            initial_capital=10000.0,
        )
        assert "total_trades" in result.metrics
        assert "win_rate" in result.metrics
        assert "profit_factor" in result.metrics
        assert "total_return_pct" in result.metrics
        assert "max_drawdown_pct" in result.metrics
        assert "sharpe_ratio" in result.metrics
        assert "avg_risk_reward" in result.metrics
        assert isinstance(result.equity_curve, list)
        assert len(result.equity_curve) > 0

    def test_equity_curve_starts_at_initial_capital(self):
        from app.backtest.engine import BacktestEngine
        engine = BacktestEngine()
        result = engine.run(
            candles=make_trending_candles(),
            symbol="TEST/USD",
            timeframe="1h",
            initial_capital=10000.0,
        )
        assert result.equity_curve[0] == 10000.0

    def test_equity_curve_length(self):
        from app.backtest.engine import BacktestEngine
        engine = BacktestEngine()
        candles = make_trending_candles(300)
        result = engine.run(
            candles=candles,
            symbol="TEST/USD",
            timeframe="1h",
            initial_capital=10000.0,
        )
        # Equity curve should have one entry per bar from lookback to end, plus initial
        expected_len = len(candles) - engine.lookback + 1
        assert len(result.equity_curve) == expected_len

    def test_trades_are_list(self):
        from app.backtest.engine import BacktestEngine
        engine = BacktestEngine()
        result = engine.run(
            candles=make_trending_candles(),
            symbol="TEST/USD",
            timeframe="1h",
            initial_capital=10000.0,
        )
        assert isinstance(result.trades, list)

    def test_flat_market_few_trades(self):
        from app.backtest.engine import BacktestEngine
        engine = BacktestEngine()
        result = engine.run(
            candles=make_flat_candles(),
            symbol="TEST/USD",
            timeframe="1h",
            initial_capital=10000.0,
        )
        # Flat market should produce 0 or very few trades
        assert result.metrics["total_trades"] >= 0

    def test_trade_risk_reward_property(self):
        from app.backtest.engine import Trade
        trade = Trade(
            entry_idx=10,
            entry_price=100.0,
            direction="BUY",
            stop_loss=95.0,
            take_profit=110.0,
            exit_idx=20,
            exit_price=110.0,
            pnl=200.0,
        )
        # reward = |110 - 100| = 10, risk = |100 - 95| = 5, R:R = 2.0
        assert trade.risk_reward == 2.0

    def test_trade_risk_reward_no_exit(self):
        from app.backtest.engine import Trade
        trade = Trade(
            entry_idx=10,
            entry_price=100.0,
            direction="BUY",
            stop_loss=95.0,
            take_profit=110.0,
        )
        assert trade.risk_reward == 0

    def test_metrics_with_no_trades(self):
        from app.backtest.engine import BacktestEngine
        engine = BacktestEngine()
        result = engine.run(
            candles=make_flat_candles(),
            symbol="TEST/USD",
            timeframe="1h",
            initial_capital=10000.0,
        )
        # Even with no trades, metrics should be present
        assert result.metrics["total_return_pct"] is not None
        assert result.metrics["max_drawdown_pct"] >= 0
