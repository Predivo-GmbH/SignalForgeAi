"""Check correlation between open position symbols and generate alerts."""

import logging

from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="check_correlations", bind=True, max_retries=3)
def check_correlations(self):
    """For each user with 2+ open positions, compute correlation matrix."""
    import asyncio

    try:
        asyncio.run(_check_correlations_async())
    except (ConnectionError, OSError, TimeoutError) as exc:
        logger.warning("check_correlations transient error: %s — retrying", exc)
        self.retry(exc=exc, countdown=60)


async def _check_correlations_async():
    from sqlalchemy import func, select

    from app.core.database import task_session
    from app.execution.correlation_monitor import CorrelationMonitor
    from app.models.position import Position
    from app.models.strategy import Strategy

    async with task_session() as db:
        # Find users with 2+ open positions
        result = await db.execute(
            select(Position.user_id, func.count(Position.id))
            .where(Position.is_open == True)  # noqa: E712
            .group_by(Position.user_id)
        )
        user_counts = result.fetchall()

        for user_id, count in user_counts:
            if count < 2:
                continue

            try:
                # Get open positions for this user
                pos_result = await db.execute(
                    select(Position).where(
                        Position.user_id == user_id,
                        Position.is_open == True,  # noqa: E712
                    )
                )
                positions = pos_result.scalars().all()

                # Check if any strategy has correlation monitoring enabled
                strategy_ids = {p.strategy_id for p in positions if p.strategy_id}
                monitor_enabled = False
                threshold = 0.7

                if strategy_ids:
                    strat_result = await db.execute(
                        select(Strategy).where(Strategy.id.in_(strategy_ids))
                    )
                    for strat in strat_result.scalars().all():
                        cfg = strat.config or {}
                        if cfg.get("correlation_monitor_enabled", False):
                            monitor_enabled = True
                            threshold = cfg.get("correlation_threshold", 0.7)
                            break

                if not monitor_enabled:
                    continue

                # Get unique symbols
                symbols = list({p.symbol for p in positions})
                if len(symbols) < 2:
                    continue

                monitor = CorrelationMonitor(
                    threshold_warning=threshold,
                    threshold_critical=min(threshold + 0.15, 0.95),
                )
                corr_result = await monitor.compute(db, symbols)

                # Store result in Redis
                await monitor.store_result(str(user_id), corr_result)

                if corr_result.alerts:
                    logger.warning(
                        "Correlation alerts for user %s: %d alerts, "
                        "max_corr=%.2f, penalty=%.2f",
                        user_id, len(corr_result.alerts),
                        corr_result.max_correlation,
                        corr_result.exposure_penalty,
                    )
                else:
                    logger.debug(
                        "Correlations OK for user %s: max=%.2f",
                        user_id, corr_result.max_correlation,
                    )

            except Exception as e:
                logger.error(
                    "Correlation check failed for user %s: %s", user_id, e
                )
