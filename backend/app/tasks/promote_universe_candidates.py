"""Event-driven promotion of universe candidates into active strategy watchlists.

Called immediately after a backfill completes so newly discovered symbols enter
the active watchlist within minutes, not at the next 6-hour expansion cycle.

Also called by the 6-hour expansion task as a safety net for any symbols that
were waiting on candle history from a previous cycle.
"""

import asyncio
import logging
from collections import defaultdict

import redis as redis_lib

from app.config import settings
from app.core.database import task_session
from app.worker import celery_app

logger = logging.getLogger(__name__)

_POOL_KEY = "signalforge:universe:candidate_pool"
_PROMOTED_KEY = "signalforge:universe:promoted_symbols"
_EXCHANGE_MAP_KEY = "signalforge:universe:candidate_exchange_map"


@celery_app.task(name="promote_universe_candidates", bind=True, max_retries=2)
def promote_universe_candidates(self, symbols: list[str] | None = None):
    """Check candle readiness for candidates and promote those that are ready.

    Args:
        symbols: specific symbols to check. If None, checks the entire candidate pool.
    """
    try:
        asyncio.run(_promote_async(symbols))
    except (ConnectionError, OSError, TimeoutError) as exc:
        logger.warning("promote_universe_candidates transient error: %s — retrying", exc)
        raise self.retry(exc=exc, countdown=30)
    except Exception:
        logger.exception("Unexpected error in promote_universe_candidates")


async def _promote_async(symbols: list[str] | None):
    from sqlalchemy import func, select

    from app.advisor.symbol_rotation import SymbolRotationManager
    from app.models.candle import Candle
    from app.models.strategy import Strategy

    redis_client = redis_lib.from_url(settings.redis_url)

    try:
        # Load candidate pool
        try:
            raw_pool = redis_client.smembers(_POOL_KEY)
            candidate_pool: set[str] = {
                s.decode() if isinstance(s, bytes) else s for s in raw_pool
            }
        except Exception:
            logger.warning("promote_universe_candidates: failed to load candidate pool")
            return

        # Load exchange map
        try:
            raw_map = redis_client.hgetall(_EXCHANGE_MAP_KEY)
            exchange_map: dict[str, str] = {
                (k.decode() if isinstance(k, bytes) else k): (
                    v.decode() if isinstance(v, bytes) else v
                )
                for k, v in raw_map.items()
            }
        except Exception:
            exchange_map = {}

        # Determine which symbols to check
        to_check = list(symbols) if symbols else list(candidate_pool)
        # Only check symbols that are actually in the pool
        to_check = [s for s in to_check if s in candidate_pool]

        if not to_check:
            logger.debug("promote_universe_candidates: nothing to check")
            return

        async with task_session() as db:
            # Load active strategies
            strat_result = await db.execute(
                select(Strategy).where(Strategy.is_active == True)  # noqa: E712
            )
            strategies = list(strat_result.scalars().all())

            if not strategies:
                return

            primary_strategy = strategies[0]
            primary_timeframe = primary_strategy.config.get("timeframes", ["4h"])[0]

            # Current watchlist
            watched: set[str] = set()
            for s in strategies:
                watched.update(s.config.get("symbols", []))

            # Filter to symbols not already watched
            candidates_to_check = [s for s in to_check if s not in watched]
            if not candidates_to_check:
                return

            # Check candle counts
            candle_result = await db.execute(
                select(Candle.symbol, func.count(Candle.symbol).label("cnt"))
                .where(
                    Candle.symbol.in_(candidates_to_check),
                    Candle.timeframe == primary_timeframe,
                )
                .group_by(Candle.symbol)
            )
            candle_counts = {row.symbol: row.cnt for row in candle_result.all()}

            min_candles = settings.universe_promotion_lookback_candles
            has_enough_candles = [
                sym for sym in candidates_to_check
                if candle_counts.get(sym, 0) >= min_candles
            ]

            if not has_enough_candles:
                logger.debug(
                    "promote_universe_candidates: %d checked, none ready yet "
                    "(need %d %s candles)",
                    len(candidates_to_check), min_candles, primary_timeframe,
                )
                return

            # Quality gate: run the signal pipeline on each symbol's recent candles.
            # Only promote if the symbol shows a non-chaotic regime and minimum confluence —
            # having candle history is necessary but not sufficient for a useful watchlist entry.
            import pandas as pd

            from app.data.storage import CandleStorage
            from app.engine.pipeline import SignalPipeline

            pipeline = SignalPipeline(
                min_confluence=primary_strategy.config.get("min_confluence", 70),
            )
            min_signal_confluence = settings.universe_min_signal_confluence
            ready: list[str] = []

            for sym in has_enough_candles:
                try:
                    candles_data = await CandleStorage.load_candles_db(
                        db, sym, primary_timeframe, limit=min_candles,
                    )
                    if len(candles_data) < 100:
                        logger.info(
                            "promote_universe_candidates: %s skipped — "
                            "only %d usable candles after load",
                            sym, len(candles_data),
                        )
                        continue

                    df = pd.DataFrame(candles_data)
                    result = pipeline.process(sym, primary_timeframe, df)

                    if result.regime == "chaotic":
                        logger.info(
                            "promote_universe_candidates: %s rejected — chaotic regime",
                            sym,
                        )
                        continue

                    if result.confluence_score < min_signal_confluence:
                        logger.info(
                            "promote_universe_candidates: %s rejected — "
                            "confluence %d < %d minimum",
                            sym, result.confluence_score, min_signal_confluence,
                        )
                        continue

                    logger.info(
                        "promote_universe_candidates: %s passed quality gate "
                        "(regime=%s, confluence=%d)",
                        sym, result.regime, result.confluence_score,
                    )
                    ready.append(sym)

                except Exception:
                    logger.warning(
                        "promote_universe_candidates: pipeline check failed for %s — skipping",
                        sym, exc_info=True,
                    )

            if not ready:
                logger.info(
                    "promote_universe_candidates: %d had enough candles but none passed "
                    "quality gate (regime + confluence >= %d)",
                    len(has_enough_candles), min_signal_confluence,
                )
                return

            logger.info(
                "promote_universe_candidates: %d/%d symbols passed quality gate: %s",
                len(ready), len(has_enough_candles), ready,
            )

            # Group by source exchange
            by_exchange: dict[str, list[str]] = defaultdict(list)
            for sym in ready:
                exc_id = exchange_map.get(sym, settings.default_exchange)
                by_exchange[exc_id].append(sym)

            rotation = SymbolRotationManager()
            all_added: list[str] = []

            for strategy in strategies:
                for exc_id, syms in by_exchange.items():
                    added = await rotation.add_symbols(
                        strategy, syms, db,
                        exchange=exc_id, source="universe_discovery",
                    )
                    all_added.extend(added)

            if all_added:
                # Remove promoted symbols from candidate pool
                try:
                    pipe = redis_client.pipeline()
                    pipe.srem(_POOL_KEY, *all_added)
                    pipe.sadd(_PROMOTED_KEY, *all_added)
                    pipe.expire(_PROMOTED_KEY, 30 * 24 * 3600)
                    pipe.execute()
                except Exception:
                    logger.warning(
                        "promote_universe_candidates: failed to update Redis after promotion",
                        exc_info=True,
                    )

                logger.info(
                    "promote_universe_candidates: promoted %d symbols into watchlist: %s",
                    len(all_added), all_added,
                )

            await db.commit()

    finally:
        try:
            redis_client.close()
        except Exception:
            pass
