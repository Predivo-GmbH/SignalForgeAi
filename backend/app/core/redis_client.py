"""Redis async client for SignalForgeAI."""

import redis.asyncio as aioredis

from app.config import settings

redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)


async def get_redis():
    """Dependency that returns the shared Redis client."""
    return redis_client
