"""Celery task to flush AI usage records from Redis queue to database."""

import asyncio
import json
import logging
import uuid
from datetime import datetime

from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="flush_ai_usage")
def flush_ai_usage() -> dict:
    """Pop all items from ai_usage_queue and bulk-insert into ai_insights."""
    return asyncio.run(_flush_async())


async def _flush_async() -> dict:
    import redis as sync_redis

    from app.config import settings

    r = sync_redis.from_url(settings.redis_url)
    items: list[dict] = []
    while True:
        raw = r.lpop("ai_usage_queue")
        if raw is None:
            break
        try:
            items.append(json.loads(raw))
        except json.JSONDecodeError:
            logger.warning("Skipping malformed AI usage record")

    if not items:
        return {"flushed": 0}

    from app.core.database import task_session
    from app.models.ai_insight import AIInsight

    async with task_session() as session:
        for item in items:
            created_at = datetime.fromisoformat(item["created_at"])
            row = AIInsight(
                id=uuid.uuid4(),
                created_at=created_at,
                updated_at=created_at,
                insight_type=item.get("insight_type", "unknown"),
                model_used=item.get("model_used", "unknown"),
                result_json={},
                input_tokens=item.get("input_tokens"),
                output_tokens=item.get("output_tokens"),
                latency_ms=item.get("latency_ms"),
                cost_usd=item.get("cost_usd"),
            )
            session.add(row)
        await session.commit()

    logger.info("Flushed %d AI usage records to database", len(items))
    return {"flushed": len(items)}
