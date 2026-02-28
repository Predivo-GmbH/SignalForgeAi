# Phase 6: Live Trading & Hardening — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire the existing SignalForge backend to real brokers (Alpaca + Binance/CCXT), persist all execution state to the database, schedule automated trading via Celery Beat, add circuit breakers / rate limiting / structured logging, and produce a production Docker Compose.

**Architecture:** Monolithic scheduler — all periodic logic runs as Celery Beat tasks within the existing FastAPI + Celery backend. Two broker adapters (Alpaca, CCXT/Binance) behind a unified `BrokerAdapter` ABC with a `BrokerRouter` that dispatches by symbol class.

**Tech Stack:** Python 3.12, FastAPI 0.115, SQLAlchemy 2.0 (async), Celery 5.4, alpaca-py, ccxt 4.4, cryptography (Fernet), slowapi, structlog, Redis 7, TimescaleDB, React 19, Vite 7, Tailwind 4

---

## Agent Team Waves

```
Wave 1 (parallel, no deps):
  @db-models        — Order, Position, BacktestResult models + migration
  @broker-adapters   — BrokerAdapter ABC + Alpaca + CCXT + Paper + Router
  @crypto-api        — Fernet encryption + /api/broker CRUD endpoints

Wave 2 (parallel, depends on Wave 1):
  @position-manager  — DB-backed PositionManager, replace in-memory
  @order-executor    — Rewrite executor to use BrokerRouter + Order model
  @candle-storage    — DB-backed CandleStorage + market/candles endpoint

Wave 3 (parallel, depends on Wave 2):
  @ingestion-tasks   — Celery Beat + ingest_candles + run_signal_pipeline
  @execution-tasks   — execute_signals + poll_orders + manage_positions tasks
  @alert-tasks       — Alert persistence, email wiring, daily summary, HMM real data

Wave 4 (parallel, depends on Wave 3):
  @realtime          — Redis subscriber + WebSocket broadcasting + TradePublisher
  @hardening         — Circuit breaker, rate limiting, structlog, health checks

Wave 5 (parallel, depends on Wave 4):
  @docker-prod       — Production Docker Compose + multi-stage Dockerfile
  @frontend-wiring   — API Keys page, useTradeStream, real correlation data
```

---

## Wave 1: Foundation

### Task 1: @db-models — New Database Models + Migration

**Files:**
- Create: `backend/app/models/order.py`
- Create: `backend/app/models/position.py`
- Create: `backend/app/models/backtest_result.py`
- Modify: `backend/app/models/user.py` (add alert_config column)
- Create: `backend/tests/test_models_phase6.py`

**Step 1: Create Order model**

```python
# backend/app/models/order.py
"""Order model — tracks every order sent to a broker."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    signal_id = Column(UUID(as_uuid=True), nullable=True)
    symbol = Column(String(20), nullable=False)
    direction = Column(String(4), nullable=False)  # BUY / SELL
    order_type = Column(String(10), nullable=False)  # market / limit / stop
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=True)  # limit price, null for market
    filled_quantity = Column(Float, default=0.0)
    average_fill_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    status = Column(String(20), default="pending")  # pending/filled/partial/cancelled/rejected
    broker = Column(String(20), nullable=False)  # alpaca / ccxt / paper
    broker_order_id = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
```

**Step 2: Create Position model**

```python
# backend/app/models/position.py
"""Position model — DB-backed position tracking."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, String
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Position(Base):
    __tablename__ = "positions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    order_id = Column(UUID(as_uuid=True), nullable=True)
    symbol = Column(String(20), nullable=False)
    direction = Column(String(4), nullable=False)
    quantity = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    unrealized_pnl = Column(Float, default=0.0)
    broker = Column(String(20), nullable=False)
    broker_position_id = Column(String(100), nullable=True)
    is_open = Column(Boolean, default=True, index=True)
    opened_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    closed_at = Column(DateTime(timezone=True), nullable=True)
```

**Step 3: Create BacktestResult model**

```python
# backend/app/models/backtest_result.py
"""BacktestResult model — persisted backtest outcomes."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID

from app.core.database import Base


class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    strategy_id = Column(UUID(as_uuid=True), nullable=True)
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(5), nullable=False)
    days = Column(Integer, nullable=False)
    metrics = Column(JSON, nullable=False)
    equity_curve = Column(JSON, nullable=True)
    trade_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
```

**Step 4: Add alert_config to User model**

In `backend/app/models/user.py`, add:
```python
from sqlalchemy.dialects.postgresql import JSON
# ... existing columns ...
alert_config = Column(JSON, nullable=True)  # persisted alert preferences
```

**Step 5: Generate Alembic migration**

```bash
cd backend
.venv/Scripts/python.exe -m alembic revision --autogenerate -m "add order, position, backtest_result models and user alert_config"
.venv/Scripts/python.exe -m alembic upgrade head
```

**Step 6: Write model tests**

