"""Paper trading adapter -- simulates order execution locally."""

import uuid

from app.execution.adapters.base import (
    AccountBalance,
    BrokerAdapter,
    BrokerOrder,
    BrokerPosition,
    OrderSide,
    OrderStatus,
    OrderType,
)


class PaperAdapter(BrokerAdapter):
    """Simulates broker execution for paper trading."""

    def __init__(self, initial_equity: float = 10000.0, slippage_pct: float = 0.001):
        self._equity = initial_equity
        self._cash = initial_equity
        self._slippage_pct = slippage_pct
        self._orders: dict[str, BrokerOrder] = {}
        self._positions: dict[str, BrokerPosition] = {}

    @property
    def name(self) -> str:
        return "paper"

    async def connect(self) -> bool:
        return True

    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: float | None = None,
    ) -> BrokerOrder:
        order_id = f"paper-{uuid.uuid4().hex[:12]}"
        fill_price = price or 0.0
        if side == OrderSide.BUY:
            fill_price *= 1 + self._slippage_pct
        else:
            fill_price *= 1 - self._slippage_pct

        order = BrokerOrder(
            broker_order_id=order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            filled_quantity=quantity,
            average_fill_price=round(fill_price, 6),
            status=OrderStatus.FILLED,
            broker="paper",
        )
        self._orders[order_id] = order
        return order

    async def cancel_order(self, broker_order_id: str, symbol: str = "") -> bool:
        if broker_order_id in self._orders:
            self._orders[broker_order_id].status = OrderStatus.CANCELLED
            return True
        return False

    async def get_order_status(self, broker_order_id: str, symbol: str = "") -> BrokerOrder:
        return self._orders[broker_order_id]

    async def get_positions(self) -> list[BrokerPosition]:
        return list(self._positions.values())

    async def get_balance(self) -> AccountBalance:
        return AccountBalance(
            equity=self._equity, cash=self._cash, buying_power=self._cash
        )
