"""Hourly snapshot task — records B&H and SF equity for running simulations.

Simulation Model
================
Two portfolios tracked:
  B&H value   = sum(initial_qty × current_price)  — frozen snapshot
  SF  value   = sum(paper_qty  × current_price)   — live paper portfolio

The paper portfolio diverges from B&H only when trades execute.
With zero trades, paper_holdings == initial_holdings, so SF ≡ B&H.
"""

import logging

from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="snapshot_simulation", bind=True, max_retries=2)
def snapshot_simulation(self):
    """Record B&H and SF equity snapshots for all running paper simulations."""
    import asyncio

    from app.tasks.task_utils import task_lock

    with task_lock("snapshot_simulation", timeout=300) as acquired:
        if not acquired:
            return
        try:
            asyncio.run(_snapshot_async())
        except (ConnectionError, OSError, TimeoutError) as exc:
            logger.warning("snapshot_simulation transient error: %s — retrying", exc)
            raise self.retry(exc=exc, countdown=60)


async def _snapshot_async():
    from sqlalchemy import select

    from app.core.database import task_session
    from app.models.simulation import PaperSimulation, SimulationSnapshot

    async with task_session() as db:
        result = await db.execute(
            select(PaperSimulation).where(PaperSimulation.status == "running")
        )
        simulations = result.scalars().all()

        if not simulations:
            return

        # Collect all symbols we need prices for (both B&H and paper)
        all_symbols: set[str] = set()
        for sim in simulations:
            for h in (sim.initial_holdings or []):
                sym = h.get("symbol", "").upper()
                if sym:
                    all_symbols.add(sym)
            for h in (sim.paper_holdings or []):
                sym = h.get("symbol", "").upper()
                if sym:
                    all_symbols.add(sym)

        # Fetch current prices
        prices = await _fetch_current_prices(list(all_symbols))

        for sim in simulations:
            try:
                # --- Buy & Hold value ---
                # B&H = sum(initial_qty * current_price) for each holding.
                bh_value = 0.0
                for h in (sim.initial_holdings or []):
                    sym = h.get("symbol", "").upper()
                    qty = h.get("quantity", 0)
                    price = prices.get(sym, h.get("price_usd", 0))
                    bh_value += qty * price

                # --- Paper portfolio (SF) value ---
                # SF = sum(paper_qty * current_price) for each holding.
                # This directly reflects the paper portfolio state after trades.
                sf_value = 0.0
                usdt_balance = 0.0
                for h in (sim.paper_holdings or []):
                    sym = h.get("symbol", "").upper()
                    qty = h.get("quantity", 0)
                    if sym in _STABLECOINS:
                        sf_value += qty
                        if sym == "USDT":
                            usdt_balance = qty
                    else:
                        price = prices.get(sym, h.get("price_usd", 0))
                        sf_value += qty * price
                        # Update stored price in paper_holdings
                        h["price_usd"] = price
                        h["value_usd"] = round(qty * price, 2)

                # Update paper_holdings prices (mark as modified for JSON column)
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(sim, "paper_holdings")

                # Positions value (from open positions for this strategy)
                from sqlalchemy import func
                from app.models.position import Position

                pos_value_result = await db.execute(
                    select(
                        func.coalesce(
                            func.sum(Position.current_price * Position.quantity), 0.0
                        )
                    ).where(
                        Position.strategy_id == sim.strategy_id,
                        Position.is_open == True,  # noqa: E712
                    )
                )
                positions_value = float(pos_value_result.scalar())

                sf_cash = usdt_balance

                snapshot = SimulationSnapshot(
                    simulation_id=sim.id,
                    bh_value_usd=round(bh_value, 2),
                    sf_value_usd=round(sf_value, 2),
                    sf_cash_usd=round(max(sf_cash, 0), 2),
                    sf_positions_value=round(positions_value, 2),
                )
                db.add(snapshot)
                logger.info(
                    "Snapshot: sim=%s B&H=$%.2f SF=$%.2f USDT=$%.2f",
                    sim.id, bh_value, sf_value, usdt_balance,
                )
            except Exception:
                logger.exception("Failed snapshot for simulation %s", sim.id)

        await db.commit()


_STABLECOINS = {"USDT", "USDC", "BUSD", "DAI", "TUSD", "FDUSD", "USDP", "USD"}


async def _fetch_current_prices(symbols: list[str]) -> dict[str, float]:
    """Fetch current USD prices for a list of crypto symbols.

    Uses the configured default exchange (SF_DEFAULT_EXCHANGE) instead of
    hardcoding Binance, so simulations work for any supported exchange.
    """
    import ccxt.async_support as ccxt_async

    from app.config import settings

    result: dict[str, float] = {}
    non_stable = []
    for s in symbols:
        upper = s.upper()
        if upper in _STABLECOINS:
            result[upper] = 1.0
        else:
            non_stable.append(upper)

    if not non_stable:
        return result

    exchange_cls = getattr(ccxt_async, settings.default_exchange, None)
    if exchange_cls is None:
        logger.warning("Unknown exchange %s for simulation snapshot", settings.default_exchange)
        return result

    exchange = exchange_cls({"enableRateLimit": True})
    try:
        await exchange.load_markets()
        pairs = [f"{s}/USDT" for s in non_stable if f"{s}/USDT" in exchange.markets]
        if pairs:
            tickers = await exchange.fetch_tickers(pairs)
            for pair, ticker in tickers.items():
                sym = pair.split("/")[0]
                if ticker and ticker.get("last"):
                    result[sym] = float(ticker["last"])
    except Exception:
        logger.warning(
            "Price fetch from %s failed for simulation snapshot",
            settings.default_exchange,
        )
    finally:
        await exchange.close()

    return result