```python
# backend/tests/test_models_phase6.py
"""Tests for Phase 6 database models."""
from uuid import uuid4
from app.models.order import Order
from app.models.position import Position
from app.models.backtest_result import BacktestResult


def test_order_model_defaults():
    order = Order(
        user_id=uuid4(), symbol="BTC/USDT", direction="BUY",
        order_type="limit", quantity=0.1, price=50000.0, broker="paper",
    )
    assert order.status == "pending"
    assert order.filled_quantity == 0.0


def test_position_model_defaults():
    pos = Position(
        user_id=uuid4(), symbol="BTC/USDT", direction="BUY",
        quantity=0.1, entry_price=50000.0, broker="paper",
    )
    assert pos.is_open is True
    assert pos.unrealized_pnl == 0.0


def test_backtest_result_model():
    result = BacktestResult(
        user_id=uuid4(), symbol="BTC/USDT", timeframe="1h", days=30,
        metrics={"win_rate": 0.55, "sharpe": 1.2}, trade_count=42,
    )
    assert result.metrics["win_rate"] == 0.55
    assert result.trade_count == 42
```

**Step 7: Run tests**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/test_models_phase6.py -v
```

**Step 8: Lint**

```bash
cd backend && .venv/Scripts/python.exe -m ruff check .
```

**Step 9: Commit**

```bash
git add backend/app/models/order.py backend/app/models/position.py backend/app/models/backtest_result.py backend/app/models/user.py backend/alembic/versions/ backend/tests/test_models_phase6.py
git commit -m "feat(backend): add Order, Position, BacktestResult models + migration"
```

---

### Task 2: @broker-adapters — Broker Adapter Layer

**Files:**
- Create: `backend/app/execution/adapters/__init__.py`
- Create: `backend/app/execution/adapters/base.py`
- Create: `backend/app/execution/adapters/paper.py`
- Create: `backend/app/execution/adapters/alpaca_adapter.py`
- Create: `backend/app/execution/adapters/ccxt_adapter.py`
- Create: `backend/app/execution/broker_router.py`
- Create: `backend/tests/test_broker_adapters.py`

**Step 1: Create BrokerAdapter ABC**

```python
# backend/app/execution/adapters/base.py
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
        """Broker identifier (e.g. 'alpaca', 'ccxt', 'paper')."""

    @abstractmethod
    async def connect(self) -> bool:
        """Verify broker connection. Returns True if healthy."""

    @abstractmethod
    async def place_order(
        self, symbol: str, side: OrderSide, order_type: OrderType,
        quantity: float, price: float | None = None,
    ) -> BrokerOrder:
        """Place an order and return the broker response."""

    @abstractmethod
    async def cancel_order(self, broker_order_id: str) -> bool:
        """Cancel an order by its broker-assigned ID."""

    @abstractmethod
    async def get_order_status(self, broker_order_id: str) -> BrokerOrder:
        """Poll current status of an order."""

    @abstractmethod
    async def get_positions(self) -> list[BrokerPosition]:
        """List all open positions at the broker."""

    @abstractmethod
    async def get_balance(self) -> AccountBalance:
        """Get current account balance."""
```

**Step 2: Create PaperAdapter**

```python
# backend/app/execution/adapters/paper.py
"""Paper trading adapter — simulates order execution locally."""

import uuid
from datetime import datetime, timezone

from app.execution.adapters.base import (
    AccountBalance, BrokerAdapter, BrokerOrder, BrokerPosition,
    OrderSide, OrderStatus, OrderType,
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
        self, symbol: str, side: OrderSide, order_type: OrderType,
        quantity: float, price: float | None = None,
    ) -> BrokerOrder:
        order_id = f"paper-{uuid.uuid4().hex[:12]}"
        fill_price = price or 0.0
        # Simulate slippage
        if side == OrderSide.BUY:
            fill_price *= 1 + self._slippage_pct
        else:
            fill_price *= 1 - self._slippage_pct

        order = BrokerOrder(
            broker_order_id=order_id, symbol=symbol, side=side,
            order_type=order_type, quantity=quantity, price=price,
            filled_quantity=quantity, average_fill_price=round(fill_price, 6),
            status=OrderStatus.FILLED, broker="paper",
        )
        self._orders[order_id] = order
        return order

    async def cancel_order(self, broker_order_id: str) -> bool:
        if broker_order_id in self._orders:
            self._orders[broker_order_id].status = OrderStatus.CANCELLED
            return True
        return False

    async def get_order_status(self, broker_order_id: str) -> BrokerOrder:
        return self._orders[broker_order_id]

    async def get_positions(self) -> list[BrokerPosition]:
        return list(self._positions.values())

    async def get_balance(self) -> AccountBalance:
        return AccountBalance(equity=self._equity, cash=self._cash, buying_power=self._cash)
```

**Step 3: Create AlpacaAdapter**

```python
# backend/app/execution/adapters/alpaca_adapter.py
"""Alpaca broker adapter for US stocks + crypto."""

import logging

