"""CCXT broker adapter for crypto exchanges (Binance primary)."""

import logging

import ccxt.async_support as ccxt_async

from app.execution.adapters.base import (
    AccountBalance,
    BrokerAdapter,
    BrokerOrder,
    BrokerPosition,
    OrderSide,
    OrderStatus,
    OrderType,
)

logger = logging.getLogger(__name__)

_CCXT_STATUS_MAP = {
    "open": OrderStatus.SUBMITTED,
    "closed": OrderStatus.FILLED,
    "canceled": OrderStatus.CANCELLED,
    "expired": OrderStatus.CANCELLED,
    "rejected": OrderStatus.REJECTED,
}


class CCXTAdapter(BrokerAdapter):
    """CCXT adapter for crypto exchange trading."""

    def __init__(
        self,
        exchange_id: str = "binance",
        api_key: str = "",
        api_secret: str = "",
        password: str = "",
        testnet: bool = True,
    ):
        exchange_class = getattr(ccxt_async, exchange_id)
        config: dict = {
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
        }
        if password:
            config["password"] = password
        if testnet:
            config["sandbox"] = True
        self._exchange = exchange_class(config)
        self._exchange_id = exchange_id

    @property
    def name(self) -> str:
        return "ccxt"

    async def connect(self) -> bool:
        try:
            await self._exchange.load_markets()
            return True
        except Exception:
            logger.exception("CCXT connect failed")
            return False

    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: float | None = None,
    ) -> BrokerOrder:
        resp = await self._exchange.create_order(
            symbol=symbol,
            type=order_type.value,
            side=side.value.lower(),
            amount=quantity,
            price=price,
        )
        return BrokerOrder(
            broker_order_id=str(resp["id"]),
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            filled_quantity=float(resp.get("filled", 0)),
            average_fill_price=(
                float(resp["average"]) if resp.get("average") else None
            ),
            status=_CCXT_STATUS_MAP.get(resp.get("status", ""), OrderStatus.PENDING),
            broker=f"ccxt:{self._exchange_id}",
        )

    async def cancel_order(self, broker_order_id: str, symbol: str = "") -> bool:
        try:
            await self._exchange.cancel_order(broker_order_id, symbol=symbol or None)
            return True
        except Exception:
            logger.exception("CCXT cancel failed")
            return False

    async def get_order_status(self, broker_order_id: str, symbol: str = "") -> BrokerOrder:
        resp = await self._exchange.fetch_order(broker_order_id, symbol=symbol or None)
        return BrokerOrder(
            broker_order_id=str(resp["id"]),
            symbol=resp["symbol"],
            side=OrderSide(resp["side"].upper()),
            order_type=OrderType(resp.get("type", "market")),
            quantity=float(resp["amount"]),
            price=float(resp["price"]) if resp.get("price") else None,
            filled_quantity=float(resp.get("filled", 0)),
            average_fill_price=(
                float(resp["average"]) if resp.get("average") else None
            ),
            status=_CCXT_STATUS_MAP.get(resp.get("status", ""), OrderStatus.PENDING),
            broker=f"ccxt:{self._exchange_id}",
        )

    async def get_positions(self) -> list[BrokerPosition]:
        positions = await self._exchange.fetch_positions()
        return [
            BrokerPosition(
                symbol=p["symbol"],
                side="BUY" if p.get("side") == "long" else "SELL",
                quantity=abs(float(p.get("contracts", 0))),
                entry_price=float(p.get("entryPrice", 0)),
                current_price=float(p.get("markPrice", 0)),
                unrealized_pnl=float(p.get("unrealizedPnl", 0)),
                broker_position_id=str(p.get("id", "")),
            )
            for p in positions
            if float(p.get("contracts", 0)) != 0
        ]

    async def get_balance(self) -> AccountBalance:
        balance = await self._exchange.fetch_balance()
        total = balance.get("total", {})
        free = balance.get("free", {})
        usdt = total.get("USDT", 0)
        return AccountBalance(
            equity=float(usdt),
            cash=float(free.get("USDT", 0)),
            buying_power=float(free.get("USDT", 0)),
        )

    async def get_full_balance(self) -> dict[str, float]:
        """Return all non-zero asset balances as {symbol: total_amount}."""
        balance = await self._exchange.fetch_balance()
        total = balance.get("total", {})
        return {k: float(v) for k, v in total.items() if float(v or 0) > 0}

    async def close(self):
        """Close the exchange connection."""
        await self._exchange.close()
