"""Manage open positions — update prices, trail stops, check SL/TP."""

import logging

from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="manage_positions", bind=True, max_retries=3)
def manage_positions(self):
    """Trail stops, check SL/TP, close positions as needed."""
    import asyncio

    asyncio.run(_manage_async())


async def _manage_async():
    from sqlalchemy import select

    from app.core.database import task_session
    from app.execution.position_manager import PositionManagerDB
    from app.models.candle import Candle
    from app.models.position import Position

    async with task_session() as db:
        result = await db.execute(
            select(Position).where(Position.is_open == True)  # noqa: E712
        )
        positions = result.scalars().all()

        for pos in positions:
            try:
                # Update current_price from latest candle
                candle_result = await db.execute(
                    select(Candle)
                    .where(Candle.symbol == pos.symbol)
                    .order_by(Candle.time.desc())
                    .limit(1)
                )
                latest_candle = candle_result.scalar_one_or_none()
                if latest_candle:
                    pos.current_price = latest_candle.close
                    # Update unrealized PnL
                    if pos.direction == "BUY":
                        pos.unrealized_pnl = (latest_candle.close - pos.entry_price) * pos.quantity
                    else:
                        pos.unrealized_pnl = (pos.entry_price - latest_candle.close) * pos.quantity

                # Check stop-loss hit
                if pos.stop_loss and pos.current_price:
                    if pos.direction == "BUY" and pos.current_price <= pos.stop_loss:
                        await PositionManagerDB.close_position(
                            db, str(pos.id), pos.current_price, "stop_loss"
                        )
                        logger.info("Stop-loss hit for position %s", pos.id)
                        continue
                    if pos.direction == "SELL" and pos.current_price >= pos.stop_loss:
                        await PositionManagerDB.close_position(
                            db, str(pos.id), pos.current_price, "stop_loss"
                        )
                        logger.info("Stop-loss hit for position %s", pos.id)
                        continue

                # Check take-profit hit
                if pos.take_profit and pos.current_price:
                    if pos.direction == "BUY" and pos.current_price >= pos.take_profit:
                        await PositionManagerDB.close_position(
                            db, str(pos.id), pos.current_price, "take_profit"
                        )
                        logger.info("Take-profit hit for position %s", pos.id)
                        continue
                    if pos.direction == "SELL" and pos.current_price <= pos.take_profit:
                        await PositionManagerDB.close_position(
                            db, str(pos.id), pos.current_price, "take_profit"
                        )
                        logger.info("Take-profit hit for position %s", pos.id)
                        continue

            except Exception as e:
                logger.error("Position management failed for %s: %s", pos.id, e)

        await db.commit()
