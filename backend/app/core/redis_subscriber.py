"""Redis subscriber -- listens to signalforge:* channels and broadcasts to WebSocket clients."""

import asyncio
import json
import logging

logger = logging.getLogger(__name__)


class RedisSubscriber:
    """Background task that subscribes to Redis channels and broadcasts to WS."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self._redis_url = redis_url
        self._running = False
        self._task: asyncio.Task | None = None
        self._broadcast_fn = None

    async def start(self, broadcast_fn):
        """Start the subscriber as a background asyncio task."""
        self._running = True
        self._broadcast_fn = broadcast_fn
        self._task = asyncio.create_task(self._listen())
        logger.info("Redis subscriber started")

    async def stop(self):
        """Stop the subscriber."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Redis subscriber stopped")

    async def _listen(self):
        """Subscribe to signalforge:* Redis channels and route messages."""
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(self._redis_url)
            pubsub = r.pubsub()
            await pubsub.psubscribe("signalforge:*")

            async for message in pubsub.listen():
                if not self._running:
                    break
                if message["type"] == "pmessage":
                    channel = message["channel"]
                    if isinstance(channel, bytes):
                        channel = channel.decode()
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode()

                    try:
                        parsed = json.loads(data)
                    except json.JSONDecodeError:
                        parsed = {"raw": data}

                    # Route to appropriate WS channel
                    if "signals" in channel:
                        await self._broadcast_fn("signals", parsed)
                    elif "prices" in channel:
                        await self._broadcast_fn("prices", parsed)
                    elif "trades" in channel:
                        await self._broadcast_fn("trades", parsed)

            await pubsub.unsubscribe()
            await r.aclose()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Redis subscriber error: %s", e)
