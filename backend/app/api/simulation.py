"""Paper simulation API — start, monitor, and stop B&H vs SignalForge tests.

Simulation Model
================
Both sides start with the user's real portfolio snapshot.

  B&H portfolio   = frozen initial_holdings × current prices (never changes)
  Paper portfolio  = starts as copy of initial_holdings, then diverges with trades

USDT Reserve Policy
===================
The AI Advisor recommends an optimal USDT reserve % based on market conditions.
At simulation start, the system trims holdings proportionally to seed the reserve.
The reserve influences trading bias — buy signals are sized down when USDT is low.
"""

import copy
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
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


# ---------- Request/Response schemas ----------


class ReserveUpdateRequest(BaseModel):
    usdt_reserve_pct: float = Field(ge=0.0, le=0.50)
    mode: str = Field(default="manual", pattern="^(ai|manual|auto_accept)$")


# ---------- Endpoints ----------


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

    # Build holdings snapshot — aggregate by symbol (holdings come from
    # multiple sources: binance, kraken, manual, etc.)
    aggregated: dict[str, dict] = {}  # symbol -> {quantity, price_usd}
    symbols_for_trading: set[str] = set()
    exchange_map: dict[str, str] = {}  # "ALPH/USDT" -> "mexc"

    # Non-exchange sources that should NOT be used as CCXT exchange IDs
    non_exchange_sources = {"manual", "trading"}

    for h in all_holdings:
        sym = h.symbol.upper()
        info = prices.get(sym, {})
        price = info.get("price") or 0

        if sym in aggregated:
            aggregated[sym]["quantity"] += h.quantity
        else:
            aggregated[sym] = {"symbol": sym, "quantity": h.quantity, "price_usd": price}

        # Build trading pairs (skip stablecoins)
        if sym not in _STABLECOINS and price > 0:
            pair = f"{sym}/USDT"
            symbols_for_trading.add(pair)
            # Track which exchange this symbol came from.
            if pair not in exchange_map and h.source:
                if h.source not in non_exchange_sources:
                    exchange_map[pair] = h.source

    # Build final snapshot with aggregated quantities
    holdings_snapshot = []
    total_value = 0.0
    for entry in aggregated.values():
        qty = entry["quantity"]
        price = entry["price_usd"]
        value = qty * price if price else 0
        holdings_snapshot.append({
            "symbol": entry["symbol"],
            "quantity": round(qty, 8),
            "price_usd": price,
            "value_usd": round(value, 2),
        })
        total_value += value

    if total_value < 1.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Portfolio value too low to start a simulation.",
        )

    # Paper holdings start as an exact copy of real holdings.
    # USDT for trading comes from existing USDT balance and future sells —
    # no artificial rebalancing at start.
    paper_holdings = copy.deepcopy(holdings_snapshot)

    # Determine existing USDT balance for reserve tracking
    existing_usdt = sum(
        h["quantity"] for h in holdings_snapshot if h["symbol"] == "USDT"
    )
    usdt_reserve_pct = existing_usdt / total_value if total_value > 0 else 0.0

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
            # Simulation marker
            "is_simulation": True,
            "usdt_reserve_pct": usdt_reserve_pct,
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
        paper_holdings=paper_holdings,
        usdt_reserve_pct=usdt_reserve_pct,
        usdt_reserve_mode="manual",
        ai_suggested_reserve_pct=None,
        ai_reserve_reasoning=None,
    )
    db.add(sim)

    # Initial snapshot (B&H = SF = starting value)
    snapshot = SimulationSnapshot(
        simulation_id=sim.id,
        bh_value_usd=round(total_value, 2),
        sf_value_usd=round(total_value, 2),
        sf_cash_usd=round(existing_usdt, 2),
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
        "usdt_reserve_pct": usdt_reserve_pct,
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


@router.get("/{sim_id}/portfolio/bh")
@limiter.limit("60/minute")
async def get_bh_portfolio(
    request: Request,
    sim_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the Buy & Hold portfolio — initial holdings at current prices."""
    sim = await _get_user_simulation(db, sim_id, user_id)

    from app.api.holdings import _fetch_prices

    symbols = [h["symbol"] for h in (sim.initial_holdings or [])]
    prices = await _fetch_prices(symbols) if symbols else {}

    holdings = []
    total_value = 0.0
    for h in (sim.initial_holdings or []):
        sym = h["symbol"]
        qty = h["quantity"]
        info = prices.get(sym, {})
        current_price = info.get("price") or h.get("price_usd", 0)
        value = qty * current_price
        initial_value = h.get("value_usd", 0)
        total_value += value

        holdings.append({
            "symbol": sym,
            "quantity": qty,
            "initial_price": h.get("price_usd", 0),
            "current_price": current_price,
            "value_usd": round(value, 2),
            "initial_value_usd": round(initial_value, 2),
            "pnl_usd": round(value - initial_value, 2),
            "pnl_pct": round((value - initial_value) / initial_value * 100, 2) if initial_value > 0 else 0,
            "change_24h_pct": info.get("change_24h_pct"),
            "image_url": info.get("image_url"),
            "market_cap": info.get("market_cap"),
            "market_cap_rank": info.get("market_cap_rank"),
        })

    # Sort by value descending
    holdings.sort(key=lambda x: x["value_usd"], reverse=True)

    return {
        "type": "buy_and_hold",
        "total_value_usd": round(total_value, 2),
        "initial_value_usd": sim.initial_value_usd,
        "total_pnl_usd": round(total_value - sim.initial_value_usd, 2),
        "total_pnl_pct": round(
            (total_value - sim.initial_value_usd) / sim.initial_value_usd * 100, 2
        ) if sim.initial_value_usd > 0 else 0,
        "holdings": holdings,
    }


@router.get("/{sim_id}/portfolio/paper")
@limiter.limit("60/minute")
async def get_paper_portfolio(
    request: Request,
    sim_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the Paper Trading portfolio — current paper holdings at live prices."""
    sim = await _get_user_simulation(db, sim_id, user_id)

    from app.api.holdings import _fetch_prices

    paper = sim.paper_holdings or []
    symbols = [h["symbol"] for h in paper]
    prices = await _fetch_prices(symbols) if symbols else {}

    # Also get open positions for this simulation strategy
    pos_result = await db.execute(
        select(Position).where(
            Position.strategy_id == sim.strategy_id,
            Position.is_open == True,  # noqa: E712
        )
    )
    open_positions = pos_result.scalars().all()

    holdings = []
    total_value = 0.0
    usdt_balance = 0.0

    for h in paper:
        sym = h["symbol"]
        qty = h["quantity"]
        if qty <= 0:
            continue

        info = prices.get(sym, {})
        if sym in _STABLECOINS:
            current_price = 1.0
        else:
            current_price = info.get("price") or h.get("price_usd", 0)
        value = qty * current_price
        total_value += value

        if sym == "USDT":
            usdt_balance = qty

        # Find initial holding to compute P&L
        initial_h = next(
            (ih for ih in (sim.initial_holdings or []) if ih["symbol"] == sym), None
        )
        initial_value = initial_h["value_usd"] if initial_h else 0
        initial_qty = initial_h["quantity"] if initial_h else 0

        holdings.append({
            "symbol": sym,
            "quantity": qty,
            "initial_quantity": initial_qty,
            "quantity_change": round(qty - initial_qty, 8),
            "current_price": current_price,
            "value_usd": round(value, 2),
            "initial_value_usd": round(initial_value, 2),
            "pnl_usd": round(value - initial_value, 2),
            "pnl_pct": round((value - initial_value) / initial_value * 100, 2) if initial_value > 0 else 0,
            "change_24h_pct": info.get("change_24h_pct"),
            "image_url": info.get("image_url"),
            "market_cap": info.get("market_cap"),
            "market_cap_rank": info.get("market_cap_rank"),
        })

    holdings.sort(key=lambda x: x["value_usd"], reverse=True)

    # Reserve status
    reserve_target_usd = total_value * sim.usdt_reserve_pct
    reserve_status = "at_target"
    if usdt_balance < reserve_target_usd * 0.9:
        reserve_status = "below_target"
    elif usdt_balance > reserve_target_usd * 1.1:
        reserve_status = "above_target"

    return {
        "type": "paper_trading",
        "total_value_usd": round(total_value, 2),
        "initial_value_usd": sim.initial_value_usd,
        "total_pnl_usd": round(total_value - sim.initial_value_usd, 2),
        "total_pnl_pct": round(
            (total_value - sim.initial_value_usd) / sim.initial_value_usd * 100, 2
        ) if sim.initial_value_usd > 0 else 0,
        "holdings": holdings,
        "usdt_balance": round(usdt_balance, 2),
        "usdt_reserve_pct": sim.usdt_reserve_pct,
        "usdt_reserve_target_usd": round(reserve_target_usd, 2),
        "usdt_reserve_status": reserve_status,
        "usdt_reserve_mode": sim.usdt_reserve_mode,
        "ai_suggested_reserve_pct": sim.ai_suggested_reserve_pct,
        "ai_reserve_reasoning": sim.ai_reserve_reasoning,
        "open_positions": [
            {
                "symbol": p.symbol,
                "direction": p.direction,
                "quantity": p.quantity,
                "entry_price": p.entry_price,
                "current_price": p.current_price,
                "unrealized_pnl": p.unrealized_pnl,
            }
            for p in open_positions
        ],
    }


@router.put("/{sim_id}/reserve")
@limiter.limit("10/minute")
async def update_reserve(
    request: Request,
    sim_id: str,
    body: ReserveUpdateRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the USDT reserve target for a running simulation."""
    sim = await _get_user_simulation(db, sim_id, user_id)

    if sim.status != "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update reserve on a stopped simulation.",
        )

    sim.usdt_reserve_pct = body.usdt_reserve_pct
    sim.usdt_reserve_mode = body.mode

    # Also update strategy config
    if sim.strategy_id:
        strat_result = await db.execute(
            select(Strategy).where(Strategy.id == sim.strategy_id)
        )
        strategy = strat_result.scalar_one_or_none()
        if strategy and strategy.config:
            strategy.config = {**strategy.config, "usdt_reserve_pct": body.usdt_reserve_pct}

    await db.commit()

    return {
        "usdt_reserve_pct": sim.usdt_reserve_pct,
        "usdt_reserve_mode": sim.usdt_reserve_mode,
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

    # Calculate final B&H and paper portfolio values
    from app.api.holdings import _fetch_prices

    bh_symbols = [h["symbol"] for h in (sim.initial_holdings or [])]
    paper_symbols = [h["symbol"] for h in (sim.paper_holdings or [])]
    all_syms = list(set(bh_symbols + paper_symbols))
    prices = await _fetch_prices(all_syms) if all_syms else {}

    # B&H final value
    bh_value = 0.0
    for h in (sim.initial_holdings or []):
        sym = h.get("symbol", "").upper()
        qty = h.get("quantity", 0)
        info = prices.get(sym, {})
        price = info.get("price") or h.get("price_usd", 0)
        bh_value += qty * price

    # Paper portfolio final value
    sf_value = 0.0
    for h in (sim.paper_holdings or []):
        sym = h.get("symbol", "").upper()
        qty = h.get("quantity", 0)
        if sym in _STABLECOINS:
            sf_value += qty
        else:
            info = prices.get(sym, {})
            price = info.get("price") or h.get("price_usd", 0)
            sf_value += qty * price

    final_snapshot = SimulationSnapshot(
        simulation_id=sim.id,
        bh_value_usd=round(bh_value, 2),
        sf_value_usd=round(sf_value, 2),
        sf_cash_usd=round(
            sum(h["quantity"] for h in (sim.paper_holdings or []) if h["symbol"] == "USDT"),
            2,
        ),
        sf_positions_value=0.0,
    )
    db.add(final_snapshot)

    # Stop simulation
    sim.status = "stopped"
    sim.stopped_at = datetime.now(timezone.utc)

    await db.commit()

    return await _build_simulation_response(db, sim)


# ---------- Helpers ----------


async def _get_user_simulation(
    db: AsyncSession, sim_id: str, user_id: str
) -> PaperSimulation:
    """Fetch a simulation belonging to the user, or raise 404."""
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
    return sim


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


def _seed_usdt_reserve(
    holdings: list[dict], reserve_pct: float, total_value: float
) -> list[dict]:
    """Seed the USDT reserve by proportionally trimming non-stablecoin holdings.

    If the portfolio already has enough USDT, no trimming occurs.
    Returns the modified holdings list.
    """
    if reserve_pct <= 0:
        return holdings

    target_usdt = total_value * reserve_pct

    # Find current USDT balance
    usdt_entry = None
    current_usdt = 0.0
    for h in holdings:
        if h["symbol"] == "USDT":
            usdt_entry = h
            current_usdt = h["quantity"]
            break

    needed_usdt = target_usdt - current_usdt
    if needed_usdt <= 0:
        return holdings  # Already have enough USDT

    # Calculate total non-stablecoin value for proportional trimming
    non_stable_value = sum(
        h["value_usd"] for h in holdings
        if h["symbol"] not in _STABLECOINS and h["value_usd"] > 0
    )

    if non_stable_value <= 0:
        return holdings

    # Trim each non-stablecoin holding proportionally
    usdt_freed = 0.0
    for h in holdings:
        if h["symbol"] in _STABLECOINS:
            continue
        if h["value_usd"] <= 0:
            continue

        # Proportion of this holding relative to all non-stablecoins
        proportion = h["value_usd"] / non_stable_value
        trim_usd = needed_usdt * proportion
        trim_qty = trim_usd / h["price_usd"] if h["price_usd"] > 0 else 0

        # Don't trim more than 50% of any single holding
        max_trim = h["quantity"] * 0.5
        trim_qty = min(trim_qty, max_trim)

        h["quantity"] = round(h["quantity"] - trim_qty, 8)
        h["value_usd"] = round(h["quantity"] * h["price_usd"], 2)
        usdt_freed += trim_qty * h["price_usd"]

    # Add freed USDT to the USDT entry
    if usdt_entry:
        usdt_entry["quantity"] = round(usdt_entry["quantity"] + usdt_freed, 2)
        usdt_entry["value_usd"] = round(usdt_entry["quantity"], 2)
    else:
        holdings.append({
            "symbol": "USDT",
            "quantity": round(usdt_freed, 2),
            "price_usd": 1.0,
            "value_usd": round(usdt_freed, 2),
        })

    return holdings


async def _get_ai_reserve_recommendation(
    db: AsyncSession, user_id: uuid.UUID
) -> tuple[float, str]:
    """Ask the AI Advisor for a USDT reserve % recommendation.

    Falls back to a rule-based heuristic if Claude is unavailable.
    """
    try:
        from app.advisor.claude_client import ModelTier, claude_client

        result = claude_client.ask_json_sync(
            ModelTier.FAST,
            (
                "You are a crypto portfolio advisor. Based on current market conditions, "
                "recommend the optimal USDT reserve percentage for a paper trading portfolio. "
                "Consider: Is the market trending or choppy? Bull or bear? High volatility? "
                "Respond ONLY with JSON: {\"usdt_reserve_pct\": 0.15, \"reasoning\": \"...\"}"
            ),
            "What USDT reserve % should a paper trading portfolio maintain right now?",
            max_tokens=200,
            cache_ttl=3600,
            insight_type="usdt_reserve",
        )
        if result:
            pct = float(result.get("usdt_reserve_pct", 0.15))
            pct = max(0.05, min(0.50, pct))  # clamp
            reasoning = result.get("reasoning", "AI-recommended reserve level.")
            return pct, reasoning
    except Exception:
        logger.warning("Claude unavailable for reserve recommendation")

    # Rule-based fallback
    return 0.15, "Default 15% reserve — moderate market exposure."


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

    # Paper portfolio USDT balance
    paper_usdt = sum(
        h["quantity"] for h in (sim.paper_holdings or []) if h["symbol"] == "USDT"
    )

    return {
        "id": str(sim.id),
        "status": sim.status,
        "strategy_id": str(sim.strategy_id) if sim.strategy_id else None,
        "started_at": sim.started_at.isoformat() if sim.started_at else None,
        "stopped_at": sim.stopped_at.isoformat() if sim.stopped_at else None,
        "initial_value_usd": initial,
        "initial_holdings": sim.initial_holdings,
        "paper_holdings": sim.paper_holdings,
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
        # Reserve info
        "usdt_reserve_pct": sim.usdt_reserve_pct,
        "usdt_reserve_mode": sim.usdt_reserve_mode,
        "usdt_balance": round(paper_usdt, 2),
        "ai_suggested_reserve_pct": sim.ai_suggested_reserve_pct,
        "ai_reserve_reasoning": sim.ai_reserve_reasoning,
    }
