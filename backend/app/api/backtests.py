"""Backtest API endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(tags=["backtests"])


class BacktestRequest(BaseModel):
    symbol: str
    timeframe: str
    days: int = Field(default=30, ge=1, le=365)
    params: dict | None = None


class WFORequest(BaseModel):
    symbol: str
    timeframe: str
    days: int = Field(default=90, ge=30, le=365)
    n_folds: int = Field(default=3, ge=2, le=10)
    train_pct: float = Field(default=0.7, ge=0.5, le=0.9)
    param_grid: dict = Field(
        default={
            "atr_sl_multiplier": [1.5, 2.0, 2.5],
            "min_confluence": [40, 50, 60],
        }
    )


@router.post("/backtests")
async def run_backtest(body: BacktestRequest):
    """Run a backtest synchronously (Celery async dispatch when broker is available)."""
    from app.tasks.backtest_task import run_backtest_task

    # Run synchronously for now -- when Celery broker is running,
    # switch to: task = run_backtest_task.delay(...)
    result = run_backtest_task(body.symbol, body.timeframe, body.days, body.params)
    return result


@router.get("/backtests")
async def list_backtests():
    """List past backtest results (stored in DB in future)."""
    return []


@router.post("/backtests/optimize")
async def run_walk_forward(body: WFORequest):
    """Run walk-forward optimization."""
    import numpy as np
    import pandas as pd

    from app.backtest.optimizer import WalkForwardOptimizer

    np.random.seed(42)
    n = body.days * 24
    dates = pd.date_range(end=pd.Timestamp.now(), periods=n, freq="1h")
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    candles = pd.DataFrame(
        {
            "open": close + np.random.randn(n) * 0.1,
            "high": close + abs(np.random.randn(n) * 0.3),
            "low": close - abs(np.random.randn(n) * 0.3),
            "close": close,
            "volume": np.random.randint(100, 10000, n).astype(float),
        },
        index=dates,
    )

    optimizer = WalkForwardOptimizer()
    result = optimizer.optimize(
        candles=candles,
        symbol=body.symbol,
        timeframe=body.timeframe,
        param_grid=body.param_grid,
        n_folds=body.n_folds,
        train_pct=body.train_pct,
    )

    def sanitize(v):
        if isinstance(v, float) and (np.isinf(v) or np.isnan(v)):
            return None
        return v

    def sanitize_dict(d):
        return {k: sanitize(v) for k, v in d.items()}

    return {
        "best_params": result.best_params,
        "out_of_sample_metrics": sanitize_dict(result.out_of_sample_metrics),
        "fold_results": [
            {**fr, "oos_metrics": sanitize_dict(fr["oos_metrics"])}
            for fr in result.fold_results
        ],
    }
