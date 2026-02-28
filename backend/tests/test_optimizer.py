import numpy as np
import pandas as pd


def make_trending_candles(n=500):
    """Generate trending upward candles with enough data for walk-forward folds."""
    rng = np.random.default_rng(42)
    close = 100 + np.arange(n) * 0.3 + rng.normal(0, 0.5, n)
    high = close + rng.uniform(0.5, 2, n)
    low = close - rng.uniform(0.5, 2, n)
    return pd.DataFrame({
        "open": close,
        "high": high,
        "low": low,
        "close": close,
        "volume": rng.uniform(1000, 5000, n),
    })


class TestWalkForwardOptimizer:
    def test_returns_wfo_result(self):
        from app.backtest.optimizer import WalkForwardOptimizer, WFOResult

        wfo = WalkForwardOptimizer()
        result = wfo.optimize(
            candles=make_trending_candles(500),
            symbol="TEST/USD",
            timeframe="1h",
            param_grid={"atr_sl_multiplier": [1.5, 2.0, 2.5], "min_confluence": [40, 50]},
        )
        assert isinstance(result, WFOResult)

    def test_returns_best_params(self):
        from app.backtest.optimizer import WalkForwardOptimizer

        wfo = WalkForwardOptimizer()
        result = wfo.optimize(
            candles=make_trending_candles(500),
            symbol="TEST/USD",
            timeframe="1h",
            param_grid={"atr_sl_multiplier": [1.5, 2.0], "min_confluence": [40, 50]},
        )
        assert "atr_sl_multiplier" in result.best_params
        assert "min_confluence" in result.best_params

    def test_out_of_sample_metrics(self):
        from app.backtest.optimizer import WalkForwardOptimizer

        wfo = WalkForwardOptimizer()
        result = wfo.optimize(
            candles=make_trending_candles(500),
            symbol="TEST/USD",
            timeframe="1h",
            param_grid={"atr_sl_multiplier": [2.0], "min_confluence": [50]},
        )
        assert isinstance(result.out_of_sample_metrics, dict)

    def test_fold_results_returned(self):
        from app.backtest.optimizer import WalkForwardOptimizer

        wfo = WalkForwardOptimizer()
        result = wfo.optimize(
            candles=make_trending_candles(500),
            symbol="TEST/USD",
            timeframe="1h",
            param_grid={"atr_sl_multiplier": [2.0], "min_confluence": [50]},
            n_folds=3,
        )
        assert len(result.fold_results) == 3

    def test_all_results_populated(self):
        from app.backtest.optimizer import WalkForwardOptimizer

        wfo = WalkForwardOptimizer()
        result = wfo.optimize(
            candles=make_trending_candles(500),
            symbol="TEST/USD",
            timeframe="1h",
            param_grid={"atr_sl_multiplier": [1.5, 2.0], "min_confluence": [40, 50]},
            n_folds=2,
        )
        # 4 combos x 2 folds = 8 train results
        assert len(result.all_results) == 4 * 2

    def test_best_params_are_from_grid(self):
        from app.backtest.optimizer import WalkForwardOptimizer

        wfo = WalkForwardOptimizer()
        result = wfo.optimize(
            candles=make_trending_candles(500),
            symbol="TEST/USD",
            timeframe="1h",
            param_grid={"atr_sl_multiplier": [1.5, 2.0, 2.5], "min_confluence": [40, 50, 60]},
        )
        assert result.best_params["atr_sl_multiplier"] in [1.5, 2.0, 2.5]
        assert result.best_params["min_confluence"] in [40, 50, 60]

    def test_fold_results_have_oos_metrics(self):
        from app.backtest.optimizer import WalkForwardOptimizer

        wfo = WalkForwardOptimizer()
        result = wfo.optimize(
            candles=make_trending_candles(500),
            symbol="TEST/USD",
            timeframe="1h",
            param_grid={"atr_sl_multiplier": [2.0], "min_confluence": [50]},
            n_folds=2,
        )
        for fold in result.fold_results:
            assert "oos_metrics" in fold
            assert "oos_score" in fold
            assert isinstance(fold["oos_metrics"], dict)
