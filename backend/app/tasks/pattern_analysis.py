"""Periodic pattern analysis — feeds insights into the self-learning loop."""

import asyncio
import json
import logging

from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="periodic_pattern_analysis", bind=True, max_retries=1)
def periodic_pattern_analysis(self):
    """Run deep pattern analysis and store results for the Risk Tuner."""
    asyncio.run(_analyze_async())


async def _analyze_async():
    from sqlalchemy import select

    from app.advisor.pattern_analyzer import PatternAnalyzer
    from app.config import settings
    from app.core.database import task_session
    from app.core.redis_client import redis_client
    from app.models.strategy import Strategy

    if not settings.ai_pattern_analysis_enabled:
        logger.info("AI pattern analysis is disabled via feature flag")
        return

    async with task_session() as db:
        result = await db.execute(
            select(Strategy).where(Strategy.is_active == True)  # noqa: E712
        )
        strategies = list(result.scalars().all())

        if not strategies:
            logger.info("No active strategies for pattern analysis")
            return

        analyzer = PatternAnalyzer()
        for strategy in strategies:
            try:
                analysis = await analyzer.analyze_deep(
                    str(strategy.user_id), db,
                )

                key = f"pattern_analysis:{strategy.id}"
                await redis_client.set(key, json.dumps(analysis), ex=172800)  # 48h TTL
                logger.info(
                    "Pattern analysis stored for strategy '%s': %d patterns, %d recs",
                    strategy.name,
                    len(analysis.get("patterns", [])),
                    len(analysis.get("recommendations", [])),
                )
            except Exception:
                logger.exception(
                    "Pattern analysis failed for strategy '%s'", strategy.name,
                )
