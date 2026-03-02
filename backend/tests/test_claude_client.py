"""Tests for the centralized Claude client."""

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
