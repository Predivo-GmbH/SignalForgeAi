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
    """Run a backtest using real candle data when available.

    Data source priority:
    1. Database (previously ingested candles)
    2. Live fetch from CCXT/Binance
    3. Synthetic data (fallback for offline/testing)

    If *user_id* is provided, the results are persisted to the BacktestResult
    table for later retrieval via ``GET /api/backtests``.
    """
    import asyncio
    import math

    import numpy as np
    import pandas as pd

    from app.backtest.engine import BacktestEngine

    n = max(days * 24, 300)  # at least 300 bars for indicators

    # Try to load real candles (async DB query or sync CCXT fetch)
    candles = None
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is None:
        # No event loop — safe to use asyncio.run() (Celery worker context)
        candles = asyncio.run(load_candles(symbol, timeframe, n))
    else:
        # Already inside an event loop (FastAPI) — use sync CCXT fetch
        candles = load_candles_sync(symbol, timeframe, n)

    if candles is None or len(candles) < 300:
        logger.warning(
            "Not enough real data for %s %s (%d candles) — using synthetic fallback",
            symbol, timeframe, len(candles) if candles is not None else 0,
        )
        rng = np.random.default_rng()
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

    # Return flat structure matching frontend BacktestResult interface
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "days": days,
        "total_return": sanitised_metrics.get("total_return_pct", 0),
        "win_rate": sanitised_metrics.get("win_rate", 0),
        "profit_factor": sanitised_metrics.get("profit_factor", 0),
        "max_drawdown": sanitised_metrics.get("max_drawdown_pct", 0),
        "total_trades": trade_count,
        "sharpe_ratio": sanitised_metrics.get("sharpe_ratio"),
        "sortino_ratio": sanitised_metrics.get("sortino_ratio"),
        "equity_curve": [
            {"time": str(i), "value": v}
            for i, v in enumerate(result.equity_curve)
        ] if result.equity_curve else [],
    }


def load_candles_sync(symbol: str, timeframe: str, limit: int):
    """Sync fallback: fetch candles directly from CCXT (no DB)."""
    try:
        from app.data.ingestion import CCXTIngestion

        ingestion = CCXTIngestion("binance")
        df = ingestion.fetch_candles(symbol, timeframe, limit=limit)
        if not df.empty and len(df) >= 300:
            logger.info("Fetched %d candles from CCXT (sync) for %s %s", len(df), symbol, timeframe)
            return df
    except Exception as e:
        logger.warning("Sync CCXT candle fetch failed: %s", e)
    return None


async def load_candles(symbol: str, timeframe: str, limit: int):
    """Try to load real candles from DB, then CCXT, return DataFrame or None."""
    import pandas as pd

    # 1. Try database
    try:
        from app.core.database import task_session
        from app.data.storage import CandleStorage

        async with task_session() as db:
            rows = await CandleStorage.load_candles_db(db, symbol, timeframe, limit=limit)
            if len(rows) >= 300:
                logger.info("Loaded %d candles from DB for %s %s", len(rows), symbol, timeframe)
                return pd.DataFrame(rows)
    except Exception as e:
        logger.warning("DB candle load failed: %s", e)

    # 2. Try live CCXT fetch
    try:
        from app.data.ingestion import CCXTIngestion

        ingestion = CCXTIngestion("binance")
        df = ingestion.fetch_candles(symbol, timeframe, limit=limit)
        if not df.empty and len(df) >= 300:
            logger.info("Fetched %d candles from CCXT for %s %s", len(df), symbol, timeframe)
            return df
    except Exception as e:
        logger.warning("CCXT candle fetch failed: %s", e)

    return None


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

    from app.core.database import task_session
    from app.models.backtest_result import BacktestResult

    async with task_session() as db:
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