from app.execution.adapters.base import (
    AccountBalance, BrokerAdapter, BrokerOrder, BrokerPosition,
    OrderSide, OrderStatus, OrderType,
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
        self, symbol: str, side: OrderSide, order_type: OrderType,
        quantity: float, price: float | None = None,
    ) -> BrokerOrder:
        from alpaca.trading.requests import LimitOrderRequest, MarketOrderRequest
        from alpaca.trading.enums import OrderSide as AlpSide, TimeInForce

        alp_side = AlpSide.BUY if side == OrderSide.BUY else AlpSide.SELL
        # Alpaca uses dash-separated symbols for crypto (e.g. BTC/USD -> BTCUSD)
        alp_symbol = symbol.replace("/", "")

        if order_type == OrderType.MARKET:
            req = MarketOrderRequest(
                symbol=alp_symbol, qty=quantity, side=alp_side,
                time_in_force=TimeInForce.GTC,
            )
        else:
            req = LimitOrderRequest(
                symbol=alp_symbol, qty=quantity, side=alp_side,
                limit_price=price, time_in_force=TimeInForce.GTC,
            )

        resp = self._client.submit_order(req)
        return BrokerOrder(
            broker_order_id=str(resp.id), symbol=symbol, side=side,
            order_type=order_type, quantity=quantity, price=price,
            filled_quantity=float(resp.filled_qty or 0),
            average_fill_price=float(resp.filled_avg_price) if resp.filled_avg_price else None,
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
            broker_order_id=str(resp.id), symbol=resp.symbol,
            side=OrderSide.BUY if resp.side.value == "buy" else OrderSide.SELL,
            order_type=OrderType(resp.type.value) if resp.type else OrderType.MARKET,
            quantity=float(resp.qty), price=float(resp.limit_price) if resp.limit_price else None,
            filled_quantity=float(resp.filled_qty or 0),
            average_fill_price=float(resp.filled_avg_price) if resp.filled_avg_price else None,
            status=_ALPACA_STATUS_MAP.get(resp.status.value, OrderStatus.PENDING),
            broker="alpaca",
        )

    async def get_positions(self) -> list[BrokerPosition]:
        positions = self._client.get_all_positions()
        return [
            BrokerPosition(
                symbol=p.symbol, side="BUY" if float(p.qty) > 0 else "SELL",
                quantity=abs(float(p.qty)), entry_price=float(p.avg_entry_price),
                current_price=float(p.current_price),
                unrealized_pnl=float(p.unrealized_pl),
                broker_position_id=str(p.asset_id),
            )
            for p in positions
        ]

    async def get_balance(self) -> AccountBalance:
        acct = self._client.get_account()
        return AccountBalance(
            equity=float(acct.equity), cash=float(acct.cash),
            buying_power=float(acct.buying_power),
        )
```

**Step 4: Create CCXTAdapter**

```python
# backend/app/execution/adapters/ccxt_adapter.py
"""CCXT broker adapter for crypto exchanges (Binance primary)."""

import logging

import ccxt.async_support as ccxt_async

from app.execution.adapters.base import (
    AccountBalance, BrokerAdapter, BrokerOrder, BrokerPosition,
    OrderSide, OrderStatus, OrderType,
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
        self, exchange_id: str = "binance",
        api_key: str = "", api_secret: str = "",
        testnet: bool = True,
    ):
        exchange_class = getattr(ccxt_async, exchange_id)
        config = {"apiKey": api_key, "secret": api_secret, "enableRateLimit": True}
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
        except Exception as e:
            logger.error("CCXT connect failed: %s", e)
            return False

    async def place_order(
        self, symbol: str, side: OrderSide, order_type: OrderType,
        quantity: float, price: float | None = None,
    ) -> BrokerOrder:
        resp = await self._exchange.create_order(
            symbol=symbol, type=order_type.value,
            side=side.value.lower(), amount=quantity, price=price,
        )
        return BrokerOrder(
            broker_order_id=str(resp["id"]), symbol=symbol, side=side,
            order_type=order_type, quantity=quantity, price=price,
            filled_quantity=float(resp.get("filled", 0)),
            average_fill_price=float(resp["average"]) if resp.get("average") else None,
            status=_CCXT_STATUS_MAP.get(resp.get("status", ""), OrderStatus.PENDING),
            broker=f"ccxt:{self._exchange_id}",
        )

    async def cancel_order(self, broker_order_id: str) -> bool:
        try:
            await self._exchange.cancel_order(broker_order_id)
            return True
        except Exception as e:
            logger.error("CCXT cancel failed: %s", e)
            return False

    async def get_order_status(self, broker_order_id: str) -> BrokerOrder:
        # CCXT requires symbol for order lookup on some exchanges
        resp = await self._exchange.fetch_order(broker_order_id)
        return BrokerOrder(
            broker_order_id=str(resp["id"]), symbol=resp["symbol"],
            side=OrderSide(resp["side"].upper()),
            order_type=OrderType(resp.get("type", "market")),
            quantity=float(resp["amount"]),
            price=float(resp["price"]) if resp.get("price") else None,
            filled_quantity=float(resp.get("filled", 0)),
            average_fill_price=float(resp["average"]) if resp.get("average") else None,
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
            for p in positions if float(p.get("contracts", 0)) != 0
        ]

    async def get_balance(self) -> AccountBalance:
        balance = await self._exchange.fetch_balance()
        total = balance.get("total", {})
        free = balance.get("free", {})
        usdt = total.get("USDT", 0)
        return AccountBalance(
            equity=float(usdt), cash=float(free.get("USDT", 0)),
            buying_power=float(free.get("USDT", 0)),
        )

    async def close(self):
        """Close the exchange connection."""
        await self._exchange.close()
```

**Step 5: Create BrokerRouter**

```python
# backend/app/execution/broker_router.py
"""Routes orders to the correct broker adapter based on symbol classification."""

import logging

from app.execution.adapters.base import (
    AccountBalance, BrokerAdapter, BrokerOrder, BrokerPosition,
    OrderSide, OrderType,
)

logger = logging.getLogger(__name__)

