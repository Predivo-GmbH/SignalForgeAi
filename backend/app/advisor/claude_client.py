"""Centralized Claude AI client with model tiers, caching, and fallback."""

import asyncio
import hashlib
import json
import logging
import re
import time
import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

# Regex to strip markdown code fences (```json ... ``` or ``` ... ```)
_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)


def _extract_json(raw: str) -> dict:
    """Parse JSON from raw text, stripping markdown code fences if present."""
    text = raw.strip()
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try extracting from code fences
    m = _CODE_FENCE_RE.search(text)
    if m:
        return json.loads(m.group(1).strip())
    # Try finding the first { ... } block
    start = text.find("{")
    if start >= 0:
        return json.loads(text[start:])
    raise json.JSONDecodeError("No JSON found in response", text, 0)


class ModelTier(str, Enum):
    """Model tier selection for different use cases."""

    FAST = "fast"  # Haiku — high-frequency, low-latency
    DEEP = "deep"  # Sonnet — periodic deep analysis
    EXPERT = "expert"  # Opus — reserved for future complex reasoning


# Centralized model mapping — upgrade any tier by changing one line
MODEL_MAP: dict[ModelTier, str] = {
    ModelTier.FAST: "claude-haiku-4-5-20251001",
    ModelTier.DEEP: "claude-sonnet-4-6",
    ModelTier.EXPERT: "claude-opus-4-6",
}

# Default max tokens per tier
TOKEN_LIMITS: dict[ModelTier, int] = {
    ModelTier.FAST: 1024,
    ModelTier.DEEP: 4096,
    ModelTier.EXPERT: 8192,
}


