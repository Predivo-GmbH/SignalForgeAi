"""
Walk-Forward Optimizer (WFO).

Splits historical data into train/test folds, runs a grid search over
parameter combinations on the training set, selects the best params,
then validates them on the out-of-sample test set.

This avoids overfitting by ensuring the chosen parameters generalize
to unseen data across multiple time periods.
"""

import itertools
from dataclasses import dataclass

import pandas as pd

from app.backtest.engine import BacktestEngine
from app.engine.layers.risk import RiskConfig


@dataclass
class WFOResult:
    """Result container for walk-forward optimization."""

    best_params: dict
    out_of_sample_metrics: dict
    fold_results: list[dict]
    all_results: list[dict]


class WalkForwardOptimizer:
    """
    Walk-forward optimization: split data into folds, optimize on train,
    validate on test, select params that perform consistently.
    """

    def optimize(
        self,
        candles: pd.DataFrame,
        symbol: str,
        timeframe: str,
        param_grid: dict[str, list],
        n_folds: int = 3,
        train_pct: float = 0.7,
        initial_capital: float = 10000,
    ) -> WFOResult:
        """
        Grid search with walk-forward validation.

        param_grid example: {
            "atr_sl_multiplier": [1.5, 2.0, 2.5],
            "min_confluence": [40, 50, 60]
        }

        Scoring: profit_factor * (1 - max_drawdown/100)
        This rewards profitability while penalizing drawdown.
        """
        # 1. Generate all parameter combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combos = [dict(zip(param_names, vals)) for vals in itertools.product(*param_values)]

        # 2. Split candles into n_folds anchored walk-forward windows
        folds = self._create_folds(candles, n_folds, train_pct)

        # 3. Run grid search across all folds on training data
        all_results: list[dict] = []
        combo_scores: dict[int, list[float]] = {i: [] for i in range(len(combos))}

        for fold_idx, (train_data, _test_data) in enumerate(folds):
            for combo_idx, params in enumerate(combos):
                engine = self._build_engine(params)
                result = engine.run(train_data, symbol, timeframe, initial_capital)
                score = self._score_result(result.metrics)
                combo_scores[combo_idx].append(score)
                all_results.append({
                    "fold": fold_idx,
                    "params": params.copy(),
                    "metrics": result.metrics,
                    "score": score,
                })

        # 4. Pick best params: highest average score across folds
        avg_scores = {
            idx: sum(scores) / len(scores) if scores else 0
            for idx, scores in combo_scores.items()
        }
        best_combo_idx = max(avg_scores, key=avg_scores.get)
        best_params = combos[best_combo_idx]

        # 5. Validate best params on each fold's test set (out-of-sample)
        fold_results: list[dict] = []
        oos_metrics_list: list[dict] = []

        for fold_idx, (_train_data, test_data) in enumerate(folds):
            engine = self._build_engine(best_params)
            result = engine.run(test_data, symbol, timeframe, initial_capital)
            fold_result = {
                "fold": fold_idx,
                "params": best_params.copy(),
                "oos_metrics": result.metrics,
                "oos_score": self._score_result(result.metrics),
            }
            fold_results.append(fold_result)
            oos_metrics_list.append(result.metrics)

        # 6. Aggregate out-of-sample metrics
        out_of_sample_metrics = self._aggregate_metrics(oos_metrics_list)

        return WFOResult(
            best_params=best_params,
            out_of_sample_metrics=out_of_sample_metrics,
            fold_results=fold_results,
            all_results=all_results,
        )

    def _create_folds(
        self,
        candles: pd.DataFrame,
        n_folds: int,
        train_pct: float,
    ) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Create walk-forward folds. Each fold uses an expanding or sliding
        window: the first fold starts at the beginning, subsequent folds
        shift forward.
        """
        n = len(candles)
        fold_size = n // n_folds
        folds = []

        for i in range(n_folds):
            start = i * fold_size
            end = min(start + fold_size, n) if i < n_folds - 1 else n
            fold_data = candles.iloc[start:end].reset_index(drop=True)
            split = int(len(fold_data) * train_pct)
            train = fold_data.iloc[:split].reset_index(drop=True)
            test = fold_data.iloc[split:].reset_index(drop=True)
            folds.append((train, test))

        return folds

    @staticmethod
    def _build_engine(params: dict) -> BacktestEngine:
        """Build a BacktestEngine from a parameter dict."""
        risk_config = RiskConfig(
            atr_sl_multiplier=params.get("atr_sl_multiplier", 2.0),
            max_risk_per_trade=params.get("max_risk_per_trade", 0.02),
            min_risk_reward=params.get("min_risk_reward", 1.5),
        )
        return BacktestEngine(
            risk_config=risk_config,
            min_confluence=params.get("min_confluence", 50),
            lookback=params.get("lookback", 200),
        )

    @staticmethod
    def _score_result(metrics: dict) -> float:
        """
        Score a backtest result for optimization.
        Formula: profit_factor * (1 - max_drawdown/100)

        This penalizes high drawdown even if profit factor is good,
        and rewards consistent returns.
        """
        pf = metrics.get("profit_factor", 0)
        dd = metrics.get("max_drawdown_pct", 0)
        # Handle inf profit factor (no losses) — cap it
        if pf == float("inf"):
            pf = 10.0
        return pf * (1 - dd / 100)

    @staticmethod
    def _aggregate_metrics(metrics_list: list[dict]) -> dict:
        """Average metrics across folds."""
        if not metrics_list:
            return {}
        keys = metrics_list[0].keys()
        aggregated = {}
        for key in keys:
            values = [m[key] for m in metrics_list]
            if all(isinstance(v, (int, float)) for v in values):
                # Handle inf values
                finite_vals = [v for v in values if v != float("inf")]
                if finite_vals:
                    aggregated[key] = sum(finite_vals) / len(finite_vals)
                else:
                    aggregated[key] = float("inf")
            else:
                aggregated[key] = values[0]
        return aggregated
