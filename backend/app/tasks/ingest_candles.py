"""Periodic candle ingestion from exchanges."""

import logging
from collections import defaultdict

from app.worker import celery_app

logger = logging.getLogger(__name__)

DEFAULT_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
DEFAULT_TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"]

MIN_CANDLES_FOR_PIPELINE = 300  # Minimum candles needed for reliable indicator calculation
BACKFILL_LIMIT = 500  # Max candles to fetch on initial backfill
INCREMENTAL_LIMIT = 50  # Max candles to fetch on incremental update


@celery_app.task(name="ingest_candles", bind=True, max_retries=3)
def ingest_candles(self):
    """Fetch latest candles for all active symbols and store in DB."""
    import asyncio

    from app.tasks.task_utils import task_lock

    with task_lock("ingest_candles", timeout=120) as acquired:
        if not acquired:
            return
        try:
            asyncio.run(_ingest_async())
        except (ConnectionError, OSError, TimeoutError) as exc:
            logger.warning("ingest_candles transient error: %s — retrying", exc)
            raise self.retry(exc=exc, countdown=30)
        except Exception:
            logger.exception("Unexpected error in ingest_candles")


async def _resolve_exchange_symbols(db) -> dict[str, set[tuple[str, str]]]:
    """Build a mapping of exchange -> set of (symbol, timeframe) pairs.

    Resolution order for each symbol:
      1. Strategy config ``exchange_map`` (set when simulation starts,
         maps each symbol to its source exchange like "mexc", "kucoin")
      2. User's BrokerConnection.broker (fallback for manually created strategies)
      3. settings.default_exchange (ultimate fallback)

    Invalid exchange names (e.g. "manual", "trading") are skipped and
    the symbol falls through to the next resolution level.
    """
    import ccxt
    from sqlalchemy import select

    from app.config import settings
    from app.models.strategy import BrokerConnection, Strategy

    default_ex = settings.default_exchange
    valid_exchanges = set(ccxt.exchanges)

    # exchange -> {(symbol, timeframe), ...}
    exchange_pairs: dict[str, set[tuple[str, str]]] = defaultdict(set)

    # Default symbols always go to the default exchange
    for sym in DEFAULT_SYMBOLS:
        for tf in DEFAULT_TIMEFRAMES:
            exchange_pairs[default_ex].add((sym, tf))

    # Collect from active strategies
    result = await db.execute(
        select(Strategy).where(Strategy.is_active == True)  # noqa: E712
    )
    strategies = result.scalars().all()

    # Look up broker connections for strategy owners (fallback only)
    user_ids = {s.user_id for s in strategies}
    broker_map: dict[str, str] = {}  # user_id -> exchange
    if user_ids:
        broker_result = await db.execute(
            select(BrokerConnection).where(BrokerConnection.user_id.in_(user_ids))
        )
        for bc in broker_result.scalars().all():
            if bc.user_id not in broker_map or bc.purpose == "read":
                broker_map[str(bc.user_id)] = bc.broker

    for strategy in strategies:
        cfg = strategy.config or {}
        # Per-symbol exchange mapping (from simulation start / holdings source)
        sym_exchange_map = cfg.get("exchange_map", {})
        fallback_exchange = broker_map.get(str(strategy.user_id), default_ex)
        for sym in cfg.get("symbols", []):
            mapped_exchange = sym_exchange_map.get(sym)
            # Validate: only use mapped exchange if it's a real CCXT exchange
            if mapped_exchange and mapped_exchange in valid_exchanges:
                exchange = mapped_exchange
            else:
                if mapped_exchange:
                    logger.warning(
                        "Invalid exchange '%s' in exchange_map for %s — using fallback '%s'",
                        mapped_exchange, sym, fallback_exchange,
                    )
                exchange = fallback_exchange
            for tf in cfg.get("timeframes", DEFAULT_TIMEFRAMES):
                exchange_pairs[exchange].add((sym, tf))

    return dict(exchange_pairs)


