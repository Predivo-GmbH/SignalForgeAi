"""Paper simulation API — start, monitor, and stop B&H vs SignalForge tests.

Simulation Model
================
Both sides start with the user's real portfolio snapshot.

  B&H value  = sum(initial_qty × current_price)
  SF  value  = B&H value + net trade P&L

With zero trades SF ≡ B&H.  The comparison only diverges when SignalForge
actually executes trades — any difference reflects pure trading alpha.
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models.position import Position
from app.models.signal import Signal
from app.models.simulation import PaperSimulation, SimulationSnapshot
from app.models.strategy import BrokerConnection, Strategy
from app.models.trade import Trade

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/simulation", tags=["simulation"])

# Stablecoins — skip when building symbol pairs
_STABLECOINS = {"USDT", "USDC", "BUSD", "DAI", "TUSD", "FDUSD", "USDP", "USD"}


@router.post("/start")
@limiter.limit("5/minute")
async def start_simulation(
    request: Request,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a new paper simulation using current holdings."""
    uid = uuid.UUID(user_id)

    # Check for existing running simulation
    existing = await db.execute(
        select(PaperSimulation).where(
            PaperSimulation.user_id == uid,
            PaperSimulation.status == "running",
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A simulation is already running. Stop it first.",
        )

    # Fetch current holdings
    from app.api.holdings import (
        _fetch_exchange_holdings,
        _fetch_manual_holdings,
        _fetch_prices,
        _fetch_trading_holdings,
    )

    exchange = await _fetch_exchange_holdings(db, user_id)
    manual = await _fetch_manual_holdings(db, user_id)
    trading = await _fetch_trading_holdings(db, user_id)
    all_holdings = exchange + manual + trading

    if not all_holdings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No holdings found. Connect an exchange or add manual holdings first.",
        )

    # Fetch prices
    unique_symbols = list({h.symbol.upper() for h in all_holdings})
    prices = await _fetch_prices(unique_symbols)

    # Build holdings snapshot with prices and track source exchanges
    holdings_snapshot = []
    total_value = 0.0
    symbols_for_trading: set[str] = set()
    exchange_map: dict[str, str] = {}  # "ALPH/USDT" -> "mexc"

    # Non-exchange sources that should NOT be used as CCXT exchange IDs
    non_exchange_sources = {"manual", "trading"}

    # Collect user's connected exchange names for fallback
    broker_result = await db.execute(
        select(BrokerConnection.broker).where(
            BrokerConnection.user_id == uid,
        ).distinct()
    )
    [row[0] for row in broker_result.all()]

    for h in all_holdings:
        sym = h.symbol.upper()
        info = prices.get(sym, {})
        price = info.get("price") or 0
        value = price * h.quantity if price else 0

        holdings_snapshot.append({
            "symbol": sym,
            "quantity": h.quantity,
            "price_usd": price,
            "value_usd": round(value, 2),
        })
        total_value += value

        # Build trading pairs (skip stablecoins)
        if sym not in _STABLECOINS and price > 0:
            pair = f"{sym}/USDT"
            symbols_for_trading.add(pair)
            # Track which exchange this symbol came from.
            # Only use real exchange names (skip "manual", "trading", etc.).
            if pair not in exchange_map and h.source:
                if h.source not in non_exchange_sources:
                    exchange_map[pair] = h.source

    if total_value < 1.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Portfolio value too low to start a simulation.",
        )

    # Create simulation strategy
    strategy = Strategy(
        id=uuid.uuid4(),
        user_id=uid,
        name=f"Paper Simulation ({datetime.now(timezone.utc).strftime('%b %d')})",
        is_active=True,
        config={
            "symbols": sorted(symbols_for_trading),
            "exchange_map": exchange_map,
            "timeframes": ["1h"],
            "account_equity": round(total_value, 2),
            "min_confluence": 50,
            "atr_sl_multiplier": 2.0,
            "max_risk_per_trade": 0.02,
            "min_risk_reward": 1.5,
            "max_daily_loss": 0.06,
            # Full stack features
            "regime_allocator_enabled": True,
            "regime_allocation_table": "moderate",
            "regime_smoothing_bars": 3,
            "cooldown_hours": 48,
            "trailing_stop_enabled": True,
            "atr_trail_multiplier": 2.0,
            "break_even_enabled": True,
            "break_even_r_multiple": 1.0,
            "drawdown_breaker_enabled": True,
            "max_drawdown_pct": 0.15,
            "cppi_enabled": True,
            "max_hold_hours": 48,
            # Mark as simulation
            "is_simulation": True,
        },
    )
    db.add(strategy)
    await db.flush()

    # Create simulation record
    sim = PaperSimulation(
        id=uuid.uuid4(),
        user_id=uid,
        strategy_id=strategy.id,
        status="running",
        initial_holdings=holdings_snapshot,
        initial_value_usd=round(total_value, 2),
    )
    db.add(sim)

    # Initial snapshot (B&H = SF = starting value)
    snapshot = SimulationSnapshot(
        simulation_id=sim.id,
        bh_value_usd=round(total_value, 2),
        sf_value_usd=round(total_value, 2),
        sf_cash_usd=round(total_value, 2),
        sf_positions_value=0.0,
    )
    db.add(snapshot)

    await db.commit()

    return {
        "id": str(sim.id),
        "status": "running",
        "strategy_id": str(strategy.id),
        "initial_value_usd": round(total_value, 2),
        "holdings_count": len(holdings_snapshot),
        "trading_symbols": sorted(symbols_for_trading),
        "started_at": sim.started_at.isoformat() if sim.started_at else None,
    }


