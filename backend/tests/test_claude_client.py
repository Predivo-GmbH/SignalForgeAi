"""Tests for the centralized Claude client."""

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.advisor.claude_client import (
    MODEL_MAP,
    TOKEN_LIMITS,
    ClaudeClient,
    ModelTier,
)


@pytest.fixture
def client_no_key():
    """ClaudeClient with no API key configured."""
    with patch("app.advisor.claude_client.settings") as mock_settings:
        mock_settings.anthropic_api_key = ""
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.ai_max_daily_api_calls = 500
        mock_settings.ai_prepaid_credit_usd = 0.0
        c = ClaudeClient()
        yield c


@pytest.fixture
def client_with_key():
    """ClaudeClient with API key configured."""
    with patch("app.advisor.claude_client.settings") as mock_settings:
        mock_settings.anthropic_api_key = "sk-ant-test-key"
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.ai_max_daily_api_calls = 500
        mock_settings.ai_prepaid_credit_usd = 0.0
        c = ClaudeClient()
        yield c


def _mock_message(content: dict) -> MagicMock:
    """Create a mock Anthropic message response."""
    msg = MagicMock()
    msg.content = [MagicMock(text=json.dumps(content))]
    msg.usage.input_tokens = 100
    msg.usage.output_tokens = 50
    return msg


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------


def test_available_false_without_key(client_no_key):
    assert client_no_key.available is False


def test_available_true_with_key(client_with_key):
    assert client_with_key.available is True


# ---------------------------------------------------------------------------
# Returns None when unavailable
# ---------------------------------------------------------------------------


async def test_ask_json_returns_none_without_key(client_no_key):
    result = await client_no_key.ask_json(
        ModelTier.FAST, "system", "user"
    )
    assert result is None


def test_ask_json_sync_returns_none_without_key(client_no_key):
    result = client_no_key.ask_json_sync(
        ModelTier.FAST, "system", "user"
    )
    assert result is None


# ---------------------------------------------------------------------------
# Model tier selection
# ---------------------------------------------------------------------------


def test_model_map_has_all_tiers():
    for tier in ModelTier:
        assert tier in MODEL_MAP
        assert tier in TOKEN_LIMITS


# ---------------------------------------------------------------------------
# Successful API call (async)
# ---------------------------------------------------------------------------


async def test_ask_json_parses_response(client_with_key):
    expected = {"summary": "test", "score": 42}
    mock_msg = _mock_message(expected)

    mock_async_client = AsyncMock()
    mock_async_client.messages.create = AsyncMock(return_value=mock_msg)

    with patch("anthropic.AsyncAnthropic", return_value=mock_async_client):
        result = await client_with_key.ask_json(
            ModelTier.FAST, "system prompt", "user message", cache_ttl=0
        )

    assert result == expected
    mock_async_client.messages.create.assert_called_once()
    call_kwargs = mock_async_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == MODEL_MAP[ModelTier.FAST]
    assert call_kwargs["system"] == "system prompt"


# ---------------------------------------------------------------------------
# Successful API call (sync)
# ---------------------------------------------------------------------------


def test_ask_json_sync_parses_response(client_with_key):
    expected = {"analysis": "good trade"}
    mock_msg = _mock_message(expected)

    mock_sync_client = MagicMock()
    mock_sync_client.messages.create.return_value = mock_msg

    with patch("anthropic.Anthropic", return_value=mock_sync_client):
        result = client_with_key.ask_json_sync(
            ModelTier.DEEP, "system", "user", cache_ttl=0
        )

    assert result == expected
    call_kwargs = mock_sync_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == MODEL_MAP[ModelTier.DEEP]


# ---------------------------------------------------------------------------
# JSON parse error returns None
# ---------------------------------------------------------------------------


async def test_ask_json_returns_none_on_invalid_json(client_with_key):
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text="not valid json {{{")]

    mock_async_client = AsyncMock()
    mock_async_client.messages.create = AsyncMock(return_value=mock_msg)

    with patch("anthropic.AsyncAnthropic", return_value=mock_async_client):
        result = await client_with_key.ask_json(
            ModelTier.FAST, "system", "user", cache_ttl=0
        )

    assert result is None


# ---------------------------------------------------------------------------
# API exception returns None
# ---------------------------------------------------------------------------


