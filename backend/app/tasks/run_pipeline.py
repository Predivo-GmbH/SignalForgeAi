"""Periodic signal pipeline execution."""

import logging

from app.worker import celery_app

logger = logging.getLogger(__name__)

DEFAULT_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]


@celery_app.task(name="run_signal_pipeline", bind=True, max_retries=3)
def run_signal_pipeline(self):
    """Run the signal pipeline for all active symbols."""
    import asyncio

    asyncio.run(_run_pipeline_async())


async def _run_pipeline_async():
    import pandas as pd

    from app.core.database import async_session
    from app.data.storage import CandleStorage
    from app.engine.pipeline import SignalPipeline

    pipeline = SignalPipeline()

    async with async_session() as db:
        for symbol in DEFAULT_SYMBOLS:
            try:
                candles_data = await CandleStorage.load_candles_db(
                    db, symbol, "1h", limit=300,
                )
                if len(candles_data) < 100:
                    logger.warning(
                        "Insufficient candles for %s: %d", symbol, len(candles_data),
                    )
                    continue

                df = pd.DataFrame(candles_data)
                signal = pipeline.process(symbol, "1h", df)
                logger.info(
                    "Pipeline for %s: action=%s, confluence=%s",
                    symbol,
                    signal.action,
                    signal.confluence_score,
                )
            except Exception as e:
                logger.error("Pipeline failed for %s: %s", symbol, e)
