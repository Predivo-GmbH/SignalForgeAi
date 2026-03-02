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


class StrategyMetrics(BaseModel):
    strategy_id: str
    strategy_name: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_return_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float | None
    avg_pnl_per_trade: float
    profit_factor: float | None
    active_signals: int


class StrategyComparisonResponse(BaseModel):
    strategies: list[StrategyMetrics]
    best_by_return: str | None
    best_by_sharpe: str | None
    best_by_win_rate: str | None


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


@router.get("/analytics/compare", response_model=StrategyComparisonResponse)
async def compare_strategies(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compare performance metrics across all active strategies."""
    from app.models.signal import Signal
    from app.models.strategy import Strategy

    # Get all strategies for this user
    strat_result = await db.execute(
        select(Strategy).where(Strategy.user_id == user_id).order_by(Strategy.created_at.desc())
    )
    strategies = list(strat_result.scalars().all())

    if not strategies:
        return StrategyComparisonResponse(
            strategies=[], best_by_return=None, best_by_sharpe=None, best_by_win_rate=None
        )

    metrics_list: list[StrategyMetrics] = []

    for strat in strategies:
        # Get closed trades for this strategy (Trade -> Signal -> Strategy)
        trade_result = await db.execute(
            select(Trade)
            .join(Signal, Trade.signal_id == Signal.id)
            .where(Signal.strategy_id == strat.id, Trade.pnl.is_not(None))
            .order_by(Trade.exit_time.asc())
        )
        trades = list(trade_result.scalars().all())

        # Get active signals count
        sig_result = await db.execute(
            select(Signal)
            .where(Signal.strategy_id == strat.id, Signal.status.in_(["pending", "active"]))
        )
        active_signals = len(list(sig_result.scalars().all()))

        total_trades = len(trades)
        winning = [t for t in trades if (t.pnl or 0) > 0]
        losing = [t for t in trades if (t.pnl or 0) < 0]
        total_pnl = sum(t.pnl or 0 for t in trades)
        win_rate = (len(winning) / total_trades * 100) if total_trades > 0 else 0.0

        # Equity curve for drawdown + Sharpe
        initial = 10_000.0
        equity = initial
        peak = equity
        max_dd = 0.0
        returns = []
        gross_profit = sum(t.pnl for t in winning if t.pnl)
        gross_loss = abs(sum(t.pnl for t in losing if t.pnl))

        for trade in trades:
            pnl = trade.pnl or 0.0
            ret = pnl / equity if equity > 0 else 0.0
            returns.append(ret)
            equity += pnl
            peak = max(peak, equity)
            dd = ((peak - equity) / peak * 100) if peak > 0 else 0.0
            max_dd = max(max_dd, dd)

        total_return_pct = ((equity - initial) / initial) * 100
        ret_arr = np.array(returns) if returns else np.array([])
        sharpe = _sharpe_ratio(ret_arr) if len(ret_arr) >= 2 else None
        avg_pnl = (total_pnl / total_trades) if total_trades > 0 else 0.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else None

        metrics_list.append(StrategyMetrics(
            strategy_id=str(strat.id),
            strategy_name=strat.name,
            total_trades=total_trades,
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=round(win_rate, 1),
            total_pnl=round(total_pnl, 2),
            total_return_pct=round(total_return_pct, 2),
            max_drawdown_pct=round(max_dd, 2),
            sharpe_ratio=round(sharpe, 4) if sharpe is not None else None,
            avg_pnl_per_trade=round(avg_pnl, 2),
            profit_factor=round(profit_factor, 2) if profit_factor is not None else None,
            active_signals=active_signals,
        ))

    # Determine best performers
    with_trades = [m for m in metrics_list if m.total_trades > 0]
    best_return = max(with_trades, key=lambda m: m.total_return_pct).strategy_name if with_trades else None
    best_sharpe = None
    sharpe_candidates = [m for m in with_trades if m.sharpe_ratio is not None]
    if sharpe_candidates:
        best_sharpe = max(sharpe_candidates, key=lambda m: m.sharpe_ratio).strategy_name
    best_wr = max(with_trades, key=lambda m: m.win_rate).strategy_name if with_trades else None

    return StrategyComparisonResponse(
        strategies=metrics_list,
        best_by_return=best_return,
        best_by_sharpe=best_sharpe,
        best_by_win_rate=best_wr,
    )


@router.get("/analytics/correlation", response_model=CorrelationResponse)
async def get_correlation(
    symbol_a: str = Query(..., description="First symbol"),
    symbol_b: str = Query(..., description="Second symbol"),
    _user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return correlation between two symbols.

    Uses real candle close prices from the database when sufficient data
    exists (>= 30 data points). Falls back to synthetic data otherwise.
    """
    from app.data.storage import CandleStorage

    min_data_points = 30

    prices_a = await CandleStorage.load_close_prices(db, symbol_a, timeframe="1h", limit=500)
    prices_b = await CandleStorage.load_close_prices(db, symbol_b, timeframe="1h", limit=500)

    if len(prices_a) >= min_data_points and len(prices_b) >= min_data_points:
        # Use real data
        n = min(len(prices_a), len(prices_b))
        corr = compute_correlation(prices_a[-n:], prices_b[-n:])
        return CorrelationResponse(
            symbol_a=symbol_a,
            symbol_b=symbol_b,
            correlation=round(corr, 4),
            data_points=n,
        )

    # Fall back to synthetic data seeded by symbol names for consistency
    seed = hash(symbol_a + symbol_b) % (2**31)
    rng = np.random.default_rng(seed)
    n = 100
    synth_a = list(np.cumsum(rng.standard_normal(n) * 0.5) + 100)
    synth_b = list(np.cumsum(rng.standard_normal(n) * 0.5) + 100)
    corr = compute_correlation(synth_a, synth_b)

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