@router.get("/active")
@limiter.limit("60/minute")
async def get_active_simulation(
    request: Request,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the active simulation with snapshots and latest values."""
    uid = uuid.UUID(user_id)

    result = await db.execute(
        select(PaperSimulation).where(
            PaperSimulation.user_id == uid,
            PaperSimulation.status == "running",
        )
    )
    sim = result.scalar_one_or_none()
    if not sim:
        return None

    return await _build_simulation_response(db, sim)


@router.get("/latest")
@limiter.limit("60/minute")
async def get_latest_simulation(
    request: Request,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the most recent simulation (running or stopped)."""
    uid = uuid.UUID(user_id)

    result = await db.execute(
        select(PaperSimulation)
        .where(PaperSimulation.user_id == uid)
        .order_by(PaperSimulation.started_at.desc())
        .limit(1)
    )
    sim = result.scalar_one_or_none()
    if not sim:
        return None

    return await _build_simulation_response(db, sim)


@router.get("/{sim_id}/comparison")
@limiter.limit("60/minute")
async def get_simulation_comparison(
    request: Request,
    sim_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Full comparison data for a simulation."""
    uid = uuid.UUID(user_id)

    result = await db.execute(
        select(PaperSimulation).where(
            PaperSimulation.id == uuid.UUID(sim_id),
            PaperSimulation.user_id == uid,
        )
    )
    sim = result.scalar_one_or_none()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    # Snapshots for equity curves
    snap_result = await db.execute(
        select(SimulationSnapshot)
        .where(SimulationSnapshot.simulation_id == sim.id)
        .order_by(SimulationSnapshot.timestamp.asc())
    )
    snapshots = snap_result.scalars().all()

    # Trade stats (Trade -> Signal -> strategy_id)
    trade_result = await db.execute(
        select(
            func.count(Trade.id).label("count"),
            func.sum(case((Trade.pnl > 0, 1), else_=0)).label("wins"),
            func.coalesce(func.sum(Trade.pnl), 0.0).label("total_pnl"),
        )
        .join(Signal, Trade.signal_id == Signal.id)
        .where(Signal.strategy_id == sim.strategy_id)
    )
    trade_stats = trade_result.one()

    # Open positions count
    pos_count_result = await db.execute(
        select(func.count(Position.id)).where(
            Position.strategy_id == sim.strategy_id,
            Position.is_open == True,  # noqa: E712
        )
    )
    open_positions = pos_count_result.scalar()

    # Calculate drawdowns
    bh_values = [s.bh_value_usd for s in snapshots]
    sf_values = [s.sf_value_usd for s in snapshots]

    initial = sim.initial_value_usd
    latest_bh = bh_values[-1] if bh_values else initial
    latest_sf = sf_values[-1] if sf_values else initial

    return {
        "id": str(sim.id),
        "status": sim.status,
        "initial_value_usd": initial,
        "started_at": sim.started_at.isoformat() if sim.started_at else None,
        "stopped_at": sim.stopped_at.isoformat() if sim.stopped_at else None,
        "equity_curves": [
            {
                "timestamp": s.timestamp.isoformat(),
                "bh_value": s.bh_value_usd,
                "sf_value": s.sf_value_usd,
            }
            for s in snapshots
        ],
        "bh_return_pct": round((latest_bh - initial) / initial * 100, 2) if initial > 0 else 0,
        "sf_return_pct": round((latest_sf - initial) / initial * 100, 2) if initial > 0 else 0,
        "bh_max_drawdown_pct": round(_max_drawdown(bh_values) * 100, 2),
        "sf_max_drawdown_pct": round(_max_drawdown(sf_values) * 100, 2),
        "sf_trade_count": trade_stats.count or 0,
        "sf_win_rate": round(
            (trade_stats.wins / trade_stats.count * 100) if trade_stats.count else 0, 1
        ),
        "sf_total_pnl": round(float(trade_stats.total_pnl or 0), 2),
        "sf_open_positions": open_positions or 0,
    }


@router.post("/{sim_id}/stop")
@limiter.limit("5/minute")
async def stop_simulation(
    request: Request,
    sim_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stop a running simulation and take a final snapshot."""
    uid = uuid.UUID(user_id)

    result = await db.execute(
        select(PaperSimulation).where(
            PaperSimulation.id == uuid.UUID(sim_id),
            PaperSimulation.user_id == uid,
            PaperSimulation.status == "running",
        )
    )
    sim = result.scalar_one_or_none()
    if not sim:
        raise HTTPException(status_code=404, detail="No running simulation found")

    # Close any open positions
    pos_result = await db.execute(
        select(Position).where(
            Position.strategy_id == sim.strategy_id,
            Position.is_open == True,  # noqa: E712
        )
    )
    open_positions = pos_result.scalars().all()

    from app.execution.position_manager import PositionManagerDB

    for pos in open_positions:
        try:
            await PositionManagerDB.close_position(
                db, str(pos.id), pos.current_price or pos.entry_price, "simulation_end"
            )
        except Exception:
            logger.exception("Failed to close position %s during sim stop", pos.id)

    # Deactivate strategy
    strat_result = await db.execute(
        select(Strategy).where(Strategy.id == sim.strategy_id)
    )
    strategy = strat_result.scalar_one_or_none()
    if strategy:
        strategy.is_active = False

    # Take final snapshot
    pnl_result = await db.execute(
        select(func.coalesce(func.sum(Trade.pnl), 0.0))
        .join(Signal, Trade.signal_id == Signal.id)
        .where(Signal.strategy_id == sim.strategy_id)
    )
    realized_pnl = float(pnl_result.scalar())

    # B&H final value — fetch live prices
    from app.api.holdings import _fetch_prices

    bh_symbols = [h["symbol"] for h in (sim.initial_holdings or [])]
    prices = await _fetch_prices(bh_symbols) if bh_symbols else {}

    bh_value = 0.0
    for h in (sim.initial_holdings or []):
        sym = h.get("symbol", "").upper()
        qty = h.get("quantity", 0)
        info = prices.get(sym, {})
        price = info.get("price") or h.get("price_usd", 0)
        bh_value += qty * price

    # SF = B&H + net trade P&L (both sides start with same portfolio)
    sf_value = bh_value + realized_pnl

    final_snapshot = SimulationSnapshot(
        simulation_id=sim.id,
        bh_value_usd=round(bh_value, 2),
        sf_value_usd=round(sf_value, 2),
        sf_cash_usd=round(sf_value, 2),
        sf_positions_value=0.0,
    )
    db.add(final_snapshot)

    # Stop simulation
    sim.status = "stopped"
    sim.stopped_at = datetime.now(timezone.utc)

    await db.commit()

    return await _build_simulation_response(db, sim)


# ---------- Helpers ----------


def _max_drawdown(values: list[float]) -> float:
    """Calculate maximum drawdown from a list of equity values."""
    if len(values) < 2:
        return 0.0
    peak = values[0]
    max_dd = 0.0
    for v in values:
        if v > peak:
            peak = v
        if peak > 0:
            dd = (peak - v) / peak
            if dd > max_dd:
                max_dd = dd
    return max_dd


async def _build_simulation_response(db: AsyncSession, sim: PaperSimulation) -> dict:
    """Build full simulation response with snapshots and trade stats."""
    # Snapshots
    snap_result = await db.execute(
        select(SimulationSnapshot)
        .where(SimulationSnapshot.simulation_id == sim.id)
        .order_by(SimulationSnapshot.timestamp.asc())
    )
    snapshots = snap_result.scalars().all()

    # Trade stats (Trade -> Signal -> strategy_id)
    trade_result = await db.execute(
        select(
            func.count(Trade.id).label("count"),
            func.sum(case((Trade.pnl > 0, 1), else_=0)).label("wins"),
        )
        .join(Signal, Trade.signal_id == Signal.id)
        .where(Signal.strategy_id == sim.strategy_id)
    )
    trade_stats = trade_result.one()

    # Open positions
    pos_count = await db.execute(
        select(func.count(Position.id)).where(
            Position.strategy_id == sim.strategy_id,
            Position.is_open == True,  # noqa: E712
        )
    )

    initial = sim.initial_value_usd
    latest_bh = snapshots[-1].bh_value_usd if snapshots else initial
    latest_sf = snapshots[-1].sf_value_usd if snapshots else initial

    return {
        "id": str(sim.id),
        "status": sim.status,
        "strategy_id": str(sim.strategy_id) if sim.strategy_id else None,
        "started_at": sim.started_at.isoformat() if sim.started_at else None,
        "stopped_at": sim.stopped_at.isoformat() if sim.stopped_at else None,
        "initial_value_usd": initial,
        "initial_holdings": sim.initial_holdings,
        "snapshots": [
            {
                "timestamp": s.timestamp.isoformat(),
                "bh_value_usd": s.bh_value_usd,
                "sf_value_usd": s.sf_value_usd,
            }
            for s in snapshots
        ],
        "latest_bh_value": latest_bh,
        "latest_sf_value": latest_sf,
        "bh_return_pct": round((latest_bh - initial) / initial * 100, 2) if initial > 0 else 0,
        "sf_return_pct": round((latest_sf - initial) / initial * 100, 2) if initial > 0 else 0,
        "sf_trades": trade_stats.count or 0,
        "sf_win_rate": round(
            (trade_stats.wins / trade_stats.count * 100) if trade_stats.count else 0, 1
        ),
        "sf_open_positions": pos_count.scalar() or 0,
    }
