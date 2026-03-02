"""Portfolio backtest runner.

Runs the BacktestEngine across all symbols in an AI Advisor strategy config
and aggregates results into a portfolio-level view.
"""

import logging
import math

import numpy as np
import pandas as pd

from app.backtest.engine import BacktestEngine

logger = logging.getLogger(__name__)


def run_portfolio_backtest(
    config: dict,
    days: int,
    strategy_name: str = "Strategy",
    ai_enhanced: bool = False,
) -> dict:
    """Run a backtest for every symbol in a strategy config, then aggregate.

    Parameters
    ----------
    config : dict
        Full strategy config (symbols, timeframes, risk params).
        Same shape as Strategy.config / deploy endpoint config.
    days : int
        How many days of historical data to backtest.
    strategy_name : str
        Display name for the strategy (used in response).

    Returns
    -------
    dict
        Portfolio-level and per-symbol backtest results.
    """
    symbols = config.get("symbols", [])
    timeframes = config.get("timeframes", ["1h"])
    account_equity = config.get("account_equity", 10000)

    # Engine params from strategy config
    engine_params = {
        "min_confluence": config.get("min_confluence", 50),
        "atr_sl_mult": config.get("atr_sl_multiplier", 2.0),
        "risk_pct": config.get("max_risk_per_trade", 0.02),
    }

    if not symbols:
        return _empty_result(strategy_name, config, days)

    # Divide capital equally across symbols
    per_symbol_capital = account_equity / len(symbols)
    primary_tf = timeframes[0] if timeframes else "1h"
    n_bars = max(days * _bars_per_day(primary_tf), 300)

    per_symbol_results = []
    all_equity_curves = []

    for symbol in symbols:
        candles = _load_candles_for_symbol(symbol, primary_tf, n_bars)

        if candles is None or len(candles) < 300:
            logger.warning(
                "Skipping %s: not enough candle data (%d bars)",
                symbol,
                len(candles) if candles is not None else 0,
            )
            per_symbol_results.append(_empty_symbol_result(symbol))
            continue

        engine = BacktestEngine(**engine_params, ai_enhanced=ai_enhanced)
        result = engine.run(
            candles, symbol, primary_tf, initial_capital=per_symbol_capital,
        )

        metrics = _sanitize_metrics(result.metrics)
        sym_result: dict = {
            "symbol": symbol,
            "total_return": metrics.get("total_return_pct", 0),
            "win_rate": metrics.get("win_rate", 0),
            "profit_factor": metrics.get("profit_factor", 0),
            "max_drawdown": metrics.get("max_drawdown_pct", 0),
            "total_trades": metrics.get("total_trades", 0),
            "sharpe_ratio": metrics.get("sharpe_ratio"),
            "sortino_ratio": metrics.get("sortino_ratio"),
        }
        if ai_enhanced:
            sym_result["ai_calls"] = metrics.get("ai_calls", 0)
            sym_result["ai_rejections"] = metrics.get("ai_rejections", 0)
        per_symbol_results.append(sym_result)
        all_equity_curves.append(result.equity_curve)

    # Aggregate portfolio
    portfolio = _aggregate_portfolio(
        per_symbol_results, all_equity_curves, account_equity,
    )

    preset = config.get("strategy_preset", _infer_preset(config))

    result_dict = {
        "strategy_name": strategy_name,
        "preset": preset,
        "symbols_count": len(symbols),
        "days": days,
        "config_summary": {
            "min_confluence": engine_params["min_confluence"],
            "max_risk_per_trade": engine_params["risk_pct"],
            "atr_sl_multiplier": engine_params["atr_sl_mult"],
            "timeframes": timeframes,
            "account_equity": account_equity,
        },
        "portfolio": portfolio,
        "per_symbol": per_symbol_results,
    }

    if ai_enhanced:
        result_dict["ai_enhanced"] = True
        portfolio["ai_calls"] = sum(s.get("ai_calls", 0) for s in per_symbol_results)
        portfolio["ai_rejections"] = sum(s.get("ai_rejections", 0) for s in per_symbol_results)

    return result_dict


def _load_candles_for_symbol(
    symbol: str, timeframe: str, limit: int,
) -> pd.DataFrame | None:
    """Load candles using the shared loader from backtest_task."""
    from app.tasks.backtest_task import load_candles_sync

    return load_candles_sync(symbol, timeframe, limit)