# Crypto symbols contain "/" with USDT, BTC, ETH quote currencies
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
        self, symbol: str, side: OrderSide, order_type: OrderType,
        quantity: float, price: float | None = None,
    ) -> BrokerOrder:
        adapter = self._resolve(symbol)
        logger.info("Routing %s %s order for %s to %s", side.value, order_type.value, symbol, adapter.name)
        return await adapter.place_order(symbol, side, order_type, quantity, price)

    async def cancel_order(self, symbol: str, broker_order_id: str) -> bool:
        adapter = self._resolve(symbol)
        return await adapter.cancel_order(broker_order_id)

    async def get_order_status(self, symbol: str, broker_order_id: str) -> BrokerOrder:
        adapter = self._resolve(symbol)
        return await adapter.get_order_status(broker_order_id)

    async def get_positions(self) -> list[BrokerPosition]:
        positions = []
        for adapter in [self._stock, self._crypto, self._paper]:
            if adapter:
                positions.extend(await adapter.get_positions())
        return positions

    async def get_balance(self) -> AccountBalance:
        # Return balance from primary adapter (stock or paper)
        adapter = self._stock or self._paper
        if adapter:
            return await adapter.get_balance()
        raise ValueError("No adapter configured for balance query")
```

**Step 6: Write tests**

```python
# backend/tests/test_broker_adapters.py
"""Tests for broker adapters and router."""

import pytest

from app.execution.adapters.base import OrderSide, OrderStatus, OrderType
from app.execution.adapters.paper import PaperAdapter
from app.execution.broker_router import BrokerRouter, is_crypto_symbol


@pytest.mark.asyncio
async def test_paper_adapter_place_order():
    adapter = PaperAdapter()
    order = await adapter.place_order("BTC/USDT", OrderSide.BUY, OrderType.LIMIT, 0.1, 50000.0)
    assert order.status == OrderStatus.FILLED
    assert order.broker == "paper"
    assert order.filled_quantity == 0.1
    assert order.average_fill_price is not None


@pytest.mark.asyncio
async def test_paper_adapter_slippage():
    adapter = PaperAdapter(slippage_pct=0.01)  # 1%
    order = await adapter.place_order("BTC/USDT", OrderSide.BUY, OrderType.LIMIT, 1.0, 100.0)
    assert order.average_fill_price == pytest.approx(101.0, rel=0.01)


@pytest.mark.asyncio
async def test_paper_adapter_cancel():
    adapter = PaperAdapter()
    order = await adapter.place_order("BTC/USDT", OrderSide.BUY, OrderType.MARKET, 0.1, 50000.0)
    cancelled = await adapter.cancel_order(order.broker_order_id)
    assert cancelled is True
    status = await adapter.get_order_status(order.broker_order_id)
    assert status.status == OrderStatus.CANCELLED


@pytest.mark.asyncio
async def test_paper_adapter_connect():
    adapter = PaperAdapter()
    assert await adapter.connect() is True


@pytest.mark.asyncio
async def test_paper_adapter_balance():
    adapter = PaperAdapter(initial_equity=25000.0)
    balance = await adapter.get_balance()
    assert balance.equity == 25000.0


def test_is_crypto_symbol():
    assert is_crypto_symbol("BTC/USDT") is True
    assert is_crypto_symbol("ETH/BTC") is True
    assert is_crypto_symbol("SPY") is False
    assert is_crypto_symbol("EUR/USD") is False
    assert is_crypto_symbol("AAPL") is False


@pytest.mark.asyncio
async def test_broker_router_paper_mode():
    paper = PaperAdapter()
    router = BrokerRouter(paper_adapter=paper)
    order = await router.place_order("BTC/USDT", OrderSide.BUY, OrderType.MARKET, 0.1, 50000.0)
    assert order.broker == "paper"


@pytest.mark.asyncio
async def test_broker_router_routes_crypto():
    paper_stock = PaperAdapter()
    paper_crypto = PaperAdapter()
    router = BrokerRouter(stock_adapter=paper_stock, crypto_adapter=paper_crypto)
    order = await router.place_order("BTC/USDT", OrderSide.BUY, OrderType.MARKET, 0.1, 50000.0)
    assert order.status == OrderStatus.FILLED


@pytest.mark.asyncio
async def test_broker_router_no_adapter_raises():
    router = BrokerRouter()
    with pytest.raises(ValueError, match="No stock adapter"):
        await router.place_order("SPY", OrderSide.BUY, OrderType.MARKET, 10, 400.0)
```

**Step 7: Add `alpaca-py` and `structlog` to pyproject.toml dependencies**

In `backend/pyproject.toml` under `[project] dependencies`, add:
```
"alpaca-py>=0.30.0",
"structlog>=24.0.0",
"slowapi>=0.1.9",
"cryptography>=43.0.0",
```

**Step 8: Run tests and lint**

```bash
cd backend && pip install alpaca-py structlog slowapi cryptography
cd backend && .venv/Scripts/python.exe -m pytest tests/test_broker_adapters.py -v
cd backend && .venv/Scripts/python.exe -m ruff check .
```

**Step 9: Commit**

```bash
git add backend/app/execution/adapters/ backend/app/execution/broker_router.py backend/tests/test_broker_adapters.py backend/pyproject.toml
git commit -m "feat(backend): broker adapter layer — ABC + Paper + Alpaca + CCXT + Router"
```

---

### Task 3: @crypto-api — Fernet Encryption + Broker API

**Files:**
- Create: `backend/app/core/encryption.py`
- Create: `backend/app/api/broker.py`
- Create: `backend/tests/test_encryption.py`
- Create: `backend/tests/test_broker_api.py`
- Modify: `backend/app/config.py` (add encryption_key)
- Modify: `backend/app/main.py` (register broker router)

**Step 1: Add SF_ENCRYPTION_KEY to config**

In `backend/app/config.py`, add:
```python
encryption_key: str = ""  # Fernet key for broker credential encryption
```

**Step 2: Create encryption module**

```python
# backend/app/core/encryption.py
"""Fernet symmetric encryption for broker API credentials."""

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