async def test_ask_json_returns_none_on_api_error(client_with_key):
    mock_async_client = AsyncMock()
    mock_async_client.messages.create = AsyncMock(
        side_effect=Exception("API timeout")
    )

    with patch("anthropic.AsyncAnthropic", return_value=mock_async_client):
        result = await client_with_key.ask_json(
            ModelTier.FAST, "system", "user", cache_ttl=0
        )

    assert result is None


# ---------------------------------------------------------------------------
# Cache behavior
# ---------------------------------------------------------------------------


async def test_cache_hit_returns_cached_result(client_with_key):
    expected = {"cached": True}
    mock_msg = _mock_message(expected)

    mock_async_client = AsyncMock()
    mock_async_client.messages.create = AsyncMock(return_value=mock_msg)

    with patch("anthropic.AsyncAnthropic", return_value=mock_async_client):
        # First call — hits API
        result1 = await client_with_key.ask_json(
            ModelTier.FAST, "sys", "usr", cache_ttl=60
        )
        # Second call — should use cache
        result2 = await client_with_key.ask_json(
            ModelTier.FAST, "sys", "usr", cache_ttl=60
        )

    assert result1 == expected
    assert result2 == expected
    # API should only be called once (second call uses cache)
    assert mock_async_client.messages.create.call_count == 1


async def test_cache_expiry_calls_api_again(client_with_key):
    expected = {"cached": True}
    mock_msg = _mock_message(expected)

    mock_async_client = AsyncMock()
    mock_async_client.messages.create = AsyncMock(return_value=mock_msg)

    with patch("anthropic.AsyncAnthropic", return_value=mock_async_client):
        # First call
        await client_with_key.ask_json(
            ModelTier.FAST, "sys", "usr", cache_ttl=1
        )

        # Expire the cache manually
        for key in client_with_key._cache:
            client_with_key._cache[key] = (time.time() - 10, expected)

        # Second call — cache expired, should hit API again
        await client_with_key.ask_json(
            ModelTier.FAST, "sys", "usr", cache_ttl=1
        )

    assert mock_async_client.messages.create.call_count == 2


async def test_cache_disabled_with_zero_ttl(client_with_key):
    expected = {"no_cache": True}
    mock_msg = _mock_message(expected)

    mock_async_client = AsyncMock()
    mock_async_client.messages.create = AsyncMock(return_value=mock_msg)

    with patch("anthropic.AsyncAnthropic", return_value=mock_async_client):
        await client_with_key.ask_json(
            ModelTier.FAST, "sys", "usr", cache_ttl=0
        )
        await client_with_key.ask_json(
            ModelTier.FAST, "sys", "usr", cache_ttl=0
        )

    # Both calls should hit API (no caching)
    assert mock_async_client.messages.create.call_count == 2


# ---------------------------------------------------------------------------
# Custom max_tokens
# ---------------------------------------------------------------------------


async def test_custom_max_tokens(client_with_key):
    mock_msg = _mock_message({"ok": True})
    mock_async_client = AsyncMock()
    mock_async_client.messages.create = AsyncMock(return_value=mock_msg)

    with patch("anthropic.AsyncAnthropic", return_value=mock_async_client):
        await client_with_key.ask_json(
            ModelTier.FAST, "sys", "usr", max_tokens=2000, cache_ttl=0
        )

    call_kwargs = mock_async_client.messages.create.call_args.kwargs
    assert call_kwargs["max_tokens"] == 2000


# ---------------------------------------------------------------------------
# Daily call limit tests
# ---------------------------------------------------------------------------


def test_daily_limit_blocks_when_exceeded_sync():
    """When Redis counter > ai_max_daily_api_calls, ask_json_sync returns None."""
    with patch("app.advisor.claude_client.settings") as mock_settings:
        mock_settings.anthropic_api_key = "sk-ant-test-key"
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.ai_max_daily_api_calls = 100
        mock_settings.ai_prepaid_credit_usd = 0.0
        c = ClaudeClient()

    mock_redis = MagicMock()
    mock_redis.incr.return_value = 101  # Over the 100 limit
    mock_redis.get.return_value = None

    with (
        patch("app.advisor.claude_client.settings") as mock_settings,
        patch("redis.from_url", return_value=mock_redis),
    ):
        mock_settings.anthropic_api_key = "sk-ant-test-key"
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.ai_max_daily_api_calls = 100
        mock_settings.ai_prepaid_credit_usd = 0.0

        result = c.ask_json_sync(ModelTier.FAST, "system", "user", cache_ttl=0)

    assert result is None


