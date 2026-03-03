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

    try:
        asyncio.run(_run_pipeline_async())
    except (ConnectionError, OSError, TimeoutError) as exc:
        logger.warning("run_signal_pipeline transient error: %s — retrying", exc)
        self.retry(exc=exc, countdown=60)


async def _run_pipeline_async():
    from sqlalchemy import select

    from app.core.database import task_session
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

        pending_publishes: list[dict] = []
        for active_strategy in active_strategies:
            await _run_strategy_pipeline(db, active_strategy, pending_publishes)

        await db.commit()

        # Publish to Redis AFTER DB commit so WS clients only see committed signals
        if pending_publishes:
            try:
                from app.core.redis_client import redis_client

                for msg in pending_publishes:
                    await redis_client.publish(
                        "signalforge:signals", json.dumps(msg),
                    )
            except Exception as pub_err:
                logger.warning("Redis publish failed: %s", pub_err)


async def _run_strategy_pipeline(db, active_strategy, pending_publishes: list[dict] | None = None):
    """Run the signal pipeline for a single strategy."""
    import pandas as pd

    from app.data.storage import CandleStorage
    from app.engine.layers.feedback_filter import FeedbackFilter
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

    pipeline = SignalPipeline(
        risk_config=risk_config,
        min_confluence=min_confluence,
        min_trigger_count=cfg.get("min_trigger_count", 2),
        trigger_lookback_candles=cfg.get("trigger_lookback_candles", 1),
        ema_slope_threshold=cfg.get("ema_slope_threshold", 0.001),
    )

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

    feedback_filter = FeedbackFilter()

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
                    "Strategy '%s' | %s %s: action=%s, confluence=%s, block=%s",
                    active_strategy.name, symbol, timeframe,
                    signal.action, signal.confluence_score, signal.block_reason,
                )

                # Persist actionable signals (BUY/SELL) to DB
                if signal.action in ("BUY", "SELL"):
                    # --- Feedback Filter: apply learned rules ---
                    skip, skip_reason = await feedback_filter.should_skip(
                        symbol=symbol,
                        regime=signal.regime,
                        db=db,
                        strategy_id=str(active_strategy.id),
                    )
                    if skip:
                        logger.info(
                            "FeedbackFilter SKIP: %s %s %s — %s (strategy=%s)",
                            signal.action, symbol, timeframe,
                            skip_reason, active_strategy.name,
                        )
                        continue

                    confluence_override = await feedback_filter.get_confluence_override(
                        symbol=symbol,
                        regime=signal.regime,
                        db=db,
                        strategy_id=str(active_strategy.id),
                    )
                    if confluence_override and signal.confluence_score < confluence_override:
                        logger.info(
                            "FeedbackFilter: %s %s confluence %d "
                            "< learned threshold %d — skipping "
                            "(strategy=%s)",
                            symbol, timeframe, signal.confluence_score,
                            confluence_override, active_strategy.name,
                        )
                        continue

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

                    # Dedup: skip if identical pending signal already exists
                    from sqlalchemy import select as sa_select
                    existing_sig = await db.execute(
                        sa_select(SignalModel.id).where(
                            SignalModel.strategy_id == active_strategy.id,
                            SignalModel.symbol == symbol,
                            SignalModel.timeframe == timeframe,
                            SignalModel.direction == signal.action,
                            SignalModel.status == "pending",
                        ).limit(1)
                    )
                    if existing_sig.scalar_one_or_none():
                        logger.info(
                            "Skipping duplicate pending signal: %s %s %s (strategy=%s)",
                            signal.action, symbol, timeframe, active_strategy.name,
                        )
                        continue

                    signal_row = SignalModel(
                        user_id=active_strategy.user_id,
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
                        "Persisted %s signal for %s %s "
                        "(strategy=%s, confluence=%d, "
                        "entry=%.2f, size=%.6f)",
                        signal.action, symbol, timeframe,
                        active_strategy.name,
                        signal.confluence_score,
                        entry_price, position_size,
                    )

                    # AI enrichment — failures reject the signal (no trading without AI)
                    await _ai_enrich_signal(signal, signal_row, db, df)

                    # Honor AI reject in live mode
                    if signal_row.ai_recommendation == "reject":
                        signal_row.status = "rejected"
                        logger.info(
                            "AI REJECT (live): %s %s %s (strategy=%s, quality=%s, reason=%s)",
                            signal.action, symbol, timeframe,
                            active_strategy.name,
                            signal_row.ai_quality_score,
                            (signal_row.ai_reasoning or "")[:100],
                        )
                        continue

                    # Collect for post-commit Redis publish
                    if pending_publishes is not None:
                        pending_publishes.append({
                            "strategy_id": str(active_strategy.id),
                            "strategy_name": active_strategy.name,
                            "symbol": symbol,
                            "action": signal.action,
                            "confluence_score": signal.confluence_score,
                            "entry_price": entry_price,
                            "regime": signal.regime,
                            "ai_quality_score": signal_row.ai_quality_score,
                            "ai_recommendation": signal_row.ai_recommendation,
                        })

            except Exception as e:
                logger.exception(
                    "Pipeline failed for %s %s (strategy=%s): %s",
                    symbol, timeframe, active_strategy.name, e,
                )


