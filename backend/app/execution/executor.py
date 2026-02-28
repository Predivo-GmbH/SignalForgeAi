import uuid
from dataclasses import dataclass
from datetime import datetime, timezone


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


class OrderExecutor:
    def __init__(self, paper_mode: bool = True):
        self.paper_mode = paper_mode

    def place_order(self, request: OrderRequest) -> OrderResult:
        if self.paper_mode:
            return self._simulate_fill(request)
        raise NotImplementedError("Live trading not yet implemented")

    def _simulate_fill(self, request: OrderRequest) -> OrderResult:
        return OrderResult(
            order_id=f"sim-{uuid.uuid4().hex[:12]}",
            status="simulated",
            filled=True,
            fill_price=request.price,
            broker="paper",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