async def test_daily_limit_blocks_when_exceeded_async():
    """When async Redis counter > ai_max_daily_api_calls, ask_json returns None."""
    with patch("app.advisor.claude_client.settings") as mock_settings:
        mock_settings.anthropic_api_key = "sk-ant-test-key"
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.ai_max_daily_api_calls = 100
        mock_settings.ai_prepaid_credit_usd = 0.0
        c = ClaudeClient()

    mock_aredis = AsyncMock()
    mock_aredis.incr = AsyncMock(return_value=101)
    mock_aredis.get = AsyncMock(return_value=None)

    with (
        patch("app.advisor.claude_client.settings") as mock_settings,
        patch("app.advisor.claude_client.aredis", mock_aredis, create=True),
        patch(
            "app.core.redis_client.redis_client", mock_aredis
        ),
    ):
        mock_settings.anthropic_api_key = "sk-ant-test-key"
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.ai_max_daily_api_calls = 100
        mock_settings.ai_prepaid_credit_usd = 0.0

        result = await c.ask_json(ModelTier.FAST, "system", "user", cache_ttl=0)

    assert result is None


def test_daily_limit_allows_when_under_limit_sync():
    """When Redis counter is under the daily limit, the call proceeds."""
    with patch("app.advisor.claude_client.settings") as mock_settings:
        mock_settings.anthropic_api_key = "sk-ant-test-key"
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.ai_max_daily_api_calls = 500
        mock_settings.ai_prepaid_credit_usd = 0.0
        c = ClaudeClient()

    expected = {"result": "ok"}
    mock_msg = _mock_message(expected)
    mock_redis = MagicMock()
    mock_redis.incr.return_value = 10  # Well under 500
    mock_redis.get.return_value = None

    mock_sync_client = MagicMock()
    mock_sync_client.messages.create.return_value = mock_msg

    with (
        patch("app.advisor.claude_client.settings") as mock_settings,
        patch("redis.from_url", return_value=mock_redis),
        patch("anthropic.Anthropic", return_value=mock_sync_client),
    ):
        mock_settings.anthropic_api_key = "sk-ant-test-key"
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.ai_max_daily_api_calls = 500
        mock_settings.ai_prepaid_credit_usd = 0.0

        result = c.ask_json_sync(ModelTier.FAST, "system", "user", cache_ttl=0)

    assert result == expected


def test_daily_limit_allows_when_redis_unavailable():
    """If Redis raises an exception, the call is allowed (fail-open)."""
    with patch("app.advisor.claude_client.settings") as mock_settings:
        mock_settings.anthropic_api_key = "sk-ant-test-key"
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.ai_max_daily_api_calls = 500
        mock_settings.ai_prepaid_credit_usd = 0.0
        c = ClaudeClient()

    expected = {"result": "allowed"}
    mock_msg = _mock_message(expected)

    mock_sync_client = MagicMock()
    mock_sync_client.messages.create.return_value = mock_msg

    with (
        patch("app.advisor.claude_client.settings") as mock_settings,
        patch("redis.from_url", side_effect=Exception("Connection refused")),
        patch("anthropic.Anthropic", return_value=mock_sync_client),
    ):
        mock_settings.anthropic_api_key = "sk-ant-test-key"
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.ai_max_daily_api_calls = 500
        mock_settings.ai_prepaid_credit_usd = 0.0

        result = c.ask_json_sync(ModelTier.FAST, "system", "user", cache_ttl=0)

    assert result == expected


# ---------------------------------------------------------------------------
# Credit hard stop tests
# ---------------------------------------------------------------------------


def test_credit_hard_stop_blocks_sync():
    """When cumulative cost >= prepaid credit, ask_json_sync returns None."""
    with patch("app.advisor.claude_client.settings") as mock_settings:
        mock_settings.anthropic_api_key = "sk-ant-test-key"
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.ai_max_daily_api_calls = 500
        mock_settings.ai_prepaid_credit_usd = 5.0
        c = ClaudeClient()

    mock_redis = MagicMock()
    mock_redis.get.return_value = b"5.25"  # Over the $5.00 prepaid

    with (
        patch("app.advisor.claude_client.settings") as mock_settings,
        patch("redis.from_url", return_value=mock_redis),
    ):
        mock_settings.anthropic_api_key = "sk-ant-test-key"
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.ai_max_daily_api_calls = 500
        mock_settings.ai_prepaid_credit_usd = 5.0

        result = c.ask_json_sync(ModelTier.FAST, "system", "user", cache_ttl=0)

    assert result is None