def _get_fernet() -> Fernet:
    key = settings.encryption_key
    if not key:
        raise ValueError("SF_ENCRYPTION_KEY not set — cannot encrypt/decrypt broker credentials")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_value(plaintext: str) -> bytes:
    """Encrypt a string value. Returns encrypted bytes."""
    return _get_fernet().encrypt(plaintext.encode())


def decrypt_value(ciphertext: bytes) -> str:
    """Decrypt encrypted bytes back to string."""
    try:
        return _get_fernet().decrypt(ciphertext).decode()
    except InvalidToken as e:
        raise ValueError("Failed to decrypt — wrong key or corrupted data") from e


def generate_key() -> str:
    """Generate a new Fernet encryption key."""
    return Fernet.generate_key().decode()
```

**Step 3: Create broker API endpoints**

```python
# backend/app/api/broker.py
"""Broker connection management API — CRUD for API credentials."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.core.encryption import encrypt_value, decrypt_value
from app.models.strategy import BrokerConnection

router = APIRouter(prefix="/broker", tags=["broker"])


class BrokerConnectRequest(BaseModel):
    broker: str  # "alpaca" or "binance"
    api_key: str
    api_secret: str
    is_paper: bool = True


class BrokerConnectionResponse(BaseModel):
    id: str
    broker: str
    api_key_masked: str  # ****last4
    is_paper: bool

    model_config = {"from_attributes": True}


def _mask_key(key: str) -> str:
    if len(key) <= 4:
        return "****"
    return f"****{key[-4:]}"


@router.post("", response_model=BrokerConnectionResponse, status_code=201)
async def create_broker_connection(
    body: BrokerConnectRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Store encrypted broker credentials."""
    conn = BrokerConnection(
        id=uuid.uuid4(),
        user_id=uuid.UUID(user_id),
        broker=body.broker,
        api_key_enc=encrypt_value(body.api_key),
        api_secret_enc=encrypt_value(body.api_secret),
        is_paper=body.is_paper,
    )
    db.add(conn)
    await db.commit()
    await db.refresh(conn)
    return BrokerConnectionResponse(
        id=str(conn.id), broker=conn.broker,
        api_key_masked=_mask_key(body.api_key), is_paper=conn.is_paper,
    )


