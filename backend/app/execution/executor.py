"""Order executor -- routes signals through BrokerRouter with DB persistence.

Also retains legacy OrderRequest/OrderResult/OrderExecutor for backward
compatibility with the original paper-mode pipeline.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.execution.adapters.base import OrderSide, OrderType
from app.execution.broker_router import BrokerRouter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Legacy dataclasses (kept for backward compatibility with existing tests)
# ---------------------------------------------------------------------------


@dataclass
class OrderRequest:
    symbol: str
    direction: str  # BUY, SELL
    quantity: float
    order_type: str  # market, limit
    price: float
    stop_loss: float
    take_profit: float


@dataclass
class OrderResult:
    order_id: str
    status: str  # simulated, submitted, filled, rejected
    filled: bool
    fill_price: float | None
    broker: str
    timestamp: str


# ---------------------------------------------------------------------------
# New OrderExecutor (BrokerRouter + DB persistence)
# ---------------------------------------------------------------------------


class OrderExecutor:
    """Executes trading orders through broker adapters with DB persistence.

    When constructed **without** arguments (or with ``paper_mode=True``),
    falls back to the legacy paper-only simulation for backward compat.
    When constructed **with** a ``BrokerRouter``, uses the full
    adapter-based execution path with Order model persistence.
    """

    def __init__(
        self,
        broker_router: BrokerRouter | None = None,
        *,
        paper_mode: bool = True,
    ):
        self._router = broker_router
        self.paper_mode = paper_mode if broker_router is None else False

    # ------------------------------------------------------------------
    # New async path -- BrokerRouter + DB Order rows
    # ------------------------------------------------------------------

    async def execute_signal(
        self,
        db: AsyncSession,
        user_id: str,
        signal: dict,
    ):
        """Execute a trading signal: create Order row -> send to broker -> update Order.

        Returns the persisted ``Order`` model instance.
        """
        from app.models.order import Order

        if self._router is None:
            raise RuntimeError(
                "OrderExecutor requires a BrokerRouter for execute_signal(). "
                "Pass a BrokerRouter to the constructor."
            )

        symbol: str = signal["symbol"]
        direction: str = signal["direction"]
        quantity: float = signal.get("quantity", 0.0)
        price: float | None = signal.get("price")
        order_type_str: str = signal.get("order_type", "market")

        # Create Order row in DB with status "pending"
        order = Order(
            user_id=uuid.UUID(user_id) if isinstance(user_id, str) else user_id,
            signal_id=(
                uuid.UUID(signal["signal_id"])
                if signal.get("signal_id")
                else None
            ),
            symbol=symbol,
            direction=direction,
            order_type=order_type_str,
            quantity=quantity,
            price=price,
            stop_loss=signal.get("stop_loss"),
            take_profit=signal.get("take_profit"),
            status="pending",
            broker="pending",
        )
        db.add(order)
        await db.flush()

        try:
            # Map to adapter enums
            side = OrderSide.BUY if direction == "BUY" else OrderSide.SELL
            o_type = OrderType(order_type_str)

            # Send to broker via router
            broker_result = await self._router.place_order(
                symbol=symbol,
                side=side,
                order_type=o_type,
                quantity=quantity,
                price=price,
            )

            # Update Order with broker response
            order.broker = broker_result.broker
            order.broker_order_id = broker_result.broker_order_id
            order.status = broker_result.status.value
            order.filled_quantity = broker_result.filled_quantity
            order.average_fill_price = broker_result.average_fill_price

            logger.info(
                "Order %s executed via %s — status=%s filled_qty=%s avg_price=%s",
                order.id,
                order.broker,
                order.status,
                order.filled_quantity,
                order.average_fill_price,
            )

        except Exception as e:
            order.status = "rejected"
            order.error_message = str(e)
            logger.error("Order %s rejected: %s", order.id, e)

        await db.flush()
        return order

    # ------------------------------------------------------------------
    # Legacy sync path -- paper-mode simulation (backward compat)
    # ------------------------------------------------------------------

    def place_order(self, request: OrderRequest) -> OrderResult:
        """Legacy paper-only order placement (synchronous)."""
        if self.paper_mode:
            return self._simulate_fill(request)
        raise NotImplementedError("Live trading requires execute_signal() with a BrokerRouter")

    def _simulate_fill(self, request: OrderRequest) -> OrderResult:
        return OrderResult(
            order_id=f"sim-{uuid.uuid4().hex[:12]}",
            status="simulated",
            filled=True,
            fill_price=request.price,
            broker="paper",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
