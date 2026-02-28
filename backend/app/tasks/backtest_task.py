"""Celery task for running backtests asynchronously."""

import logging

from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task
def run_backtest_task(
    symbol: str,
    timeframe: str,
    days: int,
    params: dict | None = None,
    user_id: str | None = None,
):
    """Run a backtest with synthetic data and return metrics.

    In production, candle data will come from CandleStorage / CCXT ingestion.
    For now, generates synthetic price data so the engine can be exercised
    without a live data connection.

    If *user_id* is provided, the results are persisted to the BacktestResult
    table for later retrieval via ``GET /api/backtests``.
    """
    import math

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
    sanitised_metrics = {}
    for k, v in result.metrics.items():
        if isinstance(v, float) and (math.isinf(v) or math.isnan(v)):
            sanitised_metrics[k] = None
        else:
            sanitised_metrics[k] = v

    trade_count = len(result.trades)
    win_rate = sanitised_metrics.get("win_rate")
    sharpe = sanitised_metrics.get("sharpe_ratio")
    max_dd = sanitised_metrics.get("max_drawdown")
    total_pnl = sanitised_metrics.get("total_pnl")

    # Persist to DB if user_id is provided
    if user_id:
        try:
            import asyncio

            asyncio.run(
                _persist_backtest(
                    user_id=user_id,
                    symbol=symbol,
                    timeframe=timeframe,
                    days=days,
                    metrics=sanitised_metrics,
                    trade_count=trade_count,
                    win_rate=win_rate,
                    sharpe_ratio=sharpe,
                    max_drawdown=max_dd,
                    total_pnl=total_pnl,
                )
            )
        except Exception:
            logger.exception("Failed to persist backtest result for user %s", user_id)

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "days": days,
        "metrics": sanitised_metrics,
        "trade_count": trade_count,
    }


async def _persist_backtest(
    *,
    user_id: str,
    symbol: str,
    timeframe: str,
    days: int,
    metrics: dict,
    trade_count: int,
    win_rate: float | None,
    sharpe_ratio: float | None,
    max_drawdown: float | None,
    total_pnl: float | None,
) -> None:
    """Save a BacktestResult row to the database."""
    import uuid

    from app.core.database import async_session
    from app.models.backtest_result import BacktestResult

    async with async_session() as db:
        row = BacktestResult(
            user_id=uuid.UUID(user_id),
            symbol=symbol,
            timeframe=timeframe,
            days=days,
            metrics=metrics,
            trade_count=trade_count,
            win_rate=win_rate,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            total_pnl=total_pnl,
        )
        db.add(row)
        await db.commit()
        logger.info("Persisted backtest result for user %s (%s %s)", user_id, symbol, timeframe)