async def test_credit_hard_stop_blocks_async():
    """When cumulative cost >= prepaid credit, ask_json returns None."""
    with patch("app.advisor.claude_client.settings") as mock_settings:
        mock_settings.anthropic_api_key = "sk-ant-test-key"
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.ai_max_daily_api_calls = 500
        mock_settings.ai_prepaid_credit_usd = 5.0
        c = ClaudeClient()

    mock_aredis = AsyncMock()
    mock_aredis.get = AsyncMock(return_value=b"5.00")  # Exactly at limit

    with (
        patch("app.advisor.claude_client.settings") as mock_settings,
        patch(
            "app.core.redis_client.redis_client", mock_aredis
        ),
    ):
        mock_settings.anthropic_api_key = "sk-ant-test-key"
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.ai_max_daily_api_calls = 500
        mock_settings.ai_prepaid_credit_usd = 5.0

        result = await c.ask_json(ModelTier.FAST, "system", "user", cache_ttl=0)

    assert result is None


def test_credit_hard_stop_allows_when_under_budget():
    """When cumulative cost < prepaid credit, call proceeds."""
    with patch("app.advisor.claude_client.settings") as mock_settings:
        mock_settings.anthropic_api_key = "sk-ant-test-key"
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.ai_max_daily_api_calls = 500
        mock_settings.ai_prepaid_credit_usd = 5.0
        c = ClaudeClient()

    expected = {"result": "under_budget"}
    mock_msg = _mock_message(expected)
    mock_redis = MagicMock()

    def _get_side_effect(key):
        if key == "ai_cumulative_cost":
            return b"2.50"  # Under the $5.00 limit
        return None  # ai_prepaid_credit → falls back to settings

    mock_redis.get.side_effect = _get_side_effect
    mock_redis.incr.return_value = 10

    mock_sync_client = MagicMock()
    mock_sync_client.messages.create.return_value = mock_msg

    with (
        patch("app.advisor.claude_client.settings") as mock_settings,
        patch("redis.from_url", return_value=mock_redis),
        patch("anthropic.Anthropic", return_value=mock_sync_client),
    ):
        mock_settings.anthropic_api_key = "sk-ant-test-key"
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.ai_max_daily_api_calls = 500
        mock_settings.ai_prepaid_credit_usd = 5.0

        result = c.ask_json_sync(ModelTier.FAST, "system", "user", cache_ttl=0)

    assert result == expected


def test_credit_hard_stop_skipped_when_prepaid_zero():
    """When ai_prepaid_credit_usd == 0, no credit check happens."""
    with patch("app.advisor.claude_client.settings") as mock_settings:
        mock_settings.anthropic_api_key = "sk-ant-test-key"
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.ai_max_daily_api_calls = 500
        mock_settings.ai_prepaid_credit_usd = 0.0
        c = ClaudeClient()

    expected = {"result": "no_credit_check"}
    mock_msg = _mock_message(expected)
    mock_redis = MagicMock()
    mock_redis.get.return_value = None  # No Redis credit → falls back to settings (0.0)
    mock_redis.incr.return_value = 1

    mock_sync_client = MagicMock()
    mock_sync_client.messages.create.return_value = mock_msg

    with (
        patch("app.advisor.claude_client.settings") as mock_settings,
        patch("redis.from_url", return_value=mock_redis),
        patch("anthropic.Anthropic", return_value=mock_sync_client),
    ):
        mock_settings.anthropic_api_key = "sk-ant-test-key"
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.ai_max_daily_api_calls = 500
        mock_settings.ai_prepaid_credit_usd = 0.0

        result = c.ask_json_sync(ModelTier.FAST, "system", "user", cache_ttl=0)

    assert result == expected


# ---------------------------------------------------------------------------
# Usage recording tests
# ---------------------------------------------------------------------------


