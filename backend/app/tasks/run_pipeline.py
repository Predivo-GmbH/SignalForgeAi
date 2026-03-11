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

    from app.tasks.task_utils import task_lock

    with task_lock("run_signal_pipeline", timeout=3600) as acquired:
        if not acquired:
            return
        try:
            asyncio.run(_run_pipeline_async())
        except (ConnectionError, OSError, TimeoutError) as exc:
            logger.warning("run_signal_pipeline transient error: %s — retrying", exc)
            raise self.retry(exc=exc, countdown=60)


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
    from app.engine.layers.trend import Trend, TrendFilter
    from app.engine.pipeline import SignalPipeline
    from app.execution.position_manager import PositionManagerDB
    from app.models.pipeline_log import PipelineLog
    from app.models.signal import Signal as SignalModel

    cfg = active_strategy.config or {}
    symbols = cfg.get("symbols", DEFAULT_SYMBOLS)
    timeframes = cfg.get("timeframes", ["1h"])
    exchange_map = cfg.get("exchange_map", {})

    # Collect pipeline decision logs for bulk insert
    log_entries: list[PipelineLog] = []
    account_equity = cfg.get("account_equity", 10000)
    min_confluence = cfg.get("min_confluence", 50)

    risk_config = RiskConfig(
        max_risk_per_trade=cfg.get("max_risk_per_trade", 0.02),
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

    feedback_filter = FeedbackFilter()

    logger.info(
        "Strategy '%s' (id=%s): processing %d symbols × %d timeframes",
        active_strategy.name, active_strategy.id, len(symbols), len(timeframes),
    )

    # Resolve default exchange once for symbols not in exchange_map
    from app.config import settings as _settings
    _default_exchange = _settings.default_exchange

    for symbol in symbols:
        # Determine which exchange's candles to use for this symbol
        sym_exchange = exchange_map.get(symbol) or _default_exchange

        for timeframe in timeframes:
            try:
                candles_data = await CandleStorage.load_candles_db(
                    db, symbol, timeframe, limit=300,
                    exchange=sym_exchange,
                )
                # Fallback: if mapped exchange has insufficient data,
                # try loading from any exchange (covers fallback ingestions)
                if len(candles_data) < 100:
                    candles_data = await CandleStorage.load_candles_db(
                        db, symbol, timeframe, limit=300,
                    )
                if len(candles_data) < 100:
                    logger.warning(
                        "Insufficient candles for %s %s: %d",
                        symbol, timeframe, len(candles_data),
                    )
                    log_entries.append(PipelineLog(
                        strategy_id=active_strategy.id, symbol=symbol,
                        timeframe=timeframe, action="NO_TRADE",
                        block_reason="insufficient_candles",
                    ))
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

                # Log NO_TRADE decisions from the technical pipeline
                if signal.action == "NO_TRADE":
                    log_entries.append(PipelineLog(
                        strategy_id=active_strategy.id, symbol=symbol,
                        timeframe=timeframe, action="NO_TRADE",
                        block_reason=signal.block_reason or "unknown",
                        confluence_score=signal.confluence_score,
                        regime=signal.regime,
                    ))

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
                        log_entries.append(PipelineLog(
                            strategy_id=active_strategy.id, symbol=symbol,
                            timeframe=timeframe, action=signal.action,
                            block_reason="feedback_filter",
                            confluence_score=signal.confluence_score,
                            regime=signal.regime,
                        ))
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
                        log_entries.append(PipelineLog(
                            strategy_id=active_strategy.id, symbol=symbol,
                            timeframe=timeframe, action=signal.action,
                            block_reason="confluence_override",
                            confluence_score=signal.confluence_score,
                            regime=signal.regime,
                        ))
                        continue

                    # --- Cooldown check: prevent re-entry too soon after close ---
                    cooldown_hours = cfg.get("cooldown_hours", 0)
                    if cooldown_hours > 0 and signal.action == "BUY":
                        from app.core.redis_client import redis_client

                        cooldown_key = f"signalforge:cooldown:{active_strategy.user_id}:{symbol}"
                        if await redis_client.exists(cooldown_key):
                            logger.info(
                                "Cooldown SKIP: BUY %s %s — cooldown active "
                                "(strategy=%s)",
                                symbol, timeframe, active_strategy.name,
                            )
                            log_entries.append(PipelineLog(
                                strategy_id=active_strategy.id, symbol=symbol,
                                timeframe=timeframe, action="BUY",
                                block_reason="cooldown",
                                confluence_score=signal.confluence_score,
                                regime=signal.regime,
                            ))
                            continue

                    # --- Position-aware filter: prevent invalid signals ---
                    # BUY: only allowed when no BUY position exists for this symbol
                    # SELL: only allowed when a BUY position exists (to close it)
                    buy_position = await PositionManagerDB.find_open_position(
                        db, str(active_strategy.user_id), symbol, direction="BUY",
                    )
                    if signal.action == "BUY" and buy_position:
                        logger.info(
                            "PositionFilter SKIP: BUY %s %s — open BUY position "
                            "already exists (strategy=%s)",
                            symbol, timeframe, active_strategy.name,
                        )
                        log_entries.append(PipelineLog(
                            strategy_id=active_strategy.id, symbol=symbol,
                            timeframe=timeframe, action="BUY",
                            block_reason="position_filter",
                            confluence_score=signal.confluence_score,
                            regime=signal.regime,
                        ))
                        continue
                    if signal.action == "SELL" and not buy_position:
                        logger.info(
                            "PositionFilter SKIP: SELL %s %s — no open BUY "
                            "position to close (strategy=%s)",
                            symbol, timeframe, active_strategy.name,
                        )
                        log_entries.append(PipelineLog(
                            strategy_id=active_strategy.id, symbol=symbol,
                            timeframe=timeframe, action="SELL",
                            block_reason="position_filter",
                            confluence_score=signal.confluence_score,
                            regime=signal.regime,
                        ))
                        continue

                    # --- Multi-timeframe alignment gate ---
                    # Before spending AI credits, verify higher TFs don't contradict.
                    # Hierarchy: 1h → 4h → 1d.  Only block on explicit conflict.
                    higher_tf_map = {"1h": "4h", "4h": "1d"}
                    higher_tf = higher_tf_map.get(timeframe)
                    if higher_tf:
                        htf_candles = await CandleStorage.load_candles_db(
                            db, symbol, higher_tf, limit=300,
                            exchange=sym_exchange,
                        )
                        if len(htf_candles) >= 200:
                            htf_df = pd.DataFrame(htf_candles)
                            htf_trend = TrendFilter(
                                slope_threshold=cfg.get("ema_slope_threshold", 0.001),
                            ).evaluate(htf_df)

                            if (
                                signal.action == "BUY"
                                and htf_trend.direction == Trend.BEARISH
                            ):
                                logger.info(
                                    "MTF SKIP: BUY %s %s blocked — %s trend "
                                    "is BEARISH (strategy=%s)",
                                    symbol, timeframe, higher_tf,
                                    active_strategy.name,
                                )
                                log_entries.append(PipelineLog(
                                    strategy_id=active_strategy.id, symbol=symbol,
                                    timeframe=timeframe, action="BUY",
                                    block_reason="mtf_filter",
                                    confluence_score=signal.confluence_score,
                                    regime=signal.regime,
                                ))
                                continue
                            if (
                                signal.action == "SELL"
                                and htf_trend.direction == Trend.BULLISH
                            ):
                                logger.info(
                                    "MTF SKIP: SELL %s %s blocked — %s trend "
                                    "is BULLISH (strategy=%s)",
                                    symbol, timeframe, higher_tf,
                                    active_strategy.name,
                                )
                                log_entries.append(PipelineLog(
                                    strategy_id=active_strategy.id, symbol=symbol,
                                    timeframe=timeframe, action="SELL",
                                    block_reason="mtf_filter",
                                    confluence_score=signal.confluence_score,
                                    regime=signal.regime,
                                ))
                                continue

                    entry_price = float(df["close"].iloc[-1])
                    position_size = signal.position_size or 0

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
                        log_entries.append(PipelineLog(
                            strategy_id=active_strategy.id, symbol=symbol,
                            timeframe=timeframe, action=signal.action,
                            block_reason="dedup",
                            confluence_score=signal.confluence_score,
                            regime=signal.regime,
                        ))
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

                    # NULL ai_recommendation means no AI gate ran — reject (no trading without AI)
                    if signal_row.ai_recommendation is None:
                        signal_row.ai_recommendation = "reject"
                        signal_row.ai_reasoning = (
                            "AI signal quality evaluation did not run — "
                            "signal rejected per no-trading-without-AI policy."
                        )
                        signal_row.ai_quality_score = 0
                        logger.warning(
                            "AI gate missing for %s %s %s — rejecting signal "
                            "(ai_signal_quality_enabled=%s, ai_multi_timeframe_enabled=%s)",
                            signal.action, symbol, timeframe,
                            settings.ai_signal_quality_enabled,
                            settings.ai_multi_timeframe_enabled,
                        )

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
                        log_entries.append(PipelineLog(
                            strategy_id=active_strategy.id, symbol=symbol,
                            timeframe=timeframe, action=signal.action,
                            block_reason="ai_reject",
                            confluence_score=signal.confluence_score,
                            regime=signal.regime,
                        ))
                        continue

                    # Signal passed all gates — log as passed
                    log_entries.append(PipelineLog(
                        strategy_id=active_strategy.id, symbol=symbol,
                        timeframe=timeframe, action=signal.action,
                        block_reason=None,
                        confluence_score=signal.confluence_score,
                        regime=signal.regime,
                    ))

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
                log_entries.append(PipelineLog(
                    strategy_id=active_strategy.id, symbol=symbol,
                    timeframe=timeframe, action="NO_TRADE",
                    block_reason="error",
                ))

    # Bulk-insert pipeline decision logs
    if log_entries:
        db.add_all(log_entries)


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

            # MTF reject is a hard block — enforce directly (CLAUDE.md core principle)
            if mtf_data.get("recommendation") == "reject":
                signal_row.ai_recommendation = "reject"
                signal_row.ai_reasoning = (
                    f"MTF analysis rejected: {mtf_data.get('reasoning', 'no higher-timeframe alignment')}"
                )
                signal_row.ai_quality_score = 0
                return

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
