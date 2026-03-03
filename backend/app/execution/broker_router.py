"""Routes orders to the correct broker adapter based on symbol classification."""

import logging

from app.execution.adapters.base import (
    AccountBalance,
    BrokerAdapter,
    BrokerOrder,
    BrokerPosition,
    OrderSide,
    OrderType,
)

logger = logging.getLogger(__name__)

CRYPTO_QUOTES = {"USDT", "BTC", "ETH", "BUSD", "USDC"}


def is_crypto_symbol(symbol: str) -> bool:
    """Determine if a symbol is a crypto pair."""
    if "/" not in symbol:
        return False
    _, quote = symbol.split("/", 1)
    return quote in CRYPTO_QUOTES


class BrokerRouter:
    """Dispatches orders to the correct broker adapter based on symbol."""

    def __init__(
        self,
        stock_adapter: BrokerAdapter | None = None,
        crypto_adapter: BrokerAdapter | None = None,
        paper_adapter: BrokerAdapter | None = None,
    ):
        self._stock = stock_adapter
        self._crypto = crypto_adapter
        self._paper = paper_adapter

    def _resolve(self, symbol: str) -> BrokerAdapter:
        if self._paper:
            return self._paper
        if is_crypto_symbol(symbol):
            if not self._crypto:
                raise ValueError(f"No crypto adapter configured for {symbol}")
            return self._crypto
        if not self._stock:
            raise ValueError(f"No stock adapter configured for {symbol}")
        return self._stock

    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: float | None = None,
    ) -> BrokerOrder:
        adapter = self._resolve(symbol)
        logger.info(
            "Routing %s %s order for %s to %s",
            side.value,
            order_type.value,
            symbol,
            adapter.name,
        )
        return await adapter.place_order(symbol, side, order_type, quantity, price)

    async def cancel_order(self, symbol: str, broker_order_id: str) -> bool:
        adapter = self._resolve(symbol)
        return await adapter.cancel_order(broker_order_id, symbol=symbol)

    async def get_order_status(self, symbol: str, broker_order_id: str) -> BrokerOrder:
        adapter = self._resolve(symbol)
        return await adapter.get_order_status(broker_order_id, symbol=symbol)

    async def get_positions(self) -> list[BrokerPosition]:
        positions: list[BrokerPosition] = []
        for adapter in [self._stock, self._crypto, self._paper]:
            if adapter:
                positions.extend(await adapter.get_positions())
        return positions

    async def get_balance(self) -> AccountBalance:
        adapter = self._stock or self._paper
        if adapter:
            return await adapter.get_balance()
        raise ValueError("No adapter configured for balance query")