@router.get("", response_model=list[BrokerConnectionResponse])
async def list_broker_connections(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List broker connections (keys masked)."""
    result = await db.execute(
        select(BrokerConnection).where(BrokerConnection.user_id == uuid.UUID(user_id))
    )
    connections = result.scalars().all()
    out = []
    for c in connections:
        try:
            raw_key = decrypt_value(c.api_key_enc)
            masked = _mask_key(raw_key)
        except Exception:
            masked = "****error"
        out.append(BrokerConnectionResponse(
            id=str(c.id), broker=c.broker, api_key_masked=masked, is_paper=c.is_paper,
        ))
    return out


@router.delete("/{connection_id}", status_code=204)
async def delete_broker_connection(
    connection_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a broker connection."""
    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.id == uuid.UUID(connection_id),
            BrokerConnection.user_id == uuid.UUID(user_id),
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Broker connection not found")
    await db.delete(conn)
    await db.commit()
```

**Step 4: Register broker router in main.py**

In `backend/app/main.py`, add:
```python
from app.api.broker import router as broker_router
app.include_router(broker_router, prefix="/api")
```

**Step 5: Write encryption tests**

```python
# backend/tests/test_encryption.py
"""Tests for Fernet encryption module."""
from unittest.mock import patch

import pytest

from app.core.encryption import decrypt_value, encrypt_value, generate_key


def test_encrypt_decrypt_roundtrip():
    key = generate_key()
    with patch("app.core.encryption.settings") as mock_settings:
        mock_settings.encryption_key = key
        plaintext = "my-secret-api-key-12345"
        encrypted = encrypt_value(plaintext)
        assert encrypted != plaintext.encode()
        decrypted = decrypt_value(encrypted)
        assert decrypted == plaintext


def test_decrypt_wrong_key_raises():
    key1 = generate_key()
    key2 = generate_key()
    with patch("app.core.encryption.settings") as mock_settings:
        mock_settings.encryption_key = key1
        encrypted = encrypt_value("secret")
    with patch("app.core.encryption.settings") as mock_settings:
        mock_settings.encryption_key = key2
        with pytest.raises(ValueError, match="Failed to decrypt"):
            decrypt_value(encrypted)


def test_no_key_raises():
    with patch("app.core.encryption.settings") as mock_settings:
        mock_settings.encryption_key = ""
        with pytest.raises(ValueError, match="SF_ENCRYPTION_KEY not set"):
            encrypt_value("test")
```

**Step 6: Write broker API tests**

```python
# backend/tests/test_broker_api.py
"""Tests for broker connection API."""
from app.core.encryption import generate_key


def test_mask_key():
    from app.api.broker import _mask_key
    assert _mask_key("abcdefgh1234") == "****1234"
    assert _mask_key("ab") == "****"
    assert _mask_key("") == "****"
```

**Step 7: Run tests and lint**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/test_encryption.py tests/test_broker_api.py -v
cd backend && .venv/Scripts/python.exe -m ruff check .
```

**Step 8: Commit**

```bash
git add backend/app/core/encryption.py backend/app/api/broker.py backend/app/config.py backend/app/main.py backend/tests/test_encryption.py backend/tests/test_broker_api.py
git commit -m "feat(backend): Fernet encryption + broker connection CRUD API"
```

---

## Wave 2: Core Wiring

### Task 4: @position-manager — DB-Backed Position Manager

**Files:**
- Rewrite: `backend/app/execution/position_manager.py`
- Rewrite: `backend/app/api/positions.py`
- Create: `backend/tests/test_position_manager_db.py`

**Step 1: Rewrite PositionManager to use DB**

Replace the entire `backend/app/execution/position_manager.py` with a class that takes an `AsyncSession`, queries the `Position` model, and creates `Trade` rows on close. Key methods:
- `async open_position(db, user_id, order, signal)` — insert Position row
- `async close_position(db, position_id, exit_price, reason)` — update Position, create Trade
- `async trail_stop(db, position_id, new_stop)` — update stop_loss
- `async list_open(db, user_id)` — query Position where is_open=True
- `async account_state(db, user_id)` — aggregate equity from trades + positions

**Step 2: Rewrite positions API to use async DB sessions**

Replace global `_pm = PositionManager()` with DB session per request. All endpoints pass `db: AsyncSession = Depends(get_db)` and call the new async methods.

**Step 3: Write tests**

Test open/close/trail/list with the in-process async SQLite test database.

**Step 4: Run all tests, lint, commit**

```bash
git commit -m "feat(backend): DB-backed PositionManager replacing in-memory"
```

---

### Task 5: @order-executor — Rewrite OrderExecutor

**Files:**
- Rewrite: `backend/app/execution/executor.py`
- Create: `backend/tests/test_order_executor.py`

**Step 1: Rewrite OrderExecutor**

Replace the current executor with a class that:
- Takes a `BrokerRouter` instance
- Creates `Order` rows in DB before sending to broker
- Updates `Order` status after broker response
- Runs pre-trade risk checks (already exist in `PreTradeChecker`)
- Returns the DB Order object

Key method: `async execute_signal(db, user_id, signal, router) -> Order`

**Step 2: Write tests using PaperAdapter**

**Step 3: Run tests, lint, commit**

```bash
git commit -m "feat(backend): rewrite OrderExecutor with BrokerRouter + DB Order persistence"
```

---

### Task 6: @candle-storage — DB-Backed Candle Storage

**Files:**
- Rewrite: `backend/app/data/storage.py`
- Modify: `backend/app/api/market.py` (wire candles endpoint to DB)
- Modify: `backend/app/api/analytics.py` (real correlation data)
- Create: `backend/tests/test_candle_storage_db.py`

**Step 1: Rewrite CandleStorage to use Candle model**

Replace in-memory dict with:
- `async save_candles(db, candles_df)` — bulk upsert into Candle table
- `async load_candles(db, symbol, timeframe, limit, since)` — query Candle table, return DataFrame

**Step 2: Wire market/candles endpoint**

Replace the empty-candles return in `market.py` with a real DB query.

**Step 3: Wire analytics/correlation to use real candle data**

Replace synthetic data in `analytics.py` correlation endpoint with real candle close prices from DB (fall back to synthetic if insufficient data).

**Step 4: Write tests, lint, commit**

```bash
git commit -m "feat(backend): DB-backed CandleStorage + real candle/correlation endpoints"
```

---

## Wave 3: Celery Tasks

### Task 7: @ingestion-tasks — Candle Ingestion + Signal Pipeline Tasks

**Files:**
- Create: `backend/app/tasks/ingest_candles.py`
- Create: `backend/app/tasks/run_pipeline.py`
- Modify: `backend/app/worker.py` (add Celery Beat schedule)
- Create: `backend/tests/test_celery_tasks.py`

**Step 1: Create ingest_candles task**

```python
# backend/app/tasks/ingest_candles.py
"""Periodic candle ingestion from exchanges."""
import logging
from app.worker import celery_app

logger = logging.getLogger(__name__)

# Symbols to ingest — configurable via Redis or DB in future
DEFAULT_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
DEFAULT_TIMEFRAMES = ["1h", "4h"]


@celery_app.task(name="ingest_candles", bind=True, max_retries=3)
def ingest_candles(self):
    """Fetch latest candles for all active symbols and store in DB."""
    import asyncio
    asyncio.run(_ingest_async())


async def _ingest_async():
    from app.core.database import async_session_factory
    from app.data.ingestion import CCXTIngestion
    from app.data.storage import CandleStorage

    ingestion = CCXTIngestion("binance")
    storage = CandleStorage()

    async with async_session_factory() as db:
        for symbol in DEFAULT_SYMBOLS:
            for timeframe in DEFAULT_TIMEFRAMES:
                try:
                    candles = ingestion.fetch_candles(symbol, timeframe, limit=50)
                    if not candles.empty:
                        await storage.save_candles(db, candles)
                        logger.info("Ingested %d candles for %s %s", len(candles), symbol, timeframe)
                except Exception as e:
                    logger.error("Ingestion failed for %s %s: %s", symbol, timeframe, e)
        await db.commit()
```

**Step 2: Create run_pipeline task**

Runs SignalPipeline for each active strategy, stores Signal in DB, publishes to Redis.

**Step 3: Configure Celery Beat in worker.py**

```python
celery_app.conf.beat_schedule = {
    "ingest-candles-1m": {
        "task": "ingest_candles",
        "schedule": 60.0,  # every 60 seconds
    },
    "run-signal-pipeline-5m": {
        "task": "run_signal_pipeline",
        "schedule": 300.0,  # every 5 minutes
    },
    "execute-pending-signals-30s": {
        "task": "execute_pending_signals",
        "schedule": 30.0,
    },
    "poll-order-status-15s": {
        "task": "poll_order_status",
        "schedule": 15.0,
    },
    "manage-positions-1m": {
        "task": "manage_positions",
        "schedule": 60.0,
    },
    "reconcile-broker-state-5m": {
        "task": "reconcile_broker_state",
        "schedule": 300.0,
    },
    "send-daily-summary": {
        "task": "send_daily_summary",
        "schedule": crontab(hour=17, minute=0),
    },
    "retrain-hmm-weekly": {
        "task": "train_hmm_regime",
        "schedule": crontab(hour=2, minute=0, day_of_week="sunday"),
    },
}
```

**Step 4: Write tests, lint, commit**

```bash
git commit -m "feat(backend): Celery Beat schedule + candle ingestion + signal pipeline tasks"
```

---

### Task 8: @execution-tasks — Order Execution + Position Management Tasks

**Files:**
- Create: `backend/app/tasks/execute_signals.py`
- Create: `backend/app/tasks/poll_orders.py`
- Create: `backend/app/tasks/manage_positions.py`
- Create: `backend/app/tasks/reconcile.py`
- Create: `backend/tests/test_execution_tasks.py`

**Step 1: execute_pending_signals task** — queries pending signals, runs pre-trade checks, places orders via BrokerRouter

**Step 2: poll_order_status task** — queries open orders, polls broker for status, updates Order table, opens Position on fill

**Step 3: manage_positions task** — trails stops, checks SL/TP, closes positions, creates Trade rows

**Step 4: reconcile_broker_state task** — syncs local DB with broker positions/orders

**Step 5: Write tests with PaperAdapter, lint, commit**

```bash
git commit -m "feat(backend): execution tasks — signal execution, order polling, position management"
```

---

### Task 9: @alert-tasks — Alert Persistence + Email Wiring

**Files:**
- Modify: `backend/app/api/alerts.py` (persist to user.alert_config)
- Create: `backend/app/tasks/send_alerts.py`
- Modify: `backend/app/tasks/hmm_train.py` (use real candle data)
- Modify: `backend/app/tasks/backtest_task.py` (persist results to DB)
- Create: `backend/tests/test_alert_tasks.py`

**Step 1: Persist alert config to User.alert_config JSON column** (replace in-memory dict)

**Step 2: Create send_alerts task** — on signal generation, check user alert config, send email if `email_on_signal=True` and `confluence >= min_confluence_alert`

**Step 3: Create send_daily_summary task** — aggregate day's trades, build email via existing `build_daily_summary_email()`, send via Resend

**Step 4: Update HMM train to use real candle data from DB** (fall back to synthetic if insufficient)

**Step 5: Update backtest_task to persist BacktestResult** + update `GET /api/backtests` to query DB

**Step 6: Write tests, lint, commit**

```bash
git commit -m "feat(backend): alert persistence, email wiring, backtest DB storage, HMM real data"
```

---

## Wave 4: Real-Time + Hardening

### Task 10: @realtime — WebSocket Broadcasting

**Files:**
- Create: `backend/app/core/redis_subscriber.py`
- Modify: `backend/app/core/pubsub.py` (add TradePublisher)
- Modify: `backend/app/ws/hub.py` (add ws_trades endpoint)
- Modify: `backend/app/main.py` (start Redis subscriber on startup)
- Create: `backend/tests/test_realtime.py`

**Step 1: Create RedisSubscriber** — background asyncio task that subscribes to `signalforge:*` Redis channels and calls `manager.broadcast()`

**Step 2: Add TradePublisher to pubsub.py** — publishes order fills and position updates to `signalforge:trades`

**Step 3: Add ws_trades endpoint** to hub.py

**Step 4: Wire Redis subscriber startup** in main.py via `@app.on_event("startup")`

**Step 5: Write tests, lint, commit**

```bash
git commit -m "feat(backend): Redis subscriber + WebSocket broadcasting for signals/prices/trades"
```

---

### Task 11: @hardening — Circuit Breaker + Rate Limiting + Logging

**Files:**
- Create: `backend/app/core/circuit_breaker.py`
- Create: `backend/app/core/logging_config.py`
- Modify: `backend/app/main.py` (add slowapi, structlog, request ID middleware, enhanced health)
- Create: `backend/tests/test_circuit_breaker.py`
- Create: `backend/tests/test_rate_limiting.py`

**Step 1: Create CircuitBreaker class**

```python
# backend/app/core/circuit_breaker.py
"""Circuit breaker for broker connections."""
import time
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Per-broker circuit breaker with Redis state persistence."""

    def __init__(self, name: str, failure_threshold: int = 5,
                 recovery_timeout: float = 30.0, window: float = 60.0):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.window = window
        self._state = CircuitState.CLOSED
        self._failures: list[float] = []
        self._last_failure_time: float = 0

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state

    def record_success(self):
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
            self._failures.clear()
            logger.info("Circuit %s CLOSED after successful call", self.name)

    def record_failure(self):
        now = time.time()
        self._failures = [t for t in self._failures if now - t < self.window]
        self._failures.append(now)
        self._last_failure_time = now
        if len(self._failures) >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning("Circuit %s OPEN — %d failures in %.0fs",
                           self.name, len(self._failures), self.window)

    def check(self) -> bool:
        """Returns True if requests are allowed."""
        return self.state != CircuitState.OPEN
```

**Step 2: Add slowapi rate limiting to main.py**

```python
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
# Apply: @limiter.limit("60/minute") on standard routes
# Apply: @limiter.limit("10/minute") on expensive routes
# Apply: @limiter.limit("5/minute") on auth routes
```

**Step 3: Configure structlog**

```python
# backend/app/core/logging_config.py
"""Structured logging configuration."""
import logging
import structlog


def configure_logging():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if True else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),
    )
```

**Step 4: Add request ID middleware and enhanced health check**

Middleware adds `X-Request-ID` header. Health check returns `{ db, redis, celery, brokers }`.

**Step 5: Add JWT secret startup check** — refuse to start if `SF_JWT_SECRET == "dev-secret-change-in-production"` and `SF_DEBUG == False`

**Step 6: Write tests, lint, commit**

```bash
git commit -m "feat(backend): circuit breaker, rate limiting, structured logging, health checks"
```

---

## Wave 5: Production + Frontend

### Task 12: @docker-prod — Production Docker Configuration

**Files:**
- Create: `backend/Dockerfile.prod` (multi-stage)
- Create: `docker-compose.prod.yml` (at project root)
- Create: `backend/.env.prod.example`

**Step 1: Multi-stage Dockerfile**

```dockerfile
# backend/Dockerfile.prod
FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml .
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

**Step 2: Production Docker Compose**

5 services: timescaledb, redis, api, worker, beat. All with health checks and `restart: unless-stopped`.

**Step 3: .env.prod.example with all required vars**

**Step 4: Commit**

```bash
git commit -m "infra: production Docker Compose + multi-stage Dockerfile"
```

---

### Task 13: @frontend-wiring — Wire Frontend to New APIs

**Files:**
- Rewrite: `frontend/src/pages/ApiKeys.tsx` (wire to /api/broker)
- Create: `frontend/src/hooks/useBrokerConnections.ts`
- Create: `frontend/src/hooks/useTradeStream.ts`
- Modify: `frontend/src/hooks/useWebSocket.ts` (export useTradeStream)
- Modify: `frontend/src/lib/ws.ts` (no changes needed, already supports arbitrary channels)
- Create: `frontend/src/tests/useBrokerConnections.test.ts`

**Step 1: Create useBrokerConnections hook**

```typescript
// frontend/src/hooks/useBrokerConnections.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface BrokerConnection {
  id: string;
  broker: string;
  api_key_masked: string;
  is_paper: boolean;
}

