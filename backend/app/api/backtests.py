"""Backtest API endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(tags=["backtests"])


class BacktestRequest(BaseModel):
    symbol: str
    timeframe: str
    days: int = Field(default=30, ge=1, le=365)
    params: dict | None = None


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