def _aggregate_portfolio(
    per_symbol: list[dict],
    equity_curves: list[list[float]],
    initial_capital: float,
) -> dict:
    """Combine per-symbol results into portfolio-level metrics."""
    if not equity_curves:
        return _empty_portfolio_metrics()

    # Combine equity curves: sum the change from each symbol's curve
    # Each curve starts at per_symbol_capital; we combine into one portfolio curve
    max_len = max(len(ec) for ec in equity_curves)
    combined = np.full(max_len, 0.0)

    for ec in equity_curves:
        arr = np.array(ec)
        # Pad shorter curves by holding their final value
        if len(arr) < max_len:
            arr = np.pad(arr, (0, max_len - len(arr)), constant_values=arr[-1])
        combined += arr

    combined_list = combined.tolist()

    # Aggregate trade-level metrics
    total_trades = sum(s.get("total_trades", 0) for s in per_symbol)
    symbols_with_trades = [s for s in per_symbol if s.get("total_trades", 0) > 0]

    if symbols_with_trades:
        # Weighted average win rate by trade count
        total_wins_weighted = sum(
            s["win_rate"] * s["total_trades"] for s in symbols_with_trades
        )
        portfolio_win_rate = total_wins_weighted / total_trades if total_trades else 0
    else:
        portfolio_win_rate = 0

    # Portfolio return from combined equity curve
    total_return = (combined_list[-1] - initial_capital) / initial_capital * 100

    # Max drawdown from combined curve
    peak = combined_list[0]
    max_dd = 0.0
    for val in combined_list:
        if val > peak:
            peak = val
        dd = (peak - val) / peak * 100 if peak > 0 else 0
        max_dd = max(max_dd, dd)

    # Sharpe from combined curve
    eq = np.array(combined_list)
    returns = np.diff(eq) / eq[:-1]
    sharpe = 0.0
    if len(returns) > 0 and np.std(returns) > 0:
        sharpe = float(np.mean(returns) / np.std(returns) * np.sqrt(252))

    # Sortino
    sortino = 0.0
    if len(returns) > 0:
        downside = returns[returns < 0]
        if len(downside) > 0 and np.std(downside) > 0:
            sortino = float(np.mean(returns) / np.std(downside) * np.sqrt(252))

    # Profit factor: average across symbols (weighted)
    pf_values = [
        s["profit_factor"] for s in symbols_with_trades
        if s.get("profit_factor") is not None and s["profit_factor"] != float("inf")
    ]
    profit_factor = float(np.mean(pf_values)) if pf_values else 0

    return {
        "total_return": _sanitize_float(total_return),
        "win_rate": _sanitize_float(portfolio_win_rate),
        "profit_factor": _sanitize_float(profit_factor),
        "max_drawdown": _sanitize_float(max_dd),
        "total_trades": total_trades,
        "sharpe_ratio": _sanitize_float(sharpe),
        "sortino_ratio": _sanitize_float(sortino),
        "equity_curve": [
            {"time": str(i), "value": round(v, 2)}
            for i, v in enumerate(combined_list)
        ],
    }


def _bars_per_day(timeframe: str) -> int:
    """Approximate number of bars per day for a given timeframe."""
    mapping = {
        "1m": 1440,
        "5m": 288,
        "15m": 96,
        "1h": 24,
        "4h": 6,
        "1D": 1,
        "1d": 1,
    }
    return mapping.get(timeframe, 24)


def _infer_preset(config: dict) -> str:
    """Best-guess preset name from config params."""
    confluence = config.get("min_confluence", 50)
    risk = config.get("max_risk_per_trade", 0.02)
    if confluence >= 70 and risk <= 0.01:
        return "conservative_swing"
    if confluence <= 35 and risk >= 0.03:
        return "aggressive_scalper"
    return "balanced_momentum"


def _sanitize_float(v: float) -> float | None:
    if isinstance(v, float) and (math.isinf(v) or math.isnan(v)):
        return None
    return round(v, 2) if isinstance(v, float) else v


def _sanitize_metrics(metrics: dict) -> dict:
    return {k: _sanitize_float(v) if isinstance(v, float) else v for k, v in metrics.items()}


def _empty_symbol_result(symbol: str) -> dict:
    return {
        "symbol": symbol,
        "total_return": 0,
        "win_rate": 0,
        "profit_factor": 0,
        "max_drawdown": 0,
        "total_trades": 0,
        "sharpe_ratio": None,
        "sortino_ratio": None,
    }


def _empty_portfolio_metrics() -> dict:
    return {
        "total_return": 0,
        "win_rate": 0,
        "profit_factor": 0,
        "max_drawdown": 0,
        "total_trades": 0,
        "sharpe_ratio": 0,
        "sortino_ratio": 0,
        "equity_curve": [],
    }


def _empty_result(strategy_name: str, config: dict, days: int) -> dict:
    return {
        "strategy_name": strategy_name,
        "preset": _infer_preset(config),
        "symbols_count": 0,
        "days": days,
        "config_summary": {},
        "portfolio": _empty_portfolio_metrics(),
        "per_symbol": [],
    }
