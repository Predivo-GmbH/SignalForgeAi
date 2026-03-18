"""Sync portfolio holdings into active strategy watchlists.

For every asset in the user's portfolio, ensures at least one active strategy
is watching it — so the pipeline can generate exit signals when needed.

Rules:
- Held asset (quantity > 0) not in any active strategy → add it
- Held asset reaches quantity=0 and no open position → remove it
- Open positions are always protected from removal
- Stablecoins (USDT, USDC, BUSD, DAI, TUSD, FDUSD, USDP, UST) are never added as trading pairs
- Fiat currency balances (USD, EUR, GBP, …) are skipped — not tradeable USDT pairs
- Exchange ticker aliases are resolved (XBT → BTC) to avoid duplicate entries
- Symbol normalisation: bare tickers (QUBIC) → QUBIC/USDT
- Exchange connections are read live so holdings entered on the exchange (e.g.
  RENDER bought on Binance) are picked up automatically — not just manually
  entered ones.
"""

import asyncio
import logging
from dataclasses import dataclass

from app.config import settings
from app.core.encryption import decrypt_value
from app.execution.adapters.ccxt_adapter import CCXTAdapter
from app.worker import celery_app

logger = logging.getLogger(__name__)

_STABLECOINS = frozenset({"USDT", "USDC", "BUSD", "DAI", "TUSD", "FDUSD", "USDP", "UST"})

# Fiat currencies that appear as "balances" on some exchanges but are not
# tradeable USDT pairs. Exchange-specific tokens (KFEE etc.) are NOT excluded —
# they are real tokens the user may want to paper-trade.
_NON_TRADEABLE = frozenset({
    "USD", "EUR", "GBP", "CHF", "JPY", "AUD", "CAD",  # fiat
})

# Ticker aliases — normalised to canonical tickers before pair construction.
# XBT is Kraken's name for Bitcoin; map it to BTC to avoid a duplicate BTC/USDT entry.
_TICKER_ALIASES: dict[str, str] = {
    "XBT": "BTC",
}

# Redis key for watchlist endpoint to read held symbol bases without a live exchange call
_HELD_BASES_KEY = "signalforge:portfolio:held_bases"
# Redis key prefix for per-connection sync status (written by worker, read by health endpoint)
_SYNC_STATUS_KEY_PREFIX = "signalforge:sync_status:"


@dataclass
class _ExchangeHolding:
    """Minimal holding-like object from a live exchange balance."""
    symbol: str
    quantity: float


def _normalise_symbol(symbol: str) -> str:
    """Convert a bare ticker or existing pair to uppercase TICKER/USDT format.

    Ticker aliases (e.g. XBT → BTC) are resolved before pair construction so
    that exchange-specific names map to the canonical tradeable symbol.
    """
    s = symbol.upper().strip()
    if "/" in s:
        base, quote = s.split("/", 1)
        base = _TICKER_ALIASES.get(base, base)
        return f"{base}/{quote}"
    s = _TICKER_ALIASES.get(s, s)
    return f"{s}/USDT"


