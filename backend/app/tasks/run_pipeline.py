"""Periodic signal pipeline execution."""

import json
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
    from sqlalchemy import select

    from app.core.database import task_session
    from app.data.storage import CandleStorage
    from app.engine.pipeline import SignalPipeline
    from app.models.signal import Signal as SignalModel
    from app.models.strategy import Strategy

    pipeline = SignalPipeline()

    async with task_session() as db:
        # Find the first active strategy to link signals to
        result = await db.execute(
            select(Strategy).where(Strategy.is_active == True).limit(1)  # noqa: E712
        )
        active_strategy = result.scalar_one_or_none()
        if active_strategy is None:
            logger.warning(
                "No active strategy found — signals will be generated but not "
                "linked for execution. Create and activate a strategy in the UI.",
            )

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

                # Persist actionable signals (BUY/SELL) to DB
                if signal.action in ("BUY", "SELL") and active_strategy is not None:
                    entry_price = float(df["close"].iloc[-1])
                    signal_row = SignalModel(
                        strategy_id=active_strategy.id,
                        symbol=symbol,
                        timeframe="1h",
                        direction=signal.action,
                        entry_price=entry_price,
                        stop_loss=signal.stop_loss or 0.0,
                        take_profit_1=signal.take_profit_1 or 0.0,
                        take_profit_2=signal.take_profit_2,
                        confluence_score=signal.confluence_score,
                        regime=signal.regime,
                        triggers=signal.triggers,
                        status="pending",
                    )
                    db.add(signal_row)
                    logger.info(
                        "Persisted %s signal for %s (confluence=%d, entry=%.2f)",
                        signal.action, symbol, signal.confluence_score, entry_price,
                    )

                    # Publish to Redis for real-time WebSocket feed
                    try:
                        from app.core.redis_client import redis_client

                        await redis_client.publish(
                            "signalforge:signals",
                            json.dumps({
                                "symbol": symbol,
                                "action": signal.action,
                                "confluence_score": signal.confluence_score,
                                "entry_price": entry_price,
                                "regime": signal.regime,
                            }),
                        )
                    except Exception:
                        pass  # Redis publish is best-effort

            except Exception as e:
                logger.error("Pipeline failed for %s: %s", symbol, e)

        await db.commit()
