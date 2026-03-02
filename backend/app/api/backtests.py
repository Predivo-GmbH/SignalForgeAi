"""Backtest API endpoints."""

import logging
import uuid as _uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db

logger = logging.getLogger(__name__)

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


class StrategyBacktestRequest(BaseModel):
    """Backtest an entire AI Advisor strategy (all symbols + risk config)."""
    strategy_id: str | None = None
    plan: dict | None = None
    days: int = Field(default=90, ge=7, le=365)
    ai_enhanced: bool = False

    @model_validator(mode="after")
    def require_source(self):
        if not self.strategy_id and not self.plan:
            raise ValueError("Provide either strategy_id or plan")
        return self


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


@router.post("/backtests/strategy")
async def run_strategy_backtest(
    body: StrategyBacktestRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Backtest an entire AI Advisor strategy against historical data.

    Accepts either a deployed strategy_id or a raw plan (pre-deployment).
    Runs the signal pipeline on every symbol in the strategy with its
    exact risk configuration, then aggregates into portfolio-level metrics.
    """
    from app.backtest.portfolio_runner import run_portfolio_backtest

    config: dict = {}
    strategy_name = "Strategy"

    if body.strategy_id:
        from sqlalchemy import select

        from app.models.strategy import Strategy

        uid = _uuid.UUID(user_id)
        sid = _uuid.UUID(body.strategy_id)
        result = await db.execute(
            select(Strategy).where(Strategy.id == sid, Strategy.user_id == uid)
        )
        strategy = result.scalar_one_or_none()
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found",
            )
        config = strategy.config or {}
        strategy_name = strategy.name

    elif body.plan:
        plan = body.plan
        selected_cryptos = plan.get("selected_cryptos", [])
        if not selected_cryptos:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Plan has no selected cryptos",
            )

        # Support both new (strategy_config) and legacy (risk_config) plan formats
        strategy_config = plan.get("strategy_config", plan.get("risk_config", {}))
        symbols = [c["symbol"] for c in selected_cryptos]

        config = {**strategy_config}
        config["symbols"] = symbols
        config.setdefault("timeframes", ["1h"])
        config.setdefault("account_equity", 10000)
        config.setdefault("min_confluence", 50)
        config.setdefault("max_risk_per_trade", 0.02)
        config.setdefault("max_daily_loss", 0.06)
        config.setdefault("atr_sl_multiplier", 2.0)
        config.setdefault("min_risk_reward", 1.5)

        strategy_name = "AI Advisor — Optimal"

    try:
        result = run_portfolio_backtest(
            config=config,
            days=body.days,
            strategy_name=strategy_name,
            ai_enhanced=body.ai_enhanced,
        )
    except Exception as e:
        logger.exception("Strategy backtest failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Strategy backtest failed: {e}",
        )

    return result
