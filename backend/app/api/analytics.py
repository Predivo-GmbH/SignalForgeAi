"""Analytics API — equity curves, risk metrics, and correlation."""

import numpy as np
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.models.trade import Trade

router = APIRouter(tags=["analytics"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class EquityPoint(BaseModel):
    date: str
    equity: float
    drawdown_pct: float


class EquityCurveResponse(BaseModel):
    points: list[EquityPoint]
    total_return_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float | None
    sortino_ratio: float | None
    calmar_ratio: float | None


class CorrelationResponse(BaseModel):
    symbol_a: str
    symbol_b: str
    correlation: float
    data_points: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def compute_correlation(prices_a: list[float], prices_b: list[float]) -> float:
    """Compute Pearson correlation of returns between two price series."""
    a = np.array(prices_a)
    b = np.array(prices_b)
    min_len = min(len(a), len(b))
    a, b = a[-min_len:], b[-min_len:]
    if len(a) < 2:
        return 0.0
    ret_a = np.diff(a) / a[:-1]
    ret_b = np.diff(b) / b[:-1]
    if np.std(ret_a) == 0 or np.std(ret_b) == 0:
        return 0.0
    return float(np.corrcoef(ret_a, ret_b)[0, 1])


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/analytics/equity", response_model=EquityCurveResponse)
async def get_equity_curve(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Build equity curve from closed trades."""
    result = await db.execute(
        select(Trade)
        .where(Trade.user_id == user_id, Trade.pnl.is_not(None))
        .order_by(Trade.exit_time.asc())
    )
    trades = list(result.scalars().all())

    if not trades:
        return EquityCurveResponse(
            points=[],
            total_return_pct=0.0,
            max_drawdown_pct=0.0,
            sharpe_ratio=None,
            sortino_ratio=None,
            calmar_ratio=None,
        )

    # Build equity curve
    initial_equity = 10_000.0
    equity = initial_equity
    peak = equity
    points: list[EquityPoint] = []
    returns: list[float] = []

    for trade in trades:
        pnl = trade.pnl or 0.0
        ret = pnl / equity if equity > 0 else 0.0
        returns.append(ret)
        equity += pnl
        peak = max(peak, equity)
        dd_pct = ((peak - equity) / peak * 100) if peak > 0 else 0.0
        date_str = (
            trade.exit_time.isoformat() if trade.exit_time else trade.created_at.isoformat()
        )
        points.append(EquityPoint(
            date=date_str, equity=round(equity, 2), drawdown_pct=round(dd_pct, 2),
        ))

    total_return_pct = ((equity - initial_equity) / initial_equity) * 100
    max_drawdown_pct = max(p.drawdown_pct for p in points) if points else 0.0

    # Risk metrics
    ret_arr = np.array(returns)
    sharpe = _sharpe_ratio(ret_arr)
    sortino = _sortino_ratio(ret_arr)
    calmar = (
        (total_return_pct / max_drawdown_pct) if max_drawdown_pct > 0 else None
    )

    return EquityCurveResponse(
        points=points,
        total_return_pct=round(total_return_pct, 2),
        max_drawdown_pct=round(max_drawdown_pct, 2),
        sharpe_ratio=round(sharpe, 4) if sharpe is not None else None,
        sortino_ratio=round(sortino, 4) if sortino is not None else None,
        calmar_ratio=round(calmar, 4) if calmar is not None else None,
    )


@router.get("/analytics/correlation", response_model=CorrelationResponse)
async def get_correlation(
    symbol_a: str = Query(..., description="First symbol"),
    symbol_b: str = Query(..., description="Second symbol"),
    _user_id: str = Depends(get_current_user),
):
    """Return correlation between two symbols (synthetic data for now)."""
    # Generate synthetic price data seeded by symbol names for consistency
    seed = hash(symbol_a + symbol_b) % (2**31)
    rng = np.random.default_rng(seed)
    n = 100
    prices_a = list(np.cumsum(rng.standard_normal(n) * 0.5) + 100)
    prices_b = list(np.cumsum(rng.standard_normal(n) * 0.5) + 100)
    corr = compute_correlation(prices_a, prices_b)

    return CorrelationResponse(
        symbol_a=symbol_a,
        symbol_b=symbol_b,
        correlation=round(corr, 4),
        data_points=n,
    )


# ---------------------------------------------------------------------------
# Private risk-metric helpers
# ---------------------------------------------------------------------------

def _sharpe_ratio(returns: np.ndarray, risk_free: float = 0.0) -> float | None:
    """Annualised Sharpe ratio (assumes daily returns)."""
    if len(returns) < 2:
        return None
    excess = returns - risk_free
    std = np.std(excess, ddof=1)
    if std == 0:
        return None
    return float(np.mean(excess) / std * np.sqrt(252))


def _sortino_ratio(returns: np.ndarray, risk_free: float = 0.0) -> float | None:
    """Annualised Sortino ratio (downside deviation only)."""
    if len(returns) < 2:
        return None
    excess = returns - risk_free
    downside = excess[excess < 0]
    if len(downside) == 0:
        return None
    down_std = np.std(downside, ddof=1)
    if down_std == 0:
        return None
    return float(np.mean(excess) / down_std * np.sqrt(252))
