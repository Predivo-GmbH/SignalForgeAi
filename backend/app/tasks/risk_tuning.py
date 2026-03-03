"""Periodic adaptive risk tuning task."""

import asyncio
import logging

from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="adaptive_risk_tuning", bind=True, max_retries=1)
def adaptive_risk_tuning(self, strategy_id: str | None = None):
    """Tune risk parameters using Claude analysis."""
    import redis

    from app.config import settings

    r = None
    lock = None
    try:
        r = redis.from_url(settings.redis_url)
        lock = r.lock("signalforge:lock:risk_tuning", timeout=600, blocking=False)
        if not lock.acquire(blocking=False):
            logger.info("adaptive_risk_tuning already running, skipping")
            r.close()
            return
    except redis.ConnectionError:
        logger.warning("Redis unavailable for risk_tuning lock — proceeding without lock")

    try:
        asyncio.run(_tune_risk_async(strategy_id))
    except (ConnectionError, OSError, TimeoutError) as exc:
        logger.warning("adaptive_risk_tuning transient error: %s — retrying", exc)
        self.retry(exc=exc, countdown=120)
    finally:
        if lock is not None:
            try:
                lock.release()
            except redis.exceptions.LockNotOwnedError:
                logger.warning("adaptive_risk_tuning lock expired before release")
            except Exception:
                pass
        if r is not None:
            r.close()


async def _tune_risk_async(strategy_id: str | None):
    from sqlalchemy import select

    from app.advisor.risk_tuner import RiskTuner
    from app.config import settings
    from app.core.database import task_session
    from app.models.strategy import Strategy

    if not settings.ai_risk_tuning_enabled:
        logger.info("AI risk tuning is disabled via feature flag")
        return

    async with task_session() as db:
        if strategy_id:
            result = await db.execute(
                select(Strategy).where(Strategy.id == strategy_id)
            )
            strategies = [result.scalar_one_or_none()]
            strategies = [s for s in strategies if s is not None]
        else:
            result = await db.execute(
                select(Strategy).where(Strategy.is_active == True)  # noqa: E712
            )
            strategies = list(result.scalars().all())

        if not strategies:
            logger.info("No strategies to tune")
            return

        tuner = RiskTuner()
        for strategy in strategies:
            try:
                result = await tuner.tune(strategy, db)
                adjustments = result.get("adjustments", {})

                if adjustments:
                    cfg = dict(strategy.config or {})
                    cfg.update(adjustments)
                    strategy.config = cfg
                    logger.info(
                        "Risk tuning applied for strategy '%s': %s — %s",
                        strategy.name, adjustments, result.get("reasoning", ""),
                    )
                else:
                    logger.info(
                        "Risk tuning: no changes for strategy '%s' — %s",
                        strategy.name, result.get("reasoning", ""),
                    )
            except Exception:
                logger.exception("Risk tuning failed for strategy '%s'", strategy.name)

        await db.commit()
