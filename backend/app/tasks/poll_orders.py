"""Poll broker for order status updates."""

import logging

from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="poll_order_status", bind=True, max_retries=3)
def poll_order_status(self):
    """Query open orders, poll broker for status, update DB."""
    import asyncio

    import redis

    from app.config import settings

    r = redis.from_url(settings.redis_url)
    lock = r.lock("signalforge:lock:poll_orders", timeout=60, blocking=False)
    if not lock.acquire(blocking=False):
        logger.info("poll_order_status already running, skipping")
        r.close()
        return
    try:
        asyncio.run(_poll_async())
    except (ConnectionError, OSError, TimeoutError) as exc:
        logger.warning("poll_order_status transient error: %s — retrying", exc)
        self.retry(exc=exc, countdown=15)
    finally:
        try:
            lock.release()
        except Exception:
            pass
        r.close()


async def _poll_async():
    from sqlalchemy import select

    from app.core.database import task_session
    from app.execution.position_manager import PositionManagerDB
    from app.models.order import Order
    from app.models.position import Position
    from app.models.signal import Signal

    async with task_session() as db:
        # Find orders in non-terminal states
        result = await db.execute(
            select(Order).where(Order.status.in_(["pending", "submitted", "partial"]))
        )
        orders = result.scalars().all()

        for order in orders:
            try:
                # For paper orders, they are instantly filled — mark as complete
                if order.broker == "paper" and order.status == "pending":
                    order.status = "filled"
                    order.filled_quantity = order.quantity

                # If order is filled and no position exists yet, open one
                if order.status == "filled" and order.filled_quantity > 0:
                    # Guard: skip if a position already exists for this order
                    existing = await db.execute(
                        select(Position.id).where(Position.order_id == order.id).limit(1)
                    )
                    if existing.scalar_one_or_none():
                        order.status = "completed"
                        continue

                    # Resolve strategy_id from the signal linked to this order
                    strategy_id = None
                    if order.signal_id:
                        sig_result = await db.execute(
                            select(Signal.strategy_id).where(Signal.id == order.signal_id)
                        )
                        strategy_id = sig_result.scalar_one_or_none()

                    pos = await PositionManagerDB.open_position(
                        db=db,
                        user_id=str(order.user_id),
                        symbol=order.symbol,
                        direction=order.direction,
                        quantity=order.filled_quantity,
                        entry_price=order.average_fill_price or order.price or 0.0,
                        stop_loss=order.stop_loss,
                        take_profit=order.take_profit,
                        broker=order.broker,
                        order_id=str(order.id),
                        strategy_id=str(strategy_id) if strategy_id else None,
                    )
                    order.status = "completed"
                    logger.info(
                        "Opened position %s from filled order %s "
                        "(SL=%.2f, TP=%.2f — bracket active)",
                        pos.id, order.id,
                        order.stop_loss or 0.0, order.take_profit or 0.0,
                    )

            except Exception as e:
                logger.error("Poll failed for order %s: %s", order.id, e)

        await db.commit()
