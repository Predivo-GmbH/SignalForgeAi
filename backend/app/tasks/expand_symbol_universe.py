"""Expand the symbol universe by continuously monitoring exchange listings.

This task runs every 6 hours and:
  1. Fetches all active USDT spot pairs from ALL connected exchanges
  2. Volume pre-filters (≥ $500k/24h) to reduce noise before AI sees the list
  3. Passes qualifying candidates to SymbolScout (Claude) for intelligent selection
  4. AI-approved candidates start candle backfill per source exchange
  5. After backfill completes, promote_universe_candidates triggers immediately
     — symbols enter the active watchlist within minutes of discovery
  6. The 6-hour cycle also runs promote_universe_candidates as a safety net
     for any symbols waiting on candle history from previous runs

Blocklist: symbols explicitly rejected by the user are stored in Redis and
skipped permanently by this task.

Philosophy: AI decides what to watch. The pipeline decides what to trade.
"""

import asyncio
import logging
from collections import defaultdict

from app.advisor.symbol_scout import SymbolScout
from app.config import settings
from app.core.database import task_session
from app.tasks.ingest_candles import backfill_symbols
from app.worker import celery_app

logger = logging.getLogger(__name__)

# Redis keys
_POOL_KEY = "signalforge:universe:candidate_pool"
_PROMOTED_KEY = "signalforge:universe:promoted_symbols"
_EXCHANGE_MAP_KEY = "signalforge:universe:candidate_exchange_map"
_BLOCKLIST_KEY = "signalforge:universe:blocklist"


@celery_app.task(name="expand_symbol_universe", bind=True, max_retries=2)
def expand_symbol_universe(self):
    """Scan all connected exchanges, AI-evaluate candidates, queue backfill."""
    from app.tasks.task_utils import task_lock

    with task_lock("expand_symbol_universe", timeout=3600) as acquired:
        if not acquired:
            return
        try:
            asyncio.run(_expand_universe_async())
        except (ConnectionError, OSError, TimeoutError) as exc:
            logger.warning("expand_symbol_universe transient error: %s — retrying", exc)
            raise self.retry(exc=exc, countdown=120)
        except Exception:
            logger.exception("Unexpected error in expand_symbol_universe")


# ---------------------------------------------------------------------------
# Exchange fetching (public endpoints — no auth needed)
# ---------------------------------------------------------------------------


def _fetch_exchange_tickers(exchange_id: str) -> list[dict]:
    """Fetch all spot tickers from an exchange. Tags each ticker with _exchange."""
    import ccxt

    try:
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({"enableRateLimit": True})
        tickers = exchange.fetch_tickers()
        result = []
        for t in tickers.values():
            t["_exchange"] = exchange_id
            result.append(t)
        return result
    except Exception:
        logger.warning("Failed to fetch tickers from %s", exchange_id, exc_info=True)
        return []


async def _fetch_all_connected_exchange_tickers(db) -> list[dict]:
    """Fetch USDT tickers from every connected non-paper exchange in parallel.

    Deduplicates by symbol keeping the highest-volume entry.
    """
    from sqlalchemy import select

    from app.models.strategy import BrokerConnection

    result = await db.execute(
        select(BrokerConnection.broker).distinct().where(
            BrokerConnection.is_paper.is_(False),
        )
    )
    exchange_ids = [row[0] for row in result.all()]

    if not exchange_ids:
        exchange_ids = [settings.default_exchange]
        logger.info(
            "expand_symbol_universe: no live connections, scanning default exchange %s",
            settings.default_exchange,
        )
    else:
        logger.info(
            "expand_symbol_universe: scanning %d exchanges: %s",
            len(exchange_ids), exchange_ids,
        )

    loop = asyncio.get_event_loop()
    batches = await asyncio.gather(
        *[loop.run_in_executor(None, _fetch_exchange_tickers, exc_id) for exc_id in exchange_ids],
        return_exceptions=True,
    )

    best: dict[str, dict] = {}
    for batch in batches:
        if isinstance(batch, Exception):
            continue
        for ticker in batch:
            sym = ticker.get("symbol", "")
            if not sym:
                continue
            existing_vol = (best.get(sym) or {}).get("quoteVolume") or 0.0
            this_vol = ticker.get("quoteVolume") or 0.0
            if this_vol > existing_vol:
                best[sym] = ticker

    logger.info("expand_symbol_universe: %d unique pairs found across all exchanges", len(best))
    return list(best.values())


# ---------------------------------------------------------------------------
# Redis helpers
# ---------------------------------------------------------------------------


def _get_redis_client():
    import redis as redis_lib
    return redis_lib.from_url(settings.redis_url)


def _load_set(redis_client, key: str) -> set[str]:
    try:
        raw = redis_client.smembers(key)
        return {s.decode() if isinstance(s, bytes) else s for s in raw}
    except Exception:
        return set()


