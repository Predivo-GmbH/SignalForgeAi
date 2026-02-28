"""Tests for Redis pub/sub signal and price publishers."""

import json
from unittest.mock import AsyncMock


class TestSignalPublisher:
    def test_format_signal_message(self):
        from app.core.pubsub import SignalPublisher

        msg = SignalPublisher.format_message(
            symbol="BTC/USDT", action="BUY", confluence=75, price=50000.0
        )
        assert msg["symbol"] == "BTC/USDT"
        assert msg["action"] == "BUY"
        assert msg["confluence_score"] == 75
        assert msg["price"] == 50000.0
        assert "timestamp" in msg

    def test_channel_name(self):
        from app.core.pubsub import SignalPublisher

        assert SignalPublisher.CHANNEL == "signalforge:signals"

    def test_format_extra_kwargs(self):
        from app.core.pubsub import SignalPublisher

        msg = SignalPublisher.format_message(
            symbol="ETH/USDT",
            action="SELL",
            confluence=80,
            price=3000,
            regime="trending",
        )
        assert msg["regime"] == "trending"
        assert msg["symbol"] == "ETH/USDT"
        assert msg["action"] == "SELL"
        assert msg["confluence_score"] == 80

    def test_format_message_timestamp_is_iso(self):
        from app.core.pubsub import SignalPublisher

        msg = SignalPublisher.format_message(
            symbol="BTC/USDT", action="BUY", confluence=75, price=50000.0
        )
        # ISO format should contain 'T' separator and end with timezone info
        assert "T" in msg["timestamp"]

    async def test_publish_calls_redis(self):
        from app.core.pubsub import SignalPublisher

        mock_redis = AsyncMock()
        signal = SignalPublisher.format_message(
            symbol="BTC/USDT", action="BUY", confluence=75, price=50000.0
        )
        await SignalPublisher.publish(mock_redis, signal)
        mock_redis.publish.assert_called_once_with(
            "signalforge:signals", json.dumps(signal)
        )


class TestPricePublisher:
    def test_price_channel_name(self):
        from app.core.pubsub import PricePublisher

        assert PricePublisher.channel_for("BTC/USDT") == "signalforge:prices:BTC/USDT"

    def test_price_channel_different_symbols(self):
        from app.core.pubsub import PricePublisher

        assert PricePublisher.channel_for("ETH/USDT") == "signalforge:prices:ETH/USDT"
        assert PricePublisher.channel_for("EUR/USD") == "signalforge:prices:EUR/USD"

    async def test_price_publish_calls_redis(self):
        from app.core.pubsub import PricePublisher

        mock_redis = AsyncMock()
        price_data = {"bid": 50000.0, "ask": 50001.0}
        await PricePublisher.publish(mock_redis, "BTC/USDT", price_data)
        mock_redis.publish.assert_called_once_with(
            "signalforge:prices:BTC/USDT", json.dumps(price_data)
        )


class TestRedisClient:
    def test_redis_client_importable(self):
        from app.core.redis_client import redis_client

        assert redis_client is not None

    def test_get_redis_is_coroutine(self):
        import asyncio

        from app.core.redis_client import get_redis

        assert asyncio.iscoroutinefunction(get_redis)
