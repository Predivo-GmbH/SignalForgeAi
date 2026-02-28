"""Celery task for running backtests asynchronously."""

from app.worker import celery_app


@celery_app.task
def run_backtest_task(symbol: str, timeframe: str, days: int, params: dict | None = None):
    """Run a backtest with synthetic data and return metrics.

    In production, candle data will come from CandleStorage / CCXT ingestion.
    For now, generates synthetic price data so the engine can be exercised
    without a live data connection.
    """
    import numpy as np
    import pandas as pd

    from app.backtest.engine import BacktestEngine

    rng = np.random.default_rng()
    n = max(days * 24, 300)  # at least 300 bars for indicators
    close = 100 + np.arange(n, dtype=float) * 0.1 + rng.normal(0, 0.5, n)
    high = close + rng.uniform(0.5, 2, n)
    low = close - rng.uniform(0.5, 2, n)
    candles = pd.DataFrame(
        {
            "open": close,
            "high": high,
            "low": low,
            "close": close,
            "volume": rng.uniform(1000, 5000, n),
        }
    )

    engine = BacktestEngine(**(params or {}))
    result = engine.run(candles, symbol, timeframe)

    # Sanitise metrics: replace inf/-inf/NaN with JSON-safe values
    import math

    sanitised_metrics = {}
    for k, v in result.metrics.items():
        if isinstance(v, float) and (math.isinf(v) or math.isnan(v)):
            sanitised_metrics[k] = None
        else:
            sanitised_metrics[k] = v

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "days": days,
        "metrics": sanitised_metrics,
        "trade_count": len(result.trades),
    }