def _load_exchange_map(redis_client) -> dict[str, str]:
    try:
        raw = redis_client.hgetall(_EXCHANGE_MAP_KEY)
        return {
            (k.decode() if isinstance(k, bytes) else k): (v.decode() if isinstance(v, bytes) else v)
            for k, v in raw.items()
        }
    except Exception:
        return {}


def _save_candidate_pool(redis_client, pool: set[str]) -> None:
    try:
        pipe = redis_client.pipeline()
        pipe.delete(_POOL_KEY)
        if pool:
            pipe.sadd(_POOL_KEY, *pool)
        pipe.expire(_POOL_KEY, 7 * 24 * 3600)
        pipe.execute()
    except Exception:
        logger.warning("Failed to save candidate pool", exc_info=True)


def _save_exchange_map(redis_client, exchange_map: dict[str, str]) -> None:
    try:
        pipe = redis_client.pipeline()
        pipe.delete(_EXCHANGE_MAP_KEY)
        if exchange_map:
            pipe.hset(_EXCHANGE_MAP_KEY, mapping=exchange_map)
        pipe.expire(_EXCHANGE_MAP_KEY, 7 * 24 * 3600)
        pipe.execute()
    except Exception:
        logger.warning("Failed to save exchange map", exc_info=True)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


async def _expand_universe_async():
    from sqlalchemy import select

    from app.advisor.universe_manager import UniverseManager
    from app.models.strategy import Strategy

    if not settings.universe_expansion_enabled:
        logger.info("Universe expansion disabled via feature flag")
        return

    redis_client = _get_redis_client()

    async with task_session() as db:
        # Load active strategies
        strat_result = await db.execute(
            select(Strategy).where(Strategy.is_active == True)  # noqa: E712
        )
        strategies = list(strat_result.scalars().all())

        if not strategies:
            logger.info("expand_symbol_universe: no active strategies")
            return

        primary_strategy = strategies[0]

        # Load persisted state
        candidate_pool = _load_set(redis_client, _POOL_KEY)
        blocklist = _load_set(redis_client, _BLOCKLIST_KEY)
        exchange_map = _load_exchange_map(redis_client)

        # Current watchlist
        watched: set[str] = set()
        for s in strategies:
            watched.update(s.config.get("symbols", []))

        # Fetch tickers from ALL connected exchanges
        tickers = await _fetch_all_connected_exchange_tickers(db)

        if tickers:
            # Volume pre-filter — reduces noise before AI evaluation
            mgr = UniverseManager(
                max_candidates=settings.universe_max_candidates,
                promotion_lookback=settings.universe_promotion_lookback_candles,
            )
            already_known = watched | candidate_pool | blocklist
            volume_filtered = mgr.filter_candidates(
                tickers,
                min_volume_usd=settings.universe_min_volume_usd,
                exclude=already_known,
            )

            if volume_filtered:
                logger.info(
                    "expand_symbol_universe: %d candidates pass volume filter, sending to AI",
                    len(volume_filtered),
                )

                # AI evaluation — Claude decides which are worth monitoring
                scout = SymbolScout()
                approved_symbols = await scout.evaluate_candidates(
                    candidates=volume_filtered,
                    strategy_config=primary_strategy.config,
                    current_watchlist=watched,
                )

                if approved_symbols:
                    logger.info(
                        "expand_symbol_universe: AI approved %d candidates: %s",
                        len(approved_symbols), approved_symbols,
                    )

                    # Record source exchange per approved symbol
                    ticker_exchange = {t["symbol"]: t.get("_exchange", settings.default_exchange) for t in volume_filtered}
                    for sym in approved_symbols:
                        exchange_map[sym] = ticker_exchange.get(sym, settings.default_exchange)

                    # Add to candidate pool
                    candidate_pool.update(approved_symbols)

                    # Backfill per source exchange, then trigger immediate promotion check
                    primary_timeframes = primary_strategy.config.get("timeframes", ["1h", "4h", "1d"])
                    by_exchange: dict[str, list[str]] = defaultdict(list)
                    for sym in approved_symbols:
                        by_exchange[exchange_map[sym]].append(sym)

                    for exc_id, syms in by_exchange.items():
                        backfill_symbols.delay(syms, primary_timeframes, exc_id)
                else:
                    logger.info(
                        "expand_symbol_universe: AI approved no new candidates this cycle"
                    )

        # Safety net: promote any candidates from previous cycles now ready
        from app.tasks.promote_universe_candidates import promote_universe_candidates
        promote_universe_candidates.delay(None)  # checks full pool

        _save_candidate_pool(redis_client, candidate_pool)
        _save_exchange_map(redis_client, exchange_map)

    try:
        redis_client.close()
    except Exception:
        pass
