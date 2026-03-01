"""Execute pending signals — place orders via BrokerRouter."""

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

                signal_dict = {
                    "signal_id": str(sig.id),
                    "symbol": sig.symbol,
                    "direction": sig.direction,
                    "quantity": 0.01,  # Default quantity; no position_size on Signal
                    "price": sig.entry_price,
                    "order_type": "market",
                    "stop_loss": sig.stop_loss,
                    "take_profit": sig.take_profit_1,
                }
                order = await executor.execute_signal(
                    db, str(strategy.user_id), signal_dict
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
