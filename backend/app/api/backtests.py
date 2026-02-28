"""Backtest API endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db

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
async def run_backtest(
    body: BacktestRequest,
    user_id: str = Depends(get_current_user),
):
    """Run a backtest synchronously (Celery async dispatch when broker is available)."""
    from app.tasks.backtest_task import run_backtest_task

    # Run synchronously for now -- when Celery broker is running,
    # switch to: task = run_backtest_task.delay(...)
    result = run_backtest_task(
        body.symbol, body.timeframe, body.days, body.params, user_id=user_id,
    )
    return result


@router.get("/backtests")
async def list_backtests(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List past backtest results from the database."""
    import uuid

    from sqlalchemy import select

    from app.models.backtest_result import BacktestResult

    result = await db.execute(
        select(BacktestResult)
        .where(BacktestResult.user_id == uuid.UUID(user_id))
        .order_by(BacktestResult.created_at.desc())
        .limit(50)
    )
    rows = result.scalars().all()
    return [
        {
            "id": str(row.id),
            "symbol": row.symbol,
            "timeframe": row.timeframe,
            "days": row.days,
            "metrics": row.metrics,
            "trade_count": row.trade_count,
            "win_rate": row.win_rate,
            "sharpe_ratio": row.sharpe_ratio,
            "max_drawdown": row.max_drawdown,
            "total_pnl": row.total_pnl,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


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