def _build_sync_ops(
    holdings: list,
    strategies: list,
    open_position_symbols: set[str],
    universe_symbols: set[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Compute which symbols to add across strategies.

    ADD-only policy: any held asset not in the watchlist is added.
    Symbols are NEVER automatically removed — removal requires explicit user action.

    Rationale: we cannot reliably verify all holdings (hardware wallets,
    unsupported exchanges, failed API calls). Removing a symbol because we
    can't confirm the balance would silently drop assets the user holds,
    blocking exit signals on open positions and preventing paper-trade testing
    of any asset not reachable via a connected exchange API.

    Returns:
        to_add: symbols that need to be added (held but not watched)
        to_remove: always empty — removals are manual only
    """
    universe_symbols = universe_symbols or set()

    # Build current watchlist across all strategies
    watched: set[str] = set()
    for strategy in strategies:
        watched.update(strategy.config.get("symbols", []))

    held_positive: set[str] = set()

    for holding in holdings:
        normalised = _normalise_symbol(holding.symbol)
        base = normalised.split("/")[0]

        # Skip stablecoins — they're not trading pairs
        if base in _STABLECOINS or base in _NON_TRADEABLE:
            continue

        if holding.quantity > 0:
            held_positive.add(normalised)

    to_add = [s for s in held_positive if s not in watched]
    to_remove: list[str] = []  # never auto-remove

    return to_add, to_remove


async def _sync_portfolio_positions(
    db,
    user_id: str,
    strategy_id: str,
    held_symbols: set[str],
    primary_timeframe: str,
    held_quantities: dict[str, float] | None = None,
) -> None:
    """Maintain synthetic BUY positions for portfolio holdings.

    Creates a synthetic open BUY position for each held symbol that has no
    existing open BUY position.  This allows the signal pipeline's position
    filter to pass SELL signals, enabling downtrend protection for assets
    the user already owns.

    Closes synthetic positions for symbols that are no longer held so the
    pipeline stops generating SELL signals on assets the user has already sold.
    """
    import uuid
    from datetime import datetime, timezone

    from sqlalchemy import select

    from app.models.candle import Candle
    from app.models.position import Position

    uid = uuid.UUID(user_id)

    # All open BUY positions for this user
    result = await db.execute(
        select(Position).where(
            Position.user_id == uid,
            Position.is_open == True,  # noqa: E712
            Position.direction == "BUY",
        )
    )
    all_open = result.scalars().all()

    synthetic_by_sym = {p.symbol: p for p in all_open if p.broker == "portfolio_sync"}
    has_open_buy: set[str] = {p.symbol for p in all_open}

    # Close synthetic positions for symbols no longer held
    for sym, pos in synthetic_by_sym.items():
        if sym not in held_symbols:
            pos.is_open = False
            pos.closed_at = datetime.now(timezone.utc)
            logger.info(
                "sync_portfolio_symbols: closed synthetic position for %s (no longer held)", sym
            )

    # Create synthetic positions for held symbols without any open BUY position
    qty_map = held_quantities or {}
    for sym in held_symbols:
        if sym in has_open_buy:
            continue

        # Use latest candle close as a proxy for entry price
        candle_row = await db.execute(
            select(Candle.close).where(
                Candle.symbol == sym,
                Candle.timeframe == primary_timeframe,
            ).order_by(Candle.time.desc()).limit(1)
        )
        row = candle_row.first()
        entry_price = float(row[0]) if row else 0.0

        # Use actual holding quantity so PnL tracking is meaningful
        actual_qty = qty_map.get(sym, 0.0)

        pos = Position(
            user_id=uid,
            order_id=None,
            strategy_id=uuid.UUID(strategy_id) if strategy_id else None,
            symbol=sym,
            direction="BUY",
            quantity=actual_qty,
            entry_price=entry_price,
            current_price=entry_price,
            stop_loss=None,
            take_profit=None,
            original_stop_loss=None,
            unrealized_pnl=0.0,
            broker="portfolio_sync",
            is_open=True,
        )
        db.add(pos)
        logger.info(
            "sync_portfolio_symbols: created synthetic BUY position for %s @ %.4f",
            sym, entry_price,
        )


@celery_app.task(name="sync_portfolio_symbols", bind=True, max_retries=2)
def sync_portfolio_symbols(self):
    """Ensure all portfolio holdings are in active strategy watchlists."""
    from app.tasks.task_utils import task_lock

    with task_lock("sync_portfolio_symbols", timeout=300) as acquired:
        if not acquired:
            return
        try:
            asyncio.run(_sync_portfolio_async())
        except (ConnectionError, OSError, TimeoutError) as exc:
            logger.warning("sync_portfolio_symbols transient error: %s — retrying", exc)
            raise self.retry(exc=exc, countdown=30)
        except Exception:
            logger.exception("Unexpected error in sync_portfolio_symbols")


async def _fetch_all_exchange_holdings(db) -> list[_ExchangeHolding]:
    """Fetch live balances from all non-paper read-only broker connections."""
    from sqlalchemy import select

    from app.models.strategy import BrokerConnection

    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.is_paper.is_(False),
            BrokerConnection.purpose == "read",
        )
    )
    connections = result.scalars().all()

    import json as _json

    import redis as _redis

    try:
        _r = _redis.from_url(settings.redis_url)
    except Exception:
        _r = None

    async def _fetch_one(conn) -> list[_ExchangeHolding]:
        conn_key = f"{_SYNC_STATUS_KEY_PREFIX}{conn.id}"
        try:
            adapter = CCXTAdapter(
                exchange_id=conn.broker,
                api_key=decrypt_value(conn.api_key_enc),
                api_secret=decrypt_value(conn.api_secret_enc),
                password=decrypt_value(conn.api_passphrase_enc) if conn.api_passphrase_enc else "",
                testnet=False,
            )
            try:
                balances = await adapter.get_full_balance()
                # Record successful sync
                if _r:
                    try:
                        _r.setex(conn_key, 3600, _json.dumps({"ok": True, "error": None}))
                    except Exception:
                        pass
                return [_ExchangeHolding(symbol=sym, quantity=qty) for sym, qty in balances.items()]
            finally:
                await adapter.close()
        except Exception as exc:
            err_msg = str(exc)[:200]
            logger.warning(
                "sync_portfolio_symbols: failed to fetch balance from %s: %s",
                conn.broker, err_msg,
            )
            # Record failed sync so health endpoint can surface it
            if _r:
                try:
                    _r.setex(conn_key, 3600, _json.dumps({"ok": False, "error": err_msg}))
                except Exception:
                    pass
            return []

    results = await asyncio.gather(*[_fetch_one(c) for c in connections])
    if _r:
        try:
            _r.close()
        except Exception:
            pass
    return [h for batch in results for h in batch]


async def _sync_portfolio_async():
    from sqlalchemy import select

    from app.advisor.symbol_rotation import SymbolRotationManager
    from app.config import settings
    from app.core.database import task_session
    from app.models.holding import ManualHolding
    from app.models.position import Position
    from app.models.strategy import Strategy

    if not settings.portfolio_symbol_sync_enabled:
        logger.info("Portfolio symbol sync disabled via feature flag")
        return


    import redis as redis_lib

    from app.tasks.expand_symbol_universe import _PROMOTED_KEY
    from app.tasks.ingest_candles import backfill_symbols

    async with task_session() as db:
        # Load all active strategies
        strat_result = await db.execute(
            select(Strategy).where(Strategy.is_active == True)  # noqa: E712
        )
        strategies = list(strat_result.scalars().all())

        if not strategies:
            logger.info("sync_portfolio_symbols: no active strategies")
            return

        # Load manual holdings + live exchange balances
        holding_result = await db.execute(select(ManualHolding))
        manual_holdings = list(holding_result.scalars().all())
        exchange_holdings = await _fetch_all_exchange_holdings(db)
        holdings = manual_holdings + exchange_holdings

        if not holdings:
            logger.info("sync_portfolio_symbols: no portfolio holdings")
            return

        # Load open positions (symbols with open trades — must not be removed)
        pos_result = await db.execute(
            select(Position).where(Position.is_open == True)  # noqa: E712
        )
        open_position_symbols = {
            _normalise_symbol(p.symbol) for p in pos_result.scalars().all()
        }

        # Universe-promoted symbols are protected from removal even if not held
        universe_symbols: set[str] = set()
        try:
            r = redis_lib.from_url(settings.redis_url)
            raw = r.smembers(_PROMOTED_KEY)
            universe_symbols = {s.decode() if isinstance(s, bytes) else s for s in raw}
            r.close()
        except Exception:
            pass

        to_add_raw, to_remove = _build_sync_ops(
            holdings, strategies, open_position_symbols, universe_symbols,
        )

        # Quality gate: only add symbols that have enough candle data for the pipeline to evaluate.
        # Symbols without data are held assets we still track via synthetic positions, but they
        # must not pollute the active watchlist until the pipeline can actually analyse them.
        to_add: list[str] = []
        if to_add_raw:
            from sqlalchemy import func
            from sqlalchemy import select as sa_select

            from app.models.candle import Candle as CandleModel

            primary_tf_for_gate = strategies[0].config.get("timeframes", ["4h"])[0]
            candle_gate_result = await db.execute(
                sa_select(CandleModel.symbol, func.count(CandleModel.symbol).label("cnt"))
                .where(
                    CandleModel.symbol.in_(to_add_raw),
                    CandleModel.timeframe == primary_tf_for_gate,
                )
                .group_by(CandleModel.symbol)
            )
            candle_gate_counts = {row.symbol: row.cnt for row in candle_gate_result.all()}
            min_candles_gate = settings.portfolio_sync_min_candles

            for sym in to_add_raw:
                cnt = candle_gate_counts.get(sym, 0)
                if cnt >= min_candles_gate:
                    to_add.append(sym)
                else:
                    logger.info(
                        "sync_portfolio_symbols: skipping watchlist add for %s — "
                        "only %d/%d %s candles (synthetic position still maintained)",
                        sym, cnt, min_candles_gate, primary_tf_for_gate,
                    )

        # Build held_symbols (full normalised pairs with qty > 0, no stables/fiat)
        held_symbols: set[str] = set()
        held_quantities: dict[str, float] = {}  # symbol → total quantity across all sources
        held_bases: set[str] = set()
        for h in holdings:
            normalised = _normalise_symbol(h.symbol)
            base = normalised.split("/")[0]
            if base not in _STABLECOINS and base not in _NON_TRADEABLE and h.quantity > 0:
                held_symbols.add(normalised)
                held_bases.add(base)
                held_quantities[normalised] = held_quantities.get(normalised, 0.0) + h.quantity

        # Cache held bases so the watchlist endpoint can classify without a live exchange call
        try:
            if held_bases:
                pipe = redis_lib.from_url(settings.redis_url).pipeline()
                pipe.delete(_HELD_BASES_KEY)
                pipe.sadd(_HELD_BASES_KEY, *held_bases)
                pipe.expire(_HELD_BASES_KEY, 600)  # 10 min TTL — refreshed every 5 min
                pipe.execute()
        except Exception:
            logger.warning("sync_portfolio_symbols: failed to cache held bases", exc_info=True)

        # Use the first active strategy as the "home" for portfolio symbols.
        primary_strategy = strategies[0]
        primary_timeframe = primary_strategy.config.get("timeframes", ["4h"])[0]

        # Always sync synthetic positions — even when watchlist is unchanged
        await _sync_portfolio_positions(
            db=db,
            user_id=str(primary_strategy.user_id),
            strategy_id=str(primary_strategy.id),
            held_symbols=held_symbols,
            primary_timeframe=primary_timeframe,
            held_quantities=held_quantities,
        )

        if not to_add and not to_remove:
            logger.info("sync_portfolio_symbols: watchlist already in sync")
            await db.commit()
            return

        mgr = SymbolRotationManager()

        if to_add:
            added = await mgr.add_symbols(primary_strategy, to_add, db, source="portfolio_sync")
            if added:
                timeframes = primary_strategy.config.get("timeframes", ["1h", "4h", "1d"])
                backfill_symbols.delay(added, timeframes)
                logger.info(
                    "sync_portfolio_symbols: added %d holdings to watchlist: %s",
                    len(added), added,
                )

        # to_remove is always empty — removals are manual only

        await db.commit()