async def _ingest_async():
    import ccxt as ccxt_sync

    from app.core.database import task_session
    from app.data.ingestion import CCXTIngestion
    from app.data.storage import CandleStorage

    # Fallback exchanges to try when a symbol isn't found on its primary exchange
    fallback_exchanges = ["binance", "kucoin", "mexc", "kraken", "gateio"]

    async with task_session() as db:
        exchange_pairs = await _resolve_exchange_symbols(db)

        # Track symbols that fail with BadSymbol on their primary exchange
        # Key: (symbol, timeframe), Value: primary exchange that failed
        bad_symbol_failures: dict[tuple[str, str], str] = {}
        # Track which exchanges we've already initialized
        ingestion_cache: dict[str, CCXTIngestion] = {}

        for exchange_id, pairs in exchange_pairs.items():
            try:
                ingestion = CCXTIngestion(exchange_id)
                ingestion_cache[exchange_id] = ingestion
            except Exception:
                logger.exception("Failed to initialize exchange: %s", exchange_id)
                continue

            for symbol, timeframe in pairs:
                try:
                    existing = await CandleStorage.load_candles_db(
                        db, symbol, timeframe, limit=1,
                        exchange=exchange_id,
                    )
                    if len(existing) == 0:
                        limit = BACKFILL_LIMIT
                        logger.info(
                            "Backfilling %d candles for %s %s from %s",
                            limit, symbol, timeframe, exchange_id,
                        )
                    else:
                        limit = INCREMENTAL_LIMIT

                    candles = ingestion.fetch_candles(symbol, timeframe, limit=limit)
                    if not candles.empty:
                        count = await CandleStorage.save_candles_db(
                            db, symbol, timeframe, candles,
                        )
                        logger.info(
                            "Ingested %d candles for %s %s from %s",
                            count, symbol, timeframe, exchange_id,
                        )
                except ccxt_sync.BadSymbol:
                    logger.warning(
                        "%s does not list %s — will try fallback exchanges",
                        exchange_id, symbol,
                    )
                    bad_symbol_failures[(symbol, timeframe)] = exchange_id
                except Exception as e:
                    logger.exception(
                        "Ingestion failed for %s %s on %s: %s",
                        symbol, timeframe, exchange_id, e,
                    )

        # --- Retry failed symbols on fallback exchanges ---
        if bad_symbol_failures:
            logger.info(
                "Retrying %d symbol/timeframe pairs on fallback exchanges",
                len(bad_symbol_failures),
            )
            for (symbol, timeframe), failed_exchange in bad_symbol_failures.items():
                for fallback_id in fallback_exchanges:
                    if fallback_id == failed_exchange:
                        continue  # Already tried this one
                    try:
                        if fallback_id not in ingestion_cache:
                            ingestion_cache[fallback_id] = CCXTIngestion(fallback_id)
                        fb_ingestion = ingestion_cache[fallback_id]

                        candles = fb_ingestion.fetch_candles(
                            symbol, timeframe, limit=BACKFILL_LIMIT,
                        )
                        if not candles.empty:
                            count = await CandleStorage.save_candles_db(
                                db, symbol, timeframe, candles,
                            )
                            logger.info(
                                "Fallback: ingested %d candles for %s %s from %s",
                                count, symbol, timeframe, fallback_id,
                            )
                            break  # Success — stop trying other exchanges
                    except ccxt_sync.BadSymbol:
                        continue  # Not on this exchange either
                    except Exception:
                        logger.warning(
                            "Fallback ingestion failed for %s %s on %s",
                            symbol, timeframe, fallback_id, exc_info=True,
                        )
                        continue
                else:
                    logger.warning(
                        "No exchange found for %s %s — symbol will have insufficient data",
                        symbol, timeframe,
                    )

        await db.commit()


@celery_app.task(name="backfill_symbols", bind=True, max_retries=3)
def backfill_symbols(
    self,
    symbols: list[str],
    timeframes: list[str] | None = None,
    exchange: str | None = None,
):
    """One-time backfill for a list of symbols (triggered by advisor deploy)."""
    import asyncio

    from app.config import settings

    ex = exchange or settings.default_exchange
    try:
        asyncio.run(_backfill_async(symbols, timeframes or DEFAULT_TIMEFRAMES, ex))
        # Trigger immediate promotion check — if these symbols are universe candidates
        # with enough candles now, they enter the active watchlist within minutes.
        from app.tasks.promote_universe_candidates import promote_universe_candidates
        promote_universe_candidates.delay(symbols)
    except (ConnectionError, OSError, TimeoutError) as exc:
        logger.warning("backfill_symbols transient error: %s — retrying", exc)
        self.retry(exc=exc, countdown=60)


async def _backfill_async(symbols: list[str], timeframes: list[str], exchange: str):
    from app.core.database import task_session
    from app.data.ingestion import CCXTIngestion
    from app.data.storage import CandleStorage

    ingestion = CCXTIngestion(exchange)

    async with task_session() as db:
        for symbol in symbols:
            for timeframe in timeframes:
                try:
                    candles = ingestion.fetch_candles(symbol, timeframe, limit=BACKFILL_LIMIT)
                    if not candles.empty:
                        count = await CandleStorage.save_candles_db(
                            db, symbol, timeframe, candles,
                        )
                        logger.info(
                            "Backfilled %d candles for %s %s from %s",
                            count, symbol, timeframe, exchange,
                        )
                except Exception as e:
                    logger.exception(
                        "Backfill failed for %s %s on %s: %s",
                        symbol, timeframe, exchange, e,
                    )
        await db.commit()
