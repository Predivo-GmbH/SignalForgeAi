"""Hourly snapshot task — records B&H and SF equity for running simulations."""

import logging

from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="snapshot_simulation", bind=True, max_retries=2)
def snapshot_simulation(self):
    """Record B&H and SF equity snapshots for all running paper simulations."""
    import asyncio

    try:
        asyncio.run(_snapshot_async())
    except (ConnectionError, OSError, TimeoutError) as exc:
        logger.warning("snapshot_simulation transient error: %s — retrying", exc)
        self.retry(exc=exc, countdown=60)


async def _snapshot_async():
    import ccxt.async_support as ccxt_async
    from sqlalchemy import func, select

    from app.core.database import task_session
    from app.models.position import Position
    from app.models.simulation import PaperSimulation, SimulationSnapshot
    from app.models.trade import Trade

    async with task_session() as db:
        result = await db.execute(
            select(PaperSimulation).where(PaperSimulation.status == "running")
        )
        simulations = result.scalars().all()

        if not simulations:
            return

        # Collect all symbols we need prices for
        all_symbols: set[str] = set()
        for sim in simulations:
            for h in (sim.initial_holdings or []):
                sym = h.get("symbol", "").upper()
                if sym:
                    all_symbols.add(sym)

        # Fetch current prices
        prices = await _fetch_current_prices(list(all_symbols))

        for sim in simulations:
            try:
                # --- Buy & Hold value ---
                bh_value = 0.0
                for h in (sim.initial_holdings or []):
                    sym = h.get("symbol", "").upper()
                    qty = h.get("quantity", 0)
                    price = prices.get(sym, h.get("price_usd", 0))
                    bh_value += qty * price

                # --- SignalForge value ---
                # Realized P&L from closed trades
                pnl_result = await db.execute(
                    select(func.coalesce(func.sum(Trade.pnl), 0.0)).where(
                        Trade.strategy_id == sim.strategy_id
                    )
                )
                realized_pnl = float(pnl_result.scalar())

                # Unrealized P&L from open positions
                pos_result = await db.execute(
                    select(
                        func.coalesce(func.sum(Position.unrealized_pnl), 0.0)
                    ).where(
                        Position.strategy_id == sim.strategy_id,
                        Position.is_open == True,  # noqa: E712
                    )
                )
                unrealized_pnl = float(pos_result.scalar())

                # Open position value (for cash breakdown)
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

                sf_value = sim.initial_value_usd + realized_pnl + unrealized_pnl
                sf_cash = sf_value - positions_value

                snapshot = SimulationSnapshot(
                    simulation_id=sim.id,
                    bh_value_usd=round(bh_value, 2),
                    sf_value_usd=round(sf_value, 2),
                    sf_cash_usd=round(max(sf_cash, 0), 2),
                    sf_positions_value=round(positions_value, 2),
                )
                db.add(snapshot)
                logger.info(
                    "Snapshot: sim=%s B&H=$%.2f SF=$%.2f",
                    sim.id, bh_value, sf_value,
                )
            except Exception:
                logger.exception("Failed snapshot for simulation %s", sim.id)

        await db.commit()


_STABLECOINS = {"USDT", "USDC", "BUSD", "DAI", "TUSD", "FDUSD", "USDP", "USD"}


async def _fetch_current_prices(symbols: list[str]) -> dict[str, float]:
    """Fetch current USD prices for a list of crypto symbols."""
    import ccxt.async_support as ccxt_async

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

    exchange = ccxt_async.binance({"enableRateLimit": True})
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
        logger.warning("Binance price fetch failed for simulation snapshot")
    finally:
        await exchange.close()

    return result
