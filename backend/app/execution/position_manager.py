import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.execution.risk_checks import AccountState


@dataclass
class Position:
    id: str
    symbol: str
    direction: str
    entry_price: float
    quantity: float
    stop_loss: float
    take_profit: float
    order_id: str
    is_open: bool = True
    pnl: float = 0.0
    exit_price: float | None = None
    exit_reason: str | None = None
    opened_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    closed_at: str | None = None


class PositionManager:
    def __init__(self, initial_equity: float = 10000):
        self._positions: dict[str, Position] = {}
        self._initial_equity = initial_equity
        self._realized_pnl = 0.0

    def open_position(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        quantity: float,
        stop_loss: float,
        take_profit: float,
        order_id: str,
    ) -> Position:
        pos = Position(
            id=uuid.uuid4().hex[:12],
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            order_id=order_id,
        )
        self._positions[pos.id] = pos
        return pos

    def close_position(self, position_id: str, exit_price: float, reason: str) -> Position:
        pos = self._positions[position_id]
        pos.is_open = False
        pos.exit_price = exit_price
        pos.exit_reason = reason
        pos.closed_at = datetime.now(timezone.utc).isoformat()
        if pos.direction == "BUY":
            pos.pnl = (exit_price - pos.entry_price) * pos.quantity
        else:
            pos.pnl = (pos.entry_price - exit_price) * pos.quantity
        self._realized_pnl += pos.pnl
        return pos

    def trail_stop(self, position_id: str, new_stop: float) -> None:
        pos = self._positions[position_id]
        if pos.direction == "BUY" and new_stop > pos.stop_loss:
            pos.stop_loss = new_stop
        elif pos.direction == "SELL" and new_stop < pos.stop_loss:
            pos.stop_loss = new_stop

    def get_position(self, position_id: str) -> Position:
        return self._positions[position_id]

    def list_open(self) -> list[Position]:
        return [p for p in self._positions.values() if p.is_open]

    def account_state(self) -> AccountState:
        return AccountState(
            equity=self._initial_equity + self._realized_pnl,
            daily_pnl=self._realized_pnl,
            open_positions=len(self.list_open()),
        )
