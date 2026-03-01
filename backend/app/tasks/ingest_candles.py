"""Periodic candle ingestion from exchanges."""

import logging

from app.worker import celery_app

logger = logging.getLogger(__name__)

DEFAULT_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
DEFAULT_TIMEFRAMES = ["1h", "4h"]

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

    async with task_session() as db:
        for symbol in DEFAULT_SYMBOLS:
            for timeframe in DEFAULT_TIMEFRAMES:
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
