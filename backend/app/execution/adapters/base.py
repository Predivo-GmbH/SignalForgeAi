"""Abstract broker adapter interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class BrokerOrder:
    broker_order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: float | None
    filled_quantity: float
    average_fill_price: float | None
    status: OrderStatus
    broker: str
    error: str | None = None


@dataclass
class BrokerPosition:
    symbol: str
    side: str
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    broker_position_id: str


@dataclass
class AccountBalance:
    equity: float
    cash: float
    buying_power: float


class BrokerAdapter(ABC):
    """Abstract interface for all broker integrations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Broker identifier (e.g. 'ccxt', 'paper')."""

    @abstractmethod
    async def connect(self) -> bool:
        """Verify broker connection. Returns True if healthy."""

    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: float | None = None,
    ) -> BrokerOrder:
        """Place an order and return the broker response."""

    @abstractmethod
    async def cancel_order(self, broker_order_id: str, symbol: str = "") -> bool:
        """Cancel an order by its broker-assigned ID."""

    @abstractmethod
    async def get_order_status(self, broker_order_id: str, symbol: str = "") -> BrokerOrder:
        """Poll current status of an order."""

    @abstractmethod
    async def get_positions(self) -> list[BrokerPosition]:
        """List all open positions at the broker."""

    @abstractmethod
    async def get_balance(self) -> AccountBalance:
        """Get current account balance."""
