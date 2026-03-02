"""Periodic candle ingestion from exchanges."""

import logging

from app.worker import celery_app

logger = logging.getLogger(__name__)

DEFAULT_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
DEFAULT_TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"]

MIN_CANDLES_FOR_PIPELINE = 300
BACKFILL_LIMIT = 500
INCREMENTAL_LIMIT = 50


@celery_app.task(name="ingest_candles", bind=True, max_retries=3)
def ingest_candles(self):
    """Fetch latest candles for all active symbols and store in DB."""
    import asyncio

    asyncio.run(_ingest_async())


async def _ingest_async():
    from app.core.database import task_session
    from app.data.ingestion import CCXTIngestion
    from app.data.storage import CandleStorage

    ingestion = CCXTIngestion("binance")

    # Collect symbols from active strategies
    from sqlalchemy import select
    from app.models.strategy import Strategy

    symbols = set(DEFAULT_SYMBOLS)
    timeframes = set(DEFAULT_TIMEFRAMES)

    async with task_session() as db:
        result = await db.execute(
            select(Strategy).where(Strategy.is_active == True)  # noqa: E712
        )
        for strategy in result.scalars().all():
            cfg = strategy.config or {}
            for s in cfg.get("symbols", []):
                symbols.add(s)
            for t in cfg.get("timeframes", []):
                timeframes.add(t)

        for symbol in symbols:
            for timeframe in timeframes:
                try:
                    # Check how many candles we already have
                    existing = await CandleStorage.load_candles_db(
                        db, symbol, timeframe, limit=1,
                    )
                    if len(existing) == 0:
                        # First run — backfill historical data
                        limit = BACKFILL_LIMIT
                        logger.info(
                            "Backfilling %d candles for %s %s",
                            limit, symbol, timeframe,
                        )
                    else:
                        limit = INCREMENTAL_LIMIT

                    candles = ingestion.fetch_candles(symbol, timeframe, limit=limit)
                    if not candles.empty:
                        count = await CandleStorage.save_candles_db(
                            db, symbol, timeframe, candles,
                        )
                        logger.info(
                            "Ingested %d candles for %s %s", count, symbol, timeframe,
                        )
                except Exception as e:
                    logger.error("Ingestion failed for %s %s: %s", symbol, timeframe, e)
        await db.commit()


@celery_app.task(name="backfill_symbols")
def backfill_symbols(symbols: list[str], timeframes: list[str] | None = None):
    """One-time backfill for a list of symbols (triggered by advisor deploy)."""
    import asyncio

    asyncio.run(_backfill_async(symbols, timeframes or DEFAULT_TIMEFRAMES))


async def _backfill_async(symbols: list[str], timeframes: list[str]):
    from app.core.database import task_session
    from app.data.ingestion import CCXTIngestion
    from app.data.storage import CandleStorage

    ingestion = CCXTIngestion("binance")

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
                            "Backfilled %d candles for %s %s", count, symbol, timeframe,
                        )
                except Exception as e:
                    logger.error("Backfill failed for %s %s: %s", symbol, timeframe, e)
        await db.commit()
