"""Poll broker for order status updates."""

import logging

from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="poll_order_status", bind=True, max_retries=3)
def poll_order_status(self):
    """Query open orders, poll broker for status, update DB."""
    import asyncio

    asyncio.run(_poll_async())


async def _poll_async():
    from sqlalchemy import select

    from app.core.database import task_session
    from app.execution.position_manager import PositionManagerDB
    from app.models.order import Order

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
                    await PositionManagerDB.open_position(
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
                    )
                    logger.info("Opened position from filled order %s", order.id)

            except Exception as e:
                logger.error("Poll failed for order %s: %s", order.id, e)

        await db.commit()