interface ConnectRequest {
  broker: string;
  api_key: string;
  api_secret: string;
  is_paper: boolean;
}

export function useBrokerConnections() {
  return useQuery<BrokerConnection[]>({
    queryKey: ["broker-connections"],
    queryFn: () => api.get("/broker"),
  });
}

export function useConnectBroker() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ConnectRequest) => api.post("/broker", data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["broker-connections"] }),
  });
}

export function useDisconnectBroker() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/broker/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["broker-connections"] }),
  });
}
```

**Step 2: Create useTradeStream hook**

```typescript
// frontend/src/hooks/useTradeStream.ts
import { useEffect, useState } from "react";
import { wsManager } from "@/lib/ws";
import { useAuth } from "@/lib/auth";

interface TradeUpdate {
  type: "order_filled" | "position_opened" | "position_closed";
  data: Record<string, unknown>;
}

export function useTradeStream() {
  const [updates, setUpdates] = useState<TradeUpdate[]>([]);
  const token = useAuth((s) => s.accessToken);

  useEffect(() => {
    const unsub = wsManager.subscribe("trades", (msg: TradeUpdate) => {
      setUpdates((prev) => [msg, ...prev].slice(0, 50));
    });
    wsManager.connect("trades", token ?? undefined);
    return unsub;
  }, [token]);

  return updates;
}
```

**Step 3: Rewrite ApiKeys.tsx to use real API**

Replace local state with `useBrokerConnections()`, `useConnectBroker()`, `useDisconnectBroker()`. Show real connection status, masked keys from API.

**Step 4: Write hook test**

**Step 5: Run frontend tests + lint + build**

```bash
cd frontend && npx vitest run && npm run lint && npm run build
```

**Step 6: Commit**

```bash
git commit -m "feat(frontend): wire API Keys page to broker API + useTradeStream hook"
```

---

## Final Quality Gate

After all waves are merged:

```bash
# Backend
cd backend && .venv/Scripts/python.exe -m pytest -q
cd backend && .venv/Scripts/python.exe -m ruff check .

# Frontend
cd frontend && npx vitest run
cd frontend && npm run lint
cd frontend && npm run build
```

**Expected:** All tests pass, 0 lint errors, clean build.

**Final commit:**

```bash
git commit -m "docs: update PROJECT-STATUS.md for Phase 6 completion"
```
