"""Periodic feedback rule synthesis task."""

import asyncio
import logging

from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="synthesize_feedback_rules", bind=True, max_retries=1)
def synthesize_feedback_rules(self, strategy_id: str | None = None):
    """Synthesize feedback rules from trade history."""
    import redis

    from app.config import settings

    r = None
    lock = None
    try:
        r = redis.from_url(settings.redis_url)
        lock = r.lock("signalforge:lock:feedback_synthesis", timeout=600, blocking=False)
        if not lock.acquire(blocking=False):
            logger.info("synthesize_feedback_rules already running, skipping")
            r.close()
            return
    except redis.ConnectionError:
        logger.warning("Redis unavailable for feedback_synthesis lock — proceeding without lock")

    try:
        asyncio.run(_synthesize_async(strategy_id))
    except (ConnectionError, OSError, TimeoutError) as exc:
        logger.warning("feedback_synthesis transient error: %s — retrying", exc)
        self.retry(exc=exc, countdown=120)
    finally:
        if lock is not None:
            try:
                lock.release()
            except redis.exceptions.LockNotOwnedError:
                logger.warning("synthesize_feedback_rules lock expired before release")
            except Exception:
                pass
        if r is not None:
            r.close()


async def _synthesize_async(strategy_id: str | None):
    from sqlalchemy import select

    from app.advisor.feedback_synthesizer import FeedbackSynthesizer
    from app.config import settings
    from app.core.database import task_session
    from app.models.strategy import Strategy

    if not settings.ai_feedback_loop_enabled:
        logger.info("AI feedback loop is disabled via feature flag")
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
            logger.info("No strategies for feedback synthesis")
            return

        synthesizer = FeedbackSynthesizer()
        for strategy in strategies:
            try:
                new_rules = await synthesizer.synthesize(
                    str(strategy.id), str(strategy.user_id), db,
                )
                if new_rules:
                    logger.info(
                        "Feedback synthesis: %d new rules for strategy '%s'",
                        len(new_rules), strategy.name,
                    )
                else:
                    logger.info(
                        "Feedback synthesis: no new rules for strategy '%s'",
                        strategy.name,
                    )
            except Exception:
                logger.exception(
                    "Feedback synthesis failed for strategy '%s'", strategy.name,
                )

        await db.commit()
