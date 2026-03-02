"""Execute pending signals — place orders via BrokerRouter.

Applies risk management checks before execution:
  - Drawdown circuit breaker (Feature 2): skip/reduce at high drawdown
  - Correlation penalty (Feature 8): reduce sizing for correlated positions
"""

import logging

from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="execute_pending_signals", bind=True, max_retries=3)
def execute_pending_signals(self):
    """Query signals pending execution, run risk checks, place orders."""
    import asyncio

    asyncio.run(_execute_async())


async def _execute_async():
    from sqlalchemy import select

    from app.core.database import task_session
    from app.execution.adapters.paper import PaperAdapter
    from app.execution.broker_router import BrokerRouter
    from app.execution.executor import OrderExecutor
    from app.models.signal import Signal
    from app.models.strategy import Strategy

    # Default to paper adapter
    paper = PaperAdapter()
    router = BrokerRouter(paper_adapter=paper)
    executor = OrderExecutor(broker_router=router)

    async with task_session() as db:
        # Query actionable signals with status "pending" that have a strategy
        # (we need strategy.user_id to create the order)
        result = await db.execute(
            select(Signal)
            .where(
                Signal.direction.in_(["BUY", "SELL"]),
                Signal.status == "pending",
                Signal.strategy_id.isnot(None),
            )
            .order_by(Signal.created_at.desc())
            .limit(10)
        )
        signals = result.scalars().all()

        for sig in signals:
            try:
                # Resolve user_id from the linked strategy
                strat_result = await db.execute(
                    select(Strategy).where(Strategy.id == sig.strategy_id)
                )
                strategy = strat_result.scalar_one_or_none()
                if strategy is None:
                    logger.warning("Signal %s has no valid strategy, skipping", sig.id)
                    continue

                cfg = strategy.config or {}
                user_id = str(strategy.user_id)
                has_size = sig.position_size and sig.position_size > 0
                quantity = sig.position_size if has_size else 0.01

                # --- Drawdown circuit breaker check (Feature 2) ---
                if cfg.get("drawdown_breaker_enabled", False):
                    try:
                        from app.execution.drawdown_breaker import DrawdownBreaker

                        breaker = DrawdownBreaker(
                            max_drawdown_pct=cfg.get("max_drawdown_pct", 0.15)
                        )
                        multiplier = await breaker.get_sizing_multiplier(user_id)
                        if multiplier <= 0:
                            logger.warning(
                                "Drawdown breaker HALT: skipping signal %s for user %s",
                                sig.id, user_id,
                            )
                            sig.status = "rejected"
                            continue
                        if multiplier < 1.0:
                            old_qty = quantity
                            quantity *= multiplier
                            logger.info(
                                "Drawdown breaker: reduced quantity %.6f -> %.6f "
                                "for signal %s (multiplier=%.2f)",
                                old_qty, quantity, sig.id, multiplier,
                            )
                    except Exception as e:
                        logger.warning("Drawdown breaker check failed: %s", e)

                # --- Correlation penalty check (Feature 8) ---
                if cfg.get("correlation_auto_reduce", False):
                    try:
                        from app.execution.correlation_monitor import CorrelationMonitor

                        monitor = CorrelationMonitor()
                        penalty = await monitor.get_cached_penalty(user_id)
                        if penalty < 1.0:
                            old_qty = quantity
                            quantity *= penalty
                            logger.info(
                                "Correlation penalty: reduced quantity %.6f -> %.6f "
                                "for signal %s (penalty=%.2f)",
                                old_qty, quantity, sig.id, penalty,
                            )
                    except Exception as e:
                        logger.warning("Correlation penalty check failed: %s", e)

                # Skip if quantity reduced to effectively zero
                if quantity <= 0:
                    logger.warning(
                        "Quantity reduced to zero for signal %s, skipping", sig.id
                    )
                    sig.status = "rejected"
                    continue

                signal_dict = {
                    "signal_id": str(sig.id),
                    "symbol": sig.symbol,
                    "direction": sig.direction,
                    "quantity": quantity,
                    "price": sig.entry_price,
                    "order_type": "market",
                    "stop_loss": sig.stop_loss,
                    "take_profit": sig.take_profit_1,
                }
                order = await executor.execute_signal(
                    db, user_id, signal_dict
                )

                # Mark signal as active after successful execution
                sig.status = "active"

                logger.info(
                    "Executed signal %s -> order %s status=%s",
                    sig.id,
                    order.id,
                    order.status,
                )
            except Exception as e:
                logger.error("Failed to execute signal %s: %s", sig.id, e)

        await db.commit()
