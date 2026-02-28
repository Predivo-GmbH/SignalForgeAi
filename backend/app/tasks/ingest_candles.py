"""Periodic candle ingestion from exchanges."""

import logging

from app.worker import celery_app

logger = logging.getLogger(__name__)

DEFAULT_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
DEFAULT_TIMEFRAMES = ["1h", "4h"]


@celery_app.task(name="ingest_candles", bind=True, max_retries=3)
def ingest_candles(self):
    """Fetch latest candles for all active symbols and store in DB."""
    import asyncio

    asyncio.run(_ingest_async())


async def _ingest_async():
    from app.core.database import async_session
    from app.data.ingestion import CCXTIngestion
    from app.data.storage import CandleStorage

    ingestion = CCXTIngestion("binance")

    async with async_session() as db:
        for symbol in DEFAULT_SYMBOLS:
            for timeframe in DEFAULT_TIMEFRAMES:
                try:
                    candles = ingestion.fetch_candles(symbol, timeframe, limit=50)
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
