"""Alpaca broker adapter for US stocks + crypto."""

import logging

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

_ALPACA_STATUS_MAP = {
    "new": OrderStatus.SUBMITTED,
    "accepted": OrderStatus.SUBMITTED,
    "pending_new": OrderStatus.PENDING,
    "partially_filled": OrderStatus.PARTIAL,
    "filled": OrderStatus.FILLED,
    "canceled": OrderStatus.CANCELLED,
    "expired": OrderStatus.CANCELLED,
    "rejected": OrderStatus.REJECTED,
    "pending_cancel": OrderStatus.SUBMITTED,
    "pending_replace": OrderStatus.SUBMITTED,
}


class AlpacaAdapter(BrokerAdapter):
    """Alpaca Markets broker adapter using alpaca-py SDK."""

    def __init__(self, api_key: str, api_secret: str, paper: bool = True):
        from alpaca.trading.client import TradingClient

        self._client = TradingClient(api_key, api_secret, paper=paper)
        self._paper = paper

    @property
    def name(self) -> str:
        return "alpaca"

    async def connect(self) -> bool:
        try:
            self._client.get_account()
            return True
        except Exception as e:
            logger.error("Alpaca connect failed: %s", e)
            return False

    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: float | None = None,
    ) -> BrokerOrder:
        from alpaca.trading.enums import OrderSide as AlpSide
        from alpaca.trading.enums import TimeInForce
        from alpaca.trading.requests import LimitOrderRequest, MarketOrderRequest

        alp_side = AlpSide.BUY if side == OrderSide.BUY else AlpSide.SELL
        alp_symbol = symbol.replace("/", "")

        if order_type == OrderType.MARKET:
            req = MarketOrderRequest(
                symbol=alp_symbol,
                qty=quantity,
                side=alp_side,
                time_in_force=TimeInForce.GTC,
            )
        else:
            req = LimitOrderRequest(
                symbol=alp_symbol,
                qty=quantity,
                side=alp_side,
                limit_price=price,
                time_in_force=TimeInForce.GTC,
            )

        resp = self._client.submit_order(req)
        return BrokerOrder(
            broker_order_id=str(resp.id),
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            filled_quantity=float(resp.filled_qty or 0),
            average_fill_price=(
                float(resp.filled_avg_price) if resp.filled_avg_price else None
            ),
            status=_ALPACA_STATUS_MAP.get(resp.status.value, OrderStatus.PENDING),
            broker="alpaca",
        )

    async def cancel_order(self, broker_order_id: str) -> bool:
        try:
            self._client.cancel_order_by_id(broker_order_id)
            return True
        except Exception as e:
            logger.error("Alpaca cancel failed: %s", e)
            return False

    async def get_order_status(self, broker_order_id: str) -> BrokerOrder:
        resp = self._client.get_order_by_id(broker_order_id)
        return BrokerOrder(
            broker_order_id=str(resp.id),
            symbol=resp.symbol,
            side=OrderSide.BUY if resp.side.value == "buy" else OrderSide.SELL,
            order_type=OrderType(resp.type.value) if resp.type else OrderType.MARKET,
            quantity=float(resp.qty),
            price=float(resp.limit_price) if resp.limit_price else None,
            filled_quantity=float(resp.filled_qty or 0),
            average_fill_price=(
                float(resp.filled_avg_price) if resp.filled_avg_price else None
            ),
            status=_ALPACA_STATUS_MAP.get(resp.status.value, OrderStatus.PENDING),
            broker="alpaca",
        )

    async def get_positions(self) -> list[BrokerPosition]:
        positions = self._client.get_all_positions()
        return [
            BrokerPosition(
                symbol=p.symbol,
                side="BUY" if float(p.qty) > 0 else "SELL",
                quantity=abs(float(p.qty)),
                entry_price=float(p.avg_entry_price),
                current_price=float(p.current_price),
                unrealized_pnl=float(p.unrealized_pl),
                broker_position_id=str(p.asset_id),
            )
            for p in positions
        ]

    async def get_balance(self) -> AccountBalance:
        acct = self._client.get_account()
        return AccountBalance(
            equity=float(acct.equity),
            cash=float(acct.cash),
            buying_power=float(acct.buying_power),
        )
