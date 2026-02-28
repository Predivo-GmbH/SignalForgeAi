"""Tests for real-time WebSocket broadcasting via Redis."""

import json
from unittest.mock import AsyncMock

import pytest


class TestRedisSubscriber:
    def test_redis_subscriber_import(self):
        from app.core.redis_subscriber import RedisSubscriber

        sub = RedisSubscriber()
        assert sub._running is False
        assert sub._task is None

    def test_redis_subscriber_custom_url(self):
        from app.core.redis_subscriber import RedisSubscriber

        sub = RedisSubscriber(redis_url="redis://custom:6380/1")
        assert sub._redis_url == "redis://custom:6380/1"

    @pytest.mark.asyncio
    async def test_stop_when_not_started(self):
        from app.core.redis_subscriber import RedisSubscriber

        sub = RedisSubscriber()
        # Should not raise even if never started
        await sub.stop()
        assert sub._running is False


class TestTradePublisher:
    def test_trade_publisher_exists(self):
        from app.core.pubsub import TradePublisher

        assert TradePublisher is not None

    def test_trade_channel_name(self):
        from app.core.pubsub import TradePublisher

        assert TradePublisher.CHANNEL == "signalforge:trades"

    def test_format_trade_message(self):
        from app.core.pubsub import TradePublisher

        msg = TradePublisher.format_message(
            symbol="BTC/USDT", side="BUY", qty=0.5, price=50000.0
        )
        assert msg["symbol"] == "BTC/USDT"
        assert msg["side"] == "BUY"
        assert msg["qty"] == 0.5
        assert msg["price"] == 50000.0
        assert "timestamp" in msg

    def test_format_trade_extra_kwargs(self):
        from app.core.pubsub import TradePublisher

        msg = TradePublisher.format_message(
            symbol="ETH/USDT",
            side="SELL",
            qty=2.0,
            price=3000.0,
            order_id="abc-123",
        )
        assert msg["order_id"] == "abc-123"

    @pytest.mark.asyncio
    async def test_trade_publish_calls_redis(self):
        from app.core.pubsub import TradePublisher

        mock_redis = AsyncMock()
        trade = TradePublisher.format_message(
            symbol="BTC/USDT", side="BUY", qty=1.0, price=50000.0
        )
        await TradePublisher.publish(mock_redis, trade)
        mock_redis.publish.assert_called_once_with(
            "signalforge:trades", json.dumps(trade)
        )


class TestConnectionManagerTrades:
    def test_manager_has_trades_channel(self):
        from app.ws.hub import manager

        assert "trades" in manager.active_connections

    @pytest.mark.asyncio
    async def test_broadcast_trades_handles_empty(self):
        from app.ws.hub import manager

        # Should not raise even with no connections
        await manager.broadcast("trades", {"test": True})


class TestWSTradesEndpoint:
    def test_ws_trades_endpoint_registered(self):
        from app.main import app

        routes = [getattr(r, "path", None) for r in app.routes]
        assert "/ws/trades" in routes
