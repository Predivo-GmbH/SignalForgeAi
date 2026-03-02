"""Periodic feedback rule synthesis task."""

import asyncio
import logging

from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="synthesize_feedback_rules", bind=True, max_retries=1)
def synthesize_feedback_rules(self, strategy_id: str | None = None):
    """Synthesize feedback rules from trade history."""
    asyncio.run(_synthesize_async(strategy_id))


async def _synthesize_async(strategy_id: str | None):
    from sqlalchemy import select

    from app.advisor.feedback_synthesizer import FeedbackSynthesizer
    from app.core.database import task_session
    from app.models.strategy import Strategy

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