async def _ai_enrich_signal(signal, signal_row, db, df):
    """Run AI enrichment on a BUY/SELL signal.

    If enrichment fails for any reason, the signal is marked as rejected —
    the system does not trade without AI analysis.
    """
    from app.config import settings

    try:
        signal_data = {
            "action": signal.action,
            "symbol": signal.symbol,
            "timeframe": signal.timeframe,
            "regime": signal.regime,
            "trend_direction": signal.trend_direction,
            "trend_strength": signal.trend_strength,
            "confluence_score": signal.confluence_score,
            "triggers": signal.triggers,
            "risk_reward": signal.risk_reward,
        }

        candle_summary = []
        for _, row in df.tail(5).iloc[::-1].iterrows():
            candle_summary.append({
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
            })

        confluence_details = signal.confluence_details or {}

        # Multi-timeframe analysis
        mtf_data = None
        if settings.ai_multi_timeframe_enabled:
            from app.advisor.multi_tf_analyzer import MultiTimeframeAnalyzer

            mtf_analyzer = MultiTimeframeAnalyzer()
            mtf_data = await mtf_analyzer.analyze(signal.symbol, signal_data, db)
            signal_row.mtf_confidence = mtf_data.get("mtf_confidence")
            signal_row.mtf_alignment = mtf_data.get("timeframe_alignment")

        # Signal quality evaluation
        if settings.ai_signal_quality_enabled:
            from app.advisor.signal_quality import SignalQualityEvaluator

            evaluator = SignalQualityEvaluator()
            quality = await evaluator.evaluate(
                signal_data, confluence_details, candle_summary, mtf_data,
            )
            signal_row.ai_quality_score = quality["quality_score"]
            signal_row.ai_reasoning = quality["reasoning"]
            signal_row.ai_recommendation = quality["recommendation"]

            # Apply position size adjustment if recommended
            size_factor = quality.get("risk_adjustments", {}).get(
                "position_size_factor", 1.0,
            )
            if size_factor != 1.0 and signal_row.position_size:
                original = signal_row.position_size
                signal_row.position_size *= size_factor
                logger.info(
                    "AI quality: adjusted position_size %.6f -> %.6f (factor=%.2f)",
                    original, signal_row.position_size, size_factor,
                )

    except Exception:
        logger.exception(
            "AI enrichment failed for %s — rejecting signal "
            "(no trading without AI)",
            signal.symbol,
        )
        signal_row.ai_recommendation = "reject"
        signal_row.ai_reasoning = (
            "AI enrichment failed — signal rejected. "
            "The system does not trade without AI analysis."
        )
        signal_row.ai_quality_score = 0
