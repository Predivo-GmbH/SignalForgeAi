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
    from app.engine.layers.risk import RiskConfig
    from app.engine.pipeline import SignalPipeline
    from app.models.signal import Signal as SignalModel
    from app.models.strategy import Strategy

    async with task_session() as db:
        result = await db.execute(
            select(Strategy).where(Strategy.is_active == True).limit(1)  # noqa: E712
        )
        active_strategy = result.scalar_one_or_none()
        if active_strategy is None:
            logger.warning(
                "No active strategy found — skipping pipeline run. "
                "Create and activate a strategy in the UI.",
            )
            return

        # Read config from active strategy (safe defaults for empty configs)
        cfg = active_strategy.config or {}
        symbols = cfg.get("symbols", DEFAULT_SYMBOLS)
        timeframes = cfg.get("timeframes", ["1h"])
        account_equity = cfg.get("account_equity", 10000)
        min_confluence = cfg.get("min_confluence", 50)

        risk_config = RiskConfig(
            max_risk_per_trade=cfg.get("max_risk_per_trade", 0.02),
            max_daily_loss=cfg.get("max_daily_loss", 0.06),
            atr_sl_multiplier=cfg.get("atr_sl_multiplier", 2.0),
            min_risk_reward=cfg.get("min_risk_reward", 1.5),
        )

        pipeline = SignalPipeline(risk_config=risk_config, min_confluence=min_confluence)

        for symbol in symbols:
            for timeframe in timeframes:
                try:
                    candles_data = await CandleStorage.load_candles_db(
                        db, symbol, timeframe, limit=300,
                    )
                    if len(candles_data) < 100:
                        logger.warning(
                            "Insufficient candles for %s %s: %d",
                            symbol, timeframe, len(candles_data),
                        )
                        continue

                    df = pd.DataFrame(candles_data)
                    signal = pipeline.process(
                        symbol, timeframe, df, account_equity=account_equity,
                    )
                    logger.info(
                        "Pipeline for %s %s: action=%s, confluence=%s",
                        symbol, timeframe, signal.action, signal.confluence_score,
                    )

                    # Persist actionable signals (BUY/SELL) to DB
                    if signal.action in ("BUY", "SELL"):
                        entry_price = float(df["close"].iloc[-1])
                        signal_row = SignalModel(
                            strategy_id=active_strategy.id,
                            symbol=symbol,
                            timeframe=timeframe,
                            direction=signal.action,
                            entry_price=entry_price,
                            stop_loss=signal.stop_loss or 0.0,
                            take_profit_1=signal.take_profit_1 or 0.0,
                            take_profit_2=signal.take_profit_2,
                            confluence_score=signal.confluence_score,
                            regime=signal.regime,
                            triggers=signal.triggers,
                            position_size=signal.position_size,
                            status="pending",
                        )
                        db.add(signal_row)
                        logger.info(
                            "Persisted %s signal for %s %s (confluence=%d, entry=%.2f, size=%.6f)",
                            signal.action, symbol, timeframe, signal.confluence_score,
                            entry_price, signal.position_size or 0,
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
                    logger.error("Pipeline failed for %s %s: %s", symbol, timeframe, e)

        await db.commit()
