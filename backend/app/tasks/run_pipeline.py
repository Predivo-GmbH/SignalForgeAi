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
        # Process ALL active strategies (parallel strategy comparison)
        result = await db.execute(
            select(Strategy).where(Strategy.is_active == True)  # noqa: E712
        )
        active_strategies = result.scalars().all()
        if not active_strategies:
            logger.warning(
                "No active strategy found — skipping pipeline run. "
                "Create and activate a strategy in the UI.",
            )
            return

        logger.info("Running pipeline for %d active strategies", len(active_strategies))

        for active_strategy in active_strategies:
            await _run_strategy_pipeline(db, active_strategy)

        await db.commit()


async def _run_strategy_pipeline(db, active_strategy):
    """Run the signal pipeline for a single strategy."""
    import pandas as pd

    from app.data.storage import CandleStorage
    from app.engine.layers.risk import RiskConfig
    from app.engine.pipeline import SignalPipeline
    from app.models.signal import Signal as SignalModel

    cfg = active_strategy.config or {}
    symbols = cfg.get("symbols", DEFAULT_SYMBOLS)
    timeframes = cfg.get("timeframes", ["1h"])
    account_equity = cfg.get("account_equity", 10000)
    min_confluence = cfg.get("min_confluence", 50)

    # --- Kelly Criterion sizing (Feature 3) ---
    kelly_risk_pct = None
    if cfg.get("kelly_enabled", False):
        try:
            from app.execution.kelly import KellyCalculator

            kelly_risk_pct = await KellyCalculator.compute(
                db,
                str(active_strategy.id),
                min_trades=cfg.get("kelly_min_trades", 20),
                fraction=cfg.get("kelly_fraction", 0.5),
                lookback=cfg.get("kelly_lookback", 50),
                max_risk_per_trade=cfg.get("max_risk_per_trade", 0.02),
            )
        except Exception as e:
            logger.warning("Kelly calculation failed for strategy %s: %s", active_strategy.id, e)

    risk_config = RiskConfig(
        max_risk_per_trade=kelly_risk_pct or cfg.get("max_risk_per_trade", 0.02),
        max_daily_loss=cfg.get("max_daily_loss", 0.06),
        atr_sl_multiplier=cfg.get("atr_sl_multiplier", 2.0),
        min_risk_reward=cfg.get("min_risk_reward", 1.5),
    )

    pipeline = SignalPipeline(risk_config=risk_config, min_confluence=min_confluence)

    # --- CPPI exposure scaling (Feature 6) ---
    cppi_exposure = 1.0
    if cfg.get("cppi_enabled", False):
        try:
            from app.execution.cppi import CPPIManager

            cppi = CPPIManager(
                multiplier=cfg.get("cppi_multiplier", 3.0),
                max_drawdown_pct=cfg.get("cppi_max_drawdown_pct", 0.15),
            )
            cppi_exposure = await cppi.calculate_exposure(
                str(active_strategy.user_id), account_equity,
            )
        except Exception as e:
            logger.warning("CPPI calculation failed for strategy %s: %s", active_strategy.id, e)

    logger.info(
        "Strategy '%s' (id=%s): processing %d symbols × %d timeframes "
        "(kelly=%s, cppi_exp=%.2f)",
        active_strategy.name, active_strategy.id, len(symbols), len(timeframes),
        f"{kelly_risk_pct:.4f}" if kelly_risk_pct else "off",
        cppi_exposure,
    )

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
                    "Strategy '%s' | %s %s: action=%s, confluence=%s",
                    active_strategy.name, symbol, timeframe,
                    signal.action, signal.confluence_score,
                )

                # Persist actionable signals (BUY/SELL) to DB
                if signal.action in ("BUY", "SELL"):
                    entry_price = float(df["close"].iloc[-1])

                    # Apply CPPI scaling to position size
                    position_size = signal.position_size or 0
                    if cppi_exposure < 1.0 and position_size > 0:
                        original_size = position_size
                        position_size *= cppi_exposure
                        logger.info(
                            "CPPI: scaled position_size %.6f -> %.6f (exposure=%.2f)",
                            original_size, position_size, cppi_exposure,
                        )

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
                        position_size=position_size,
                        status="pending",
                    )
                    db.add(signal_row)
                    logger.info(
                        "Persisted %s signal for %s %s (strategy=%s, confluence=%d, entry=%.2f, size=%.6f)",
                        signal.action, symbol, timeframe, active_strategy.name,
                        signal.confluence_score, entry_price, position_size,
                    )

                    # Publish to Redis for real-time WebSocket feed
                    try:
                        from app.core.redis_client import redis_client

                        await redis_client.publish(
                            "signalforge:signals",
                            json.dumps({
                                "strategy_id": str(active_strategy.id),
                                "strategy_name": active_strategy.name,
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
                logger.error(
                    "Pipeline failed for %s %s (strategy=%s): %s",
                    symbol, timeframe, active_strategy.name, e,
                )