def test_ask_json_sync_records_usage():
    """After a successful sync call, _record_usage_sync is called with correct params."""
    with patch("app.advisor.claude_client.settings") as mock_settings:
        mock_settings.anthropic_api_key = "sk-ant-test-key"
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.ai_max_daily_api_calls = 500
        mock_settings.ai_prepaid_credit_usd = 0.0
        c = ClaudeClient()

    expected = {"analysis": "good"}
    mock_msg = _mock_message(expected)
    mock_redis = MagicMock()
    mock_redis.get.return_value = None  # No Redis credit → skip credit check
    mock_redis.incr.return_value = 1

    mock_sync_client = MagicMock()
    mock_sync_client.messages.create.return_value = mock_msg

    with (
        patch("app.advisor.claude_client.settings") as mock_settings,
        patch("redis.from_url", return_value=mock_redis),
        patch("anthropic.Anthropic", return_value=mock_sync_client),
        patch.object(c, "_record_usage_sync") as mock_record,
    ):
        mock_settings.anthropic_api_key = "sk-ant-test-key"
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.ai_max_daily_api_calls = 500
        mock_settings.ai_prepaid_credit_usd = 0.0

        result = c.ask_json_sync(
            ModelTier.FAST, "system", "user", cache_ttl=0, insight_type="test_insight"
        )

    assert result == expected
    mock_record.assert_called_once()
    call_kwargs = mock_record.call_args.kwargs
    assert call_kwargs["insight_type"] == "test_insight"
    assert call_kwargs["model"] == MODEL_MAP[ModelTier.FAST]
    assert call_kwargs["input_tokens"] == 100
    assert call_kwargs["output_tokens"] == 50
    assert call_kwargs["cost_usd"] >= 0
    assert "latency_ms" in call_kwargs


async def test_ask_json_async_records_usage():
    """After a successful async call, _record_usage_async is called."""
    with patch("app.advisor.claude_client.settings") as mock_settings:
        mock_settings.anthropic_api_key = "sk-ant-test-key"
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.ai_max_daily_api_calls = 500
        mock_settings.ai_prepaid_credit_usd = 0.0
        c = ClaudeClient()

    expected = {"analysis": "good"}
    mock_msg = _mock_message(expected)

    mock_aredis = AsyncMock()
    mock_aredis.incr = AsyncMock(return_value=1)
    mock_aredis.get = AsyncMock(return_value=None)

    mock_async_client = AsyncMock()
    mock_async_client.messages.create = AsyncMock(return_value=mock_msg)

    with (
        patch("app.advisor.claude_client.settings") as mock_settings,
        patch(
            "app.core.redis_client.redis_client", mock_aredis
        ),
        patch("anthropic.AsyncAnthropic", return_value=mock_async_client),
        patch.object(
            c, "_record_usage_async", new_callable=AsyncMock
        ) as mock_record,
    ):
        mock_settings.anthropic_api_key = "sk-ant-test-key"
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.ai_max_daily_api_calls = 500
        mock_settings.ai_prepaid_credit_usd = 0.0

        result = await c.ask_json(
            ModelTier.FAST, "system", "user", cache_ttl=0, insight_type="async_insight"
        )

    assert result == expected
    # The async version uses asyncio.create_task, so we need to let it run
    # Since we patched _record_usage_async, the create_task should call our mock
    # Give the event loop a chance to run the task
    await asyncio.sleep(0)
    mock_record.assert_called_once()
    call_kwargs = mock_record.call_args.kwargs
    assert call_kwargs["insight_type"] == "async_insight"
    assert call_kwargs["model"] == MODEL_MAP[ModelTier.FAST]
    assert call_kwargs["input_tokens"] == 100
    assert call_kwargs["output_tokens"] == 50


def test_record_usage_sync_pushes_to_redis():
    """_record_usage_sync pushes JSON to 'ai_usage_queue' and increments cumulative cost."""
    with patch("app.advisor.claude_client.settings") as mock_settings:
        mock_settings.anthropic_api_key = "sk-ant-test-key"
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.ai_max_daily_api_calls = 500
        mock_settings.ai_prepaid_credit_usd = 0.0
        c = ClaudeClient()

    mock_redis = MagicMock()

    with (
        patch("app.advisor.claude_client.settings") as mock_settings,
        patch("redis.from_url", return_value=mock_redis),
    ):
        mock_settings.redis_url = "redis://localhost:6379/0"

        c._record_usage_sync(
            insight_type="test_type",
            model="claude-haiku-4-5-20251001",
            input_tokens=100,
            output_tokens=50,
            latency_ms=200,
            cost_usd=0.00035,
        )

    # Verify rpush was called with the queue key and a JSON payload
    mock_redis.rpush.assert_called_once()
    queue_key = mock_redis.rpush.call_args[0][0]
    payload_str = mock_redis.rpush.call_args[0][1]
    assert queue_key == "ai_usage_queue"
    payload = json.loads(payload_str)
    assert payload["insight_type"] == "test_type"
    assert payload["model_used"] == "claude-haiku-4-5-20251001"
    assert payload["input_tokens"] == 100
    assert payload["output_tokens"] == 50
    assert payload["latency_ms"] == 200
    assert payload["cost_usd"] == 0.00035
    assert "created_at" in payload

    # Verify incrbyfloat was called to track cumulative cost
    mock_redis.incrbyfloat.assert_called_once_with("ai_cumulative_cost", 0.00035)


