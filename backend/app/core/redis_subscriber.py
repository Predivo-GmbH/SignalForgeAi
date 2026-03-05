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
        import redis.asyncio as aioredis

        backoff = 1
        while self._running:
            try:
                r = aioredis.from_url(self._redis_url)
                pubsub = r.pubsub()
                await pubsub.psubscribe("signalforge:*")
                logger.info("Redis subscriber connected")
                backoff = 1  # Reset on successful connect

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
                        try:
                            if "signals" in channel:
                                await self._broadcast_fn("signals", parsed)
                            elif "prices" in channel:
                                await self._broadcast_fn("prices", parsed)
                            elif "trades" in channel:
                                await self._broadcast_fn("trades", parsed)
                        except Exception as e:
                            logger.exception("Subscriber handler error on %s: %s", channel, e)

                await pubsub.unsubscribe()
                await r.aclose()
            except asyncio.CancelledError:
                break
            except Exception as e:
                if not self._running:
                    break
                logger.warning(
                    "Redis subscriber disconnected: %s — reconnecting in %ds",
                    e, backoff,
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)
