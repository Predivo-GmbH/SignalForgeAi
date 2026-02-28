"""Redis pub/sub publishers for signals and price data."""

import json
from datetime import datetime, timezone


class SignalPublisher:
    """Publishes trading signals to a shared Redis channel."""

    CHANNEL = "signalforge:signals"

    @staticmethod
    def format_message(symbol: str, action: str, confluence: int, price: float, **kwargs) -> dict:
        """Format a signal message with standard fields plus optional extras."""
        return {
            "symbol": symbol,
            "action": action,
            "confluence_score": confluence,
            "price": price,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **kwargs,
        }

    @staticmethod
    async def publish(redis, signal_dict: dict) -> None:
        """Publish a signal message to the signals channel."""
        await redis.publish(SignalPublisher.CHANNEL, json.dumps(signal_dict))


class PricePublisher:
    """Publishes live price updates to per-symbol Redis channels."""

    @staticmethod
    def channel_for(symbol: str) -> str:
        """Return the Redis channel name for a given symbol."""
        return f"signalforge:prices:{symbol}"

    @staticmethod
    async def publish(redis, symbol: str, price_data: dict) -> None:
        """Publish price data to the symbol-specific channel."""
        channel = PricePublisher.channel_for(symbol)
        await redis.publish(channel, json.dumps(price_data))


class TradePublisher:
    """Publishes trade execution events to a shared Redis channel."""

    CHANNEL = "signalforge:trades"

    @staticmethod
    def format_message(
        symbol: str, side: str, qty: float, price: float, **kwargs
    ) -> dict:
        """Format a trade message with standard fields plus optional extras."""
        return {
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "price": price,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **kwargs,
        }

    @staticmethod
    async def publish(redis, trade_dict: dict) -> None:
        """Publish a trade message to the trades channel."""
        await redis.publish(TradePublisher.CHANNEL, json.dumps(trade_dict))