class ClaudeClient:
    """Async-compatible Claude client with response caching and metrics."""

    def __init__(self) -> None:
        self._client: Any = None
        self._async_client: Any = None
        self._cache: dict[str, tuple[float, Any]] = {}
        self._default_cache_ttl = 300  # 5 minutes

    @property
    def available(self) -> bool:
        """Return True if an Anthropic API key is configured."""
        return bool(settings.anthropic_api_key)

    def _get_sync_client(self) -> Any:
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        return self._client

    def _get_async_client(self) -> Any:
        if self._async_client is None:
            import anthropic

            self._async_client = anthropic.AsyncAnthropic(
                api_key=settings.anthropic_api_key,
            )
        return self._async_client

    @staticmethod
    def _cache_key(tier: ModelTier, system: str, user_msg: str) -> str:
        content = f"{tier.value}:{system}:{user_msg}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _get_cached(self, key: str, ttl: int) -> dict | None:
        """Return cached result if not expired, else None."""
        if key in self._cache:
            cached_time, cached_result = self._cache[key]
            if time.time() - cached_time < ttl:
                logger.debug("Claude cache hit")
                return cached_result
            del self._cache[key]
        return None

    _MAX_CACHE_SIZE = 256  # Maximum number of entries in the response cache

    def _set_cached(self, key: str, result: dict) -> None:
        self._cache[key] = (time.time(), result)
        # Prune cache if it exceeds max size — keep most recent entries
        if len(self._cache) > self._MAX_CACHE_SIZE:
            sorted_keys = sorted(
                self._cache.keys(),
                key=lambda k: self._cache[k][0],  # sort by timestamp
            )
            for old_key in sorted_keys[: len(sorted_keys) - 128]:
                del self._cache[old_key]

    # ------------------------------------------------------------------
    # Daily call limit via Redis
    # ------------------------------------------------------------------

    def _check_daily_limit_sync(self) -> bool:
        """Check and increment daily call counter (sync). Returns True if OK."""
        try:
            import redis

            r = redis.from_url(settings.redis_url)
            try:
                # Credit hard stop — check Redis value first, then config fallback
                prepaid = float(r.get("ai_prepaid_credit") or 0)
                if prepaid <= 0:
                    prepaid = settings.ai_prepaid_credit_usd
                if prepaid > 0:
                    cumulative = float(r.get("ai_cumulative_cost") or 0)
                    if cumulative >= prepaid:
                        logger.warning(
                            "AI prepaid credit exhausted ($%.4f / $%.2f)",
                            cumulative, prepaid,
                        )
                        return False

                key = f"ai_calls:{datetime.now(UTC).strftime('%Y-%m-%d')}"
                count = r.incr(key)
                if count == 1:
                    r.expire(key, 86400)
                if count > settings.ai_max_daily_api_calls:
                    logger.warning(
                        "Daily AI API call limit reached (%d/%d)",
                        count, settings.ai_max_daily_api_calls,
                    )
                    return False
            finally:
                r.close()
        except Exception:
            logger.warning("Redis unavailable for daily limit check, allowing call", exc_info=True)
        return True

    async def _check_daily_limit_async(self) -> bool:
        """Check and increment daily call counter (async). Returns True if OK."""
        try:
            from app.core.redis_client import redis_client as aredis

            # Credit hard stop — check Redis value first, then config fallback
            prepaid = float(await aredis.get("ai_prepaid_credit") or 0)
            if prepaid <= 0:
                prepaid = settings.ai_prepaid_credit_usd
            if prepaid > 0:
                cumulative = float(await aredis.get("ai_cumulative_cost") or 0)
                if cumulative >= prepaid:
                    logger.warning(
                        "AI prepaid credit exhausted ($%.4f / $%.2f)",
                        cumulative, prepaid,
                    )
                    return False

            key = f"ai_calls:{datetime.now(UTC).strftime('%Y-%m-%d')}"
            count = await aredis.incr(key)
            if count == 1:
                await aredis.expire(key, 86400)
            if count > settings.ai_max_daily_api_calls:
                logger.warning(
                    "Daily AI API call limit reached (%d/%d)",
                    count, settings.ai_max_daily_api_calls,
                )
                return False
        except Exception:
            logger.warning(
                "Redis unavailable for async daily limit check, allowing call",
                exc_info=True,
            )
        return True

    # ------------------------------------------------------------------
    # Usage recording
    # ------------------------------------------------------------------

    async def _record_usage_async(
        self,
        *,
        insight_type: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        cost_usd: float,
    ) -> None:
        """Fire-and-forget insert into ai_insights table (async path)."""
        try:
            from app.core.database import async_session
            from app.models.ai_insight import AIInsight

            async with async_session() as session:
                row = AIInsight(
                    id=uuid.uuid4(),
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                    insight_type=insight_type,
                    model_used=model,
                    result_json={},
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    latency_ms=latency_ms,
                    cost_usd=cost_usd,
                )
                session.add(row)
                await session.commit()
        except Exception:
            logger.warning("Failed to record AI usage (async)", exc_info=True)

        # Increment cumulative cost in Redis for credit hard stop
        try:
            from app.core.redis_client import redis_client as aredis

            await aredis.incrbyfloat("ai_cumulative_cost", cost_usd)
            # Ensure key expires after 30 days so it resets naturally
            ttl = await aredis.ttl("ai_cumulative_cost")
            if ttl == -1:  # no expiry set
                await aredis.expire("ai_cumulative_cost", 30 * 86400)
        except Exception:
            logger.warning("Failed to increment cumulative cost (async)", exc_info=True)

    def _record_usage_sync(
        self,
        *,
        insight_type: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        cost_usd: float,
    ) -> None:
        """Push usage data to Redis queue for later flush (sync path)."""
        try:
            import redis as sync_redis

            r = sync_redis.from_url(settings.redis_url)
            try:
                payload = json.dumps({
                    "insight_type": insight_type,
                    "model_used": model,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "latency_ms": latency_ms,
                    "cost_usd": cost_usd,
                    "created_at": datetime.now(UTC).isoformat(),
                })
                r.rpush("ai_usage_queue", payload)

                # Increment cumulative cost for credit hard stop
                r.incrbyfloat("ai_cumulative_cost", cost_usd)
                # Ensure key expires after 30 days so it resets naturally
                if r.ttl("ai_cumulative_cost") == -1:
                    r.expire("ai_cumulative_cost", 30 * 86400)
            finally:
                r.close()
        except Exception:
            logger.warning("Failed to queue AI usage (sync)", exc_info=True)

    # ------------------------------------------------------------------
    # Main API methods
    # ------------------------------------------------------------------

    async def ask_json(
        self,
        tier: ModelTier,
        system_prompt: str,
        user_message: str,
        *,
        max_tokens: int | None = None,
        cache_ttl: int | None = None,
        insight_type: str = "unknown",
    ) -> dict | None:
        """Send a message to Claude and parse JSON response (async).

        Returns None if API key missing or call fails. Callers must
        abort the operation or reject the signal — the system does
        not trade or make decisions without AI analysis.
        """
        if not self.available:
            return None

        if not await self._check_daily_limit_async():
            return None

        ttl = cache_ttl if cache_ttl is not None else self._default_cache_ttl
        if ttl > 0:
            key = self._cache_key(tier, system_prompt, user_message)
            cached = self._get_cached(key, ttl)
            if cached is not None:
                return cached

        try:
            model = MODEL_MAP[tier]
            client = self._get_async_client()
            t0 = time.monotonic()
            message = await client.messages.create(
                model=model,
                max_tokens=max_tokens or TOKEN_LIMITS[tier],
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            latency_ms = int((time.monotonic() - t0) * 1000)

            raw = message.content[0].text
            result = _extract_json(raw)

            if ttl > 0:
                key = self._cache_key(tier, system_prompt, user_message)
                self._set_cached(key, result)

            # Fire-and-forget usage recording
            from app.advisor.pricing import compute_cost

            in_tok = getattr(message.usage, "input_tokens", 0)
            out_tok = getattr(message.usage, "output_tokens", 0)
            cost = compute_cost(model, in_tok, out_tok)
            asyncio.create_task(self._record_usage_async(
                insight_type=insight_type,
                model=model,
                input_tokens=in_tok,
                output_tokens=out_tok,
                latency_ms=latency_ms,
                cost_usd=cost,
            ))

            return result
        except Exception:
            logger.exception("Claude async API call failed (tier=%s)", tier.value)
            return None

    def ask_json_sync(
        self,
        tier: ModelTier,
        system_prompt: str,
        user_message: str,
        *,
        max_tokens: int | None = None,
        cache_ttl: int | None = None,
        insight_type: str = "unknown",
    ) -> dict | None:
        """Send a message to Claude and parse JSON response (sync).

        For use in Celery tasks and other synchronous contexts.
        Returns None if API key missing or call fails.
        """
        if not self.available:
            return None

        if not self._check_daily_limit_sync():
            return None

        ttl = cache_ttl if cache_ttl is not None else self._default_cache_ttl
        if ttl > 0:
            key = self._cache_key(tier, system_prompt, user_message)
            cached = self._get_cached(key, ttl)
            if cached is not None:
                return cached

        try:
            model = MODEL_MAP[tier]
            client = self._get_sync_client()
            t0 = time.monotonic()
            message = client.messages.create(
                model=model,
                max_tokens=max_tokens or TOKEN_LIMITS[tier],
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            latency_ms = int((time.monotonic() - t0) * 1000)

            raw = message.content[0].text
            result = _extract_json(raw)

            if ttl > 0:
                key = self._cache_key(tier, system_prompt, user_message)
                self._set_cached(key, result)

            # Queue usage recording for Celery flush
            from app.advisor.pricing import compute_cost

            in_tok = getattr(message.usage, "input_tokens", 0)
            out_tok = getattr(message.usage, "output_tokens", 0)
            cost = compute_cost(model, in_tok, out_tok)
            self._record_usage_sync(
                insight_type=insight_type,
                model=model,
                input_tokens=in_tok,
                output_tokens=out_tok,
                latency_ms=latency_ms,
                cost_usd=cost,
            )

            return result
        except Exception:
            logger.exception("Claude sync API call failed (tier=%s)", tier.value)
            return None


# Singleton instance
claude_client = ClaudeClient()