def test_record_usage_sync_handles_redis_failure():
    """Redis failure in _record_usage_sync doesn't raise an exception."""
    with patch("app.advisor.claude_client.settings") as mock_settings:
        mock_settings.anthropic_api_key = "sk-ant-test-key"
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.ai_max_daily_api_calls = 500
        mock_settings.ai_prepaid_credit_usd = 0.0
        c = ClaudeClient()

    with (
        patch("app.advisor.claude_client.settings") as mock_settings,
        patch("redis.from_url", side_effect=Exception("Redis down")),
    ):
        mock_settings.redis_url = "redis://localhost:6379/0"

        # Should not raise
        c._record_usage_sync(
            insight_type="test_type",
            model="claude-haiku-4-5-20251001",
            input_tokens=100,
            output_tokens=50,
            latency_ms=200,
            cost_usd=0.001,
        )


# ---------------------------------------------------------------------------
# Insight type propagation tests
# ---------------------------------------------------------------------------


def test_insight_type_propagated_sync():
    """insight_type param is passed through to _record_usage_sync."""
    with patch("app.advisor.claude_client.settings") as mock_settings:
        mock_settings.anthropic_api_key = "sk-ant-test-key"
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.ai_max_daily_api_calls = 500
        mock_settings.ai_prepaid_credit_usd = 0.0
        c = ClaudeClient()

    expected = {"ok": True}
    mock_msg = _mock_message(expected)
    mock_redis = MagicMock()
    mock_redis.get.return_value = None  # No Redis credit → skip credit check
    mock_redis.incr.return_value = 1

    mock_sync_client = MagicMock()
    mock_sync_client.messages.create.return_value = mock_msg

    with (
        patch("app.advisor.claude_client.settings") as mock_settings,
        patch("redis.from_url", return_value=mock_redis),
        patch("anthropic.Anthropic", return_value=mock_sync_client),
        patch.object(c, "_record_usage_sync") as mock_record,
    ):
        mock_settings.anthropic_api_key = "sk-ant-test-key"
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.ai_max_daily_api_calls = 500
        mock_settings.ai_prepaid_credit_usd = 0.0

        c.ask_json_sync(
            ModelTier.DEEP, "sys", "usr",
            cache_ttl=0, insight_type="pattern_analysis",
        )

    mock_record.assert_called_once()
    assert mock_record.call_args.kwargs["insight_type"] == "pattern_analysis"


async def test_insight_type_propagated_async():
    """insight_type param is passed through to _record_usage_async."""
    with patch("app.advisor.claude_client.settings") as mock_settings:
        mock_settings.anthropic_api_key = "sk-ant-test-key"
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.ai_max_daily_api_calls = 500
        mock_settings.ai_prepaid_credit_usd = 0.0
        c = ClaudeClient()

    expected = {"ok": True}
    mock_msg = _mock_message(expected)

    mock_aredis = AsyncMock()
    mock_aredis.incr = AsyncMock(return_value=1)
    mock_aredis.get = AsyncMock(return_value=None)

    mock_async_client = AsyncMock()
    mock_async_client.messages.create = AsyncMock(return_value=mock_msg)

    with (
        patch("app.advisor.claude_client.settings") as mock_settings,
        patch(
            "app.core.redis_client.redis_client", mock_aredis
        ),
        patch("anthropic.AsyncAnthropic", return_value=mock_async_client),
        patch.object(
            c, "_record_usage_async", new_callable=AsyncMock
        ) as mock_record,
    ):
        mock_settings.anthropic_api_key = "sk-ant-test-key"
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.ai_max_daily_api_calls = 500
        mock_settings.ai_prepaid_credit_usd = 0.0

        await c.ask_json(
            ModelTier.FAST, "sys", "usr",
            cache_ttl=0, insight_type="risk_tuner",
        )

    await asyncio.sleep(0)
    mock_record.assert_called_once()
    assert mock_record.call_args.kwargs["insight_type"] == "risk_tuner"
