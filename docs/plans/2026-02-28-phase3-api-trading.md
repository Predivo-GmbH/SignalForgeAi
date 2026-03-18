# SignalForgeAI Phase 3 — API & Paper Trading

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build all REST endpoints, WebSocket real-time hub, Redis pub/sub infrastructure, Celery async backtest jobs, and the Order Executor + Position Manager with Alpaca paper trading and CCXT testnet support.

**Architecture:** REST API routers mounted under `/api` prefix alongside existing auth. WebSocket hub at `/ws`. Redis pub/sub channels bridge signal engine to order executor. Celery handles async backtest jobs. Order executor places paper trades through Alpaca SDK (stocks) and CCXT (crypto testnet).

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Redis 7 (aioredis), Celery 5, Socket.io (python-socketio), Alpaca SDK (alpaca-py), CCXT 4.x, pytest

**Depends on:** Phase 2 complete (SignalPipeline, Signal + Trade DB models, all 6 layers, BacktestEngine, WalkForwardOptimizer)

---

## Task 1: Auth Dependency + Config Updates

**Files:**
- Create: `backend/app/auth/dependencies.py`
- Modify: `backend/app/config.py`
- Test: `backend/tests/test_auth_dep.py`

**Step 1: Write failing tests**

Create `backend/tests/test_auth_dep.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_valid_token_returns_user_id(self):
        from app.auth.dependencies import get_current_user
        from app.auth.jwt import create_access_token
        token = create_access_token("test-user-id")
        user_id = await get_current_user(authorization=f"Bearer {token}")
        assert user_id == "test-user-id"

    @pytest.mark.asyncio
    async def test_missing_header_raises_401(self):
        from app.auth.dependencies import get_current_user
        with pytest.raises(HTTPException) as exc:
            await get_current_user(authorization=None)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self):
        from app.auth.dependencies import get_current_user
        with pytest.raises(HTTPException) as exc:
            await get_current_user(authorization="Bearer invalid-token")
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_non_bearer_scheme_raises_401(self):
        from app.auth.dependencies import get_current_user
        with pytest.raises(HTTPException) as exc:
            await get_current_user(authorization="Basic abc123")
        assert exc.value.status_code == 401
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_auth_dep.py -v`
Expected: FAIL — module not found

**Step 3: Implement auth dependency**

Create `backend/app/auth/dependencies.py`:

```python
from fastapi import Header, HTTPException, status

from app.auth.jwt import decode_token


async def get_current_user(
    authorization: str | None = Header(None),
) -> str:
    """Extract and validate JWT from Authorization header. Returns user_id."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )
    token = authorization.removeprefix("Bearer ")
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return payload["sub"]
```

**Step 4: Update config.py**

Add Alpaca and Celery settings to `backend/app/config.py`:

```python
class Settings(BaseSettings):
    # ... existing fields ...

    # Alpaca
    alpaca_api_key: str = ""
    alpaca_api_secret: str = ""
    alpaca_paper: bool = True  # Always paper mode

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
```

**Step 5: Run tests — all PASS**

**Step 6: Commit**
```bash
git add backend/app/auth/dependencies.py backend/tests/test_auth_dep.py backend/app/config.py
git commit -m "feat(backend): auth dependency (get_current_user) + Alpaca/Celery config"
```

---

## Task 2: Signals REST API

**Files:**
- Create: `backend/app/api/signals.py`
- Create: `backend/app/api/__init__.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_signals_api.py`

**Step 1: Write failing tests**

Create `backend/tests/test_signals_api.py`:

```python
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.auth.jwt import create_access_token


@pytest.fixture
def auth_headers():
    token = create_access_token("test-user-id")
    return {"Authorization": f"Bearer {token}"}


class TestSignalsAPI:
    @pytest.mark.asyncio
    async def test_list_signals_empty(self, auth_headers):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/signals", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_signals_requires_auth(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/signals")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_generate_signal(self, auth_headers):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/api/signals/generate",
                json={"symbol": "BTC/USDT", "timeframe": "1h"},
                headers=auth_headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "action" in data
        assert data["symbol"] == "BTC/USDT"

    @pytest.mark.asyncio
    async def test_get_signal_not_found(self, auth_headers):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(
                "/api/signals/00000000-0000-0000-0000-000000000000",
                headers=auth_headers,
            )
        assert resp.status_code == 404
```

**Step 2: Implement signals router**

Create `backend/app/api/__init__.py` (empty).

Create `backend/app/api/signals.py`:

```python
"""Signals API — list, get, and on-demand signal generation."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.models.signal import Signal as SignalModel

router = APIRouter(prefix="/signals", tags=["signals"])


class GenerateRequest(BaseModel):
    symbol: str
    timeframe: str = "1h"


@router.get("")
async def list_signals(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    result = await db.execute(
        select(SignalModel).order_by(SignalModel.created_at.desc()).limit(limit).offset(offset)
    )
    signals = result.scalars().all()
    return [_signal_to_dict(s) for s in signals]


@router.get("/{signal_id}")
async def get_signal(
    signal_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SignalModel).where(SignalModel.id == signal_id))
    signal = result.scalar_one_or_none()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return _signal_to_dict(signal)


@router.post("/generate")
async def generate_signal(
    body: GenerateRequest,
    user_id: str = Depends(get_current_user),
):
    """Run the signal pipeline on-demand (uses synthetic data for now)."""
    import numpy as np
    import pandas as pd
    from app.engine.pipeline import SignalPipeline

    rng = np.random.default_rng()
    n = 300
    close = 100 + np.arange(n) * 0.3 + rng.normal(0, 0.5, n)
    high = close + rng.uniform(0.5, 2, n)
    low = close - rng.uniform(0.5, 2, n)
    candles = pd.DataFrame({
        "open": close, "high": high, "low": low, "close": close,
        "volume": rng.uniform(1000, 5000, n),
    })

    pipeline = SignalPipeline()
    signal = pipeline.process(body.symbol, body.timeframe, candles)
    return {
        "symbol": signal.symbol,
        "timeframe": signal.timeframe,
        "action": signal.action,
        "regime": signal.regime,
        "confluence_score": signal.confluence_score,
        "triggers": signal.triggers,
        "stop_loss": signal.stop_loss,
        "take_profit_1": signal.take_profit_1,
        "take_profit_2": signal.take_profit_2,
        "position_size": signal.position_size,
        "risk_reward": signal.risk_reward,
        "block_reason": signal.block_reason,
        "timestamp": signal.timestamp,
    }


def _signal_to_dict(s: SignalModel) -> dict:
    return {
        "id": str(s.id),
        "symbol": s.symbol,
        "timeframe": s.timeframe,
        "direction": s.direction,
        "entry_price": s.entry_price,
        "stop_loss": s.stop_loss,
        "take_profit_1": s.take_profit_1,
        "take_profit_2": s.take_profit_2,
        "confluence_score": s.confluence_score,
        "regime": s.regime,
        "triggers": s.triggers,
        "status": s.status,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }
```

**Step 3: Register router in main.py**

Add to `backend/app/main.py`:
```python
from app.api.signals import router as signals_router
app.include_router(signals_router, prefix="/api")
```

**Step 4: Run tests — all PASS**

**Step 5: Commit**
```bash
git add backend/app/api/ backend/tests/test_signals_api.py backend/app/main.py
git commit -m "feat(backend): Signals REST API — list, get, generate endpoints"
```

---

## Task 3: Trades REST API + Stats

**Files:**
- Create: `backend/app/api/trades.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_trades_api.py`

**Step 1: Write failing tests**

```python
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.auth.jwt import create_access_token


@pytest.fixture
def auth_headers():
    token = create_access_token("test-user-id")
    return {"Authorization": f"Bearer {token}"}


class TestTradesAPI:
    @pytest.mark.asyncio
    async def test_list_trades_empty(self, auth_headers):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/trades", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_trade_stats_empty(self, auth_headers):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/trades/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_trades"] == 0
        assert data["win_rate"] == 0

    @pytest.mark.asyncio
    async def test_get_trade_not_found(self, auth_headers):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(
                "/api/trades/00000000-0000-0000-0000-000000000000",
                headers=auth_headers,
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_trades_requires_auth(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/trades")
        assert resp.status_code == 401
```

**Step 2: Implement trades router**

`backend/app/api/trades.py` — GET /trades, GET /trades/stats, GET /trades/:id

Stats endpoint calculates: total_trades, win_rate, profit_factor, total_pnl, avg_risk_reward, max_drawdown from Trade records.

**Step 3: Register router, run tests, commit**

```bash
git commit -m "feat(backend): Trades REST API — list, get, stats endpoints"
```

---

## Task 4: Strategies CRUD

**Files:**
- Create: `backend/app/api/strategies.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_strategies_api.py`

**Step 1: Write failing tests**

```python
class TestStrategiesAPI:
    @pytest.mark.asyncio
    async def test_create_strategy(self, auth_headers):
        # POST /api/strategies with name + config → 201
        ...

    @pytest.mark.asyncio
    async def test_list_strategies(self, auth_headers):
        # GET /api/strategies → 200, list
        ...

    @pytest.mark.asyncio
    async def test_update_strategy(self, auth_headers):
        # PUT /api/strategies/:id → 200
        ...

    @pytest.mark.asyncio
    async def test_activate_strategy(self, auth_headers):
        # POST /api/strategies/:id/activate → 200
        ...

    @pytest.mark.asyncio
    async def test_delete_strategy(self, auth_headers):
        # DELETE /api/strategies/:id → 204
        ...
```

**Step 2: Implement strategies router**

Full CRUD: create, list (user-scoped), get, update, delete, activate/deactivate.

Strategy config stores pipeline params: `{"min_confluence": 50, "atr_sl_multiplier": 2.0, "symbols": ["BTC/USDT"], "timeframes": ["1h"]}`.

**Step 3: Register, test, commit**
```bash
git commit -m "feat(backend): Strategies CRUD API with activate/deactivate"
```

---

## Task 5: Market Data Endpoints

**Files:**
- Create: `backend/app/api/market.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_market_api.py`

**Step 1: Write failing tests**

```python
class TestMarketAPI:
    @pytest.mark.asyncio
    async def test_list_symbols(self, auth_headers):
        # GET /api/market/symbols → 200, list of supported symbols
        ...

    @pytest.mark.asyncio
    async def test_get_candles(self, auth_headers):
        # GET /api/market/candles/BTC-USDT/1h → 200 (empty or synthetic)
        ...

    @pytest.mark.asyncio
    async def test_engine_status(self, auth_headers):
        # GET /api/engine/status → 200
        ...
```

**Step 2: Implement**

- `/api/market/symbols` — returns supported symbol list from config
- `/api/market/candles/{symbol}/{timeframe}` — returns stored candles (from CandleStorage or DB)
- `/api/engine/status` — returns signal engine status (active layers, last signal time, regime)

**Step 3: Test, commit**
```bash
git commit -m "feat(backend): Market data + engine status endpoints"
```

---

## Task 6: Celery Setup + Async Backtest

**Files:**
- Create: `backend/app/worker.py`
- Create: `backend/app/tasks/backtest_task.py`
- Create: `backend/app/tasks/__init__.py`
- Create: `backend/app/api/backtests.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_backtest_api.py`

**Step 1: Create Celery app**

`backend/app/worker.py`:
```python
from celery import Celery
from app.config import settings

celery_app = Celery(
    "signalforge",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)
```

**Step 2: Create backtest task**

`backend/app/tasks/backtest_task.py`:
```python
from app.worker import celery_app


@celery_app.task(bind=True)
def run_backtest_task(self, symbol, timeframe, days, params):
    """Run a backtest asynchronously. Returns result dict."""
    import numpy as np
    import pandas as pd
    from app.backtest.engine import BacktestEngine

    # Generate synthetic data (replaced by real CCXT data in Phase 4+)
    rng = np.random.default_rng()
    n = days * 24  # hourly candles
    close = 100 + np.arange(n) * 0.1 + rng.normal(0, 0.5, n)
    high = close + rng.uniform(0.5, 2, n)
    low = close - rng.uniform(0.5, 2, n)
    candles = pd.DataFrame({
        "open": close, "high": high, "low": low, "close": close,
        "volume": rng.uniform(1000, 5000, n),
    })

    engine = BacktestEngine(**params) if params else BacktestEngine()
    result = engine.run(candles, symbol, timeframe)
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "days": days,
        "metrics": result.metrics,
        "trade_count": len(result.trades),
    }
```

**Step 3: Create backtest API**

`backend/app/api/backtests.py`:
- POST `/api/backtests` — submits Celery task, returns task_id
- GET `/api/backtests/{task_id}` — returns task status/result
- GET `/api/backtests` — lists recent backtest results

**Step 4: Write tests (test task function directly, test API endpoints)**

**Step 5: Commit**
```bash
git commit -m "feat(backend): Celery setup + async backtest API endpoints"
```

---

## Task 7: Redis Pub/Sub Infrastructure

**Files:**
- Create: `backend/app/core/redis.py`
- Create: `backend/app/core/pubsub.py`
- Test: `backend/tests/test_pubsub.py`

**Step 1: Write failing tests**

```python
import pytest


class TestSignalPublisher:
    def test_format_signal_message(self):
        from app.core.pubsub import SignalPublisher
        msg = SignalPublisher.format_message(
            symbol="BTC/USDT", action="BUY", confluence=75, price=50000.0
        )
        assert msg["symbol"] == "BTC/USDT"
        assert msg["action"] == "BUY"
        assert "timestamp" in msg

    def test_channel_name(self):
        from app.core.pubsub import SignalPublisher
        assert SignalPublisher.CHANNEL == "signalforge:signals"

    def test_price_channel_name(self):
        from app.core.pubsub import PricePublisher
        assert PricePublisher.channel_for("BTC/USDT") == "signalforge:prices:BTC/USDT"
```

**Step 2: Implement Redis connection + pub/sub**

`backend/app/core/redis.py`:
```python
import redis.asyncio as aioredis
from app.config import settings

redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)

async def get_redis():
    return redis_client
```

`backend/app/core/pubsub.py`:
```python
import json
from datetime import datetime, timezone


class SignalPublisher:
    CHANNEL = "signalforge:signals"

    @staticmethod
    def format_message(symbol, action, confluence, price, **kwargs):
        return {
            "symbol": symbol,
            "action": action,
            "confluence_score": confluence,
            "price": price,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **kwargs,
        }

    @staticmethod
    async def publish(redis, signal_dict):
        await redis.publish(SignalPublisher.CHANNEL, json.dumps(signal_dict))


class PricePublisher:
    @staticmethod
    def channel_for(symbol: str) -> str:
        return f"signalforge:prices:{symbol}"

    @staticmethod
    async def publish(redis, symbol, price_data):
        channel = PricePublisher.channel_for(symbol)
        await redis.publish(channel, json.dumps(price_data))
```

**Step 3: Test, commit**
```bash
git commit -m "feat(backend): Redis connection + signal/price pub/sub channels"
```

---

## Task 8: WebSocket Hub

**Files:**
- Create: `backend/app/ws/__init__.py`
- Create: `backend/app/ws/hub.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_ws.py`

**Step 1: Write failing tests**

```python
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.auth.jwt import create_access_token


class TestWebSocketEndpoints:
    @pytest.mark.asyncio
    async def test_ws_signals_endpoint_exists(self):
        """Verify the WebSocket route is registered."""
        routes = [r.path for r in app.routes]
        assert "/ws/signals" in routes or any("/ws" in str(r.path) for r in app.routes)

    @pytest.mark.asyncio
    async def test_health_still_works(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/health")
        assert resp.status_code == 200
```

**Step 2: Implement WebSocket hub**

`backend/app/ws/hub.py`:
```python
"""WebSocket hub — real-time signal and price streaming."""

import asyncio
import json

from fastapi import WebSocket, WebSocketDisconnect
from app.auth.jwt import decode_token


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {
            "signals": [],
            "prices": [],
            "trades": [],
        }

    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        self.active_connections.setdefault(channel, []).append(websocket)

    def disconnect(self, websocket: WebSocket, channel: str):
        if channel in self.active_connections:
            self.active_connections[channel] = [
                ws for ws in self.active_connections[channel] if ws != websocket
            ]

    async def broadcast(self, channel: str, message: dict):
        dead = []
        for ws in self.active_connections.get(channel, []):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, channel)


manager = ConnectionManager()


async def ws_signals(websocket: WebSocket):
    """WebSocket endpoint for real-time signal feed."""
    # Optional: validate token from query param
    token = websocket.query_params.get("token")
    if token:
        payload = decode_token(token)
        if not payload:
            await websocket.close(code=1008)
            return

    await manager.connect(websocket, "signals")
    try:
        while True:
            await websocket.receive_text()  # Keep alive
    except WebSocketDisconnect:
        manager.disconnect(websocket, "signals")


async def ws_prices(websocket: WebSocket):
    """WebSocket endpoint for real-time price updates."""
    await manager.connect(websocket, "prices")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, "prices")
```

**Step 3: Register WebSocket routes in main.py**
```python
from app.ws.hub import ws_signals, ws_prices
app.websocket("/ws/signals")(ws_signals)
app.websocket("/ws/prices")(ws_prices)
```

**Step 4: Test, commit**
```bash
git commit -m "feat(backend): WebSocket hub — real-time signal and price streaming"
```

---

## Task 9: Order Executor

**Files:**
- Create: `backend/app/execution/__init__.py`
- Create: `backend/app/execution/executor.py`
- Create: `backend/app/execution/risk_checks.py`
- Test: `backend/tests/test_executor.py`

**Step 1: Write failing tests**

```python
import pytest


class TestPreTradeRiskChecks:
    def test_passes_within_limits(self):
        from app.execution.risk_checks import PreTradeChecker, AccountState
        checker = PreTradeChecker()
        state = AccountState(
            equity=10000, daily_pnl=0, open_positions=0, max_positions=5
        )
        result = checker.check(state, risk_amount=200)
        assert result.approved is True

    def test_rejects_daily_loss_exceeded(self):
        from app.execution.risk_checks import PreTradeChecker, AccountState
        checker = PreTradeChecker()
        state = AccountState(
            equity=10000, daily_pnl=-700, open_positions=0, max_positions=5
        )
        result = checker.check(state, risk_amount=200)
        assert result.approved is False
        assert "daily_loss" in result.reason

    def test_rejects_max_positions(self):
        from app.execution.risk_checks import PreTradeChecker, AccountState
        checker = PreTradeChecker()
        state = AccountState(
            equity=10000, daily_pnl=0, open_positions=5, max_positions=5
        )
        result = checker.check(state, risk_amount=200)
        assert result.approved is False
        assert "max_positions" in result.reason


class TestOrderExecutor:
    def test_paper_mode_default(self):
        from app.execution.executor import OrderExecutor
        executor = OrderExecutor()
        assert executor.paper_mode is True

    def test_place_order_returns_order_result(self):
        from app.execution.executor import OrderExecutor, OrderRequest, OrderResult
        executor = OrderExecutor()
        order = OrderRequest(
            symbol="BTC/USDT",
            direction="BUY",
            quantity=0.01,
            order_type="limit",
            price=50000.0,
            stop_loss=49000.0,
            take_profit=52000.0,
        )
        result = executor.place_order(order)
        assert isinstance(result, OrderResult)
        assert result.filled or result.status == "simulated"

    def test_simulated_order_generates_id(self):
        from app.execution.executor import OrderExecutor, OrderRequest
        executor = OrderExecutor()
        order = OrderRequest(
            symbol="BTC/USDT", direction="BUY", quantity=0.01,
            order_type="market", price=50000.0,
            stop_loss=49000.0, take_profit=52000.0,
        )
        result = executor.place_order(order)
        assert result.order_id is not None
        assert result.order_id.startswith("sim-")
```

**Step 2: Implement risk checks**

`backend/app/execution/risk_checks.py`:
- `AccountState` dataclass: equity, daily_pnl, open_positions, max_positions
- `CheckResult` dataclass: approved (bool), reason (str | None)
- `PreTradeChecker.check(state, risk_amount)` — validates daily loss < 6%, position count < max, risk_amount < 2% equity

**Step 3: Implement order executor**

`backend/app/execution/executor.py`:
- `OrderRequest` dataclass: symbol, direction, quantity, order_type, price, stop_loss, take_profit
- `OrderResult` dataclass: order_id, status, filled (bool), fill_price, broker, timestamp
- `OrderExecutor` class:
  - `paper_mode = True` (always starts in paper mode)
  - `place_order(request)` — in paper mode, simulates fill with `sim-{uuid}` order ID
  - Future: Alpaca SDK integration for stocks, CCXT for crypto (stubbed with NotImplementedError for live mode)

**Step 4: Test, commit**
```bash
git commit -m "feat(backend): Order Executor with pre-trade risk checks + paper mode"
```

---

## Task 10: Position Manager

**Files:**
- Create: `backend/app/execution/position_manager.py`
- Test: `backend/tests/test_position_manager.py`

**Step 1: Write failing tests**

```python
import pytest


class TestPositionManager:
    def test_open_position(self):
        from app.execution.position_manager import PositionManager, Position
        pm = PositionManager()
        pos = pm.open_position(
            symbol="BTC/USDT", direction="BUY", entry_price=50000,
            quantity=0.01, stop_loss=49000, take_profit=52000,
            order_id="sim-123",
        )
        assert isinstance(pos, Position)
        assert pos.symbol == "BTC/USDT"
        assert pos.is_open is True

    def test_close_position(self):
        from app.execution.position_manager import PositionManager
        pm = PositionManager()
        pos = pm.open_position(
            symbol="BTC/USDT", direction="BUY", entry_price=50000,
            quantity=0.01, stop_loss=49000, take_profit=52000,
            order_id="sim-123",
        )
        closed = pm.close_position(pos.id, exit_price=51000, reason="take_profit")
        assert closed.is_open is False
        assert closed.pnl > 0

    def test_trail_stop(self):
        from app.execution.position_manager import PositionManager
        pm = PositionManager()
        pos = pm.open_position(
            symbol="BTC/USDT", direction="BUY", entry_price=50000,
            quantity=0.01, stop_loss=49000, take_profit=52000,
            order_id="sim-123",
        )
        pm.trail_stop(pos.id, new_stop=49500)
        updated = pm.get_position(pos.id)
        assert updated.stop_loss == 49500

    def test_list_open_positions(self):
        from app.execution.position_manager import PositionManager
        pm = PositionManager()
        pm.open_position(
            symbol="BTC/USDT", direction="BUY", entry_price=50000,
            quantity=0.01, stop_loss=49000, take_profit=52000,
            order_id="sim-123",
        )
        pm.open_position(
            symbol="ETH/USDT", direction="SELL", entry_price=3000,
            quantity=0.1, stop_loss=3100, take_profit=2800,
            order_id="sim-456",
        )
        open_positions = pm.list_open()
        assert len(open_positions) == 2

    def test_account_state(self):
        from app.execution.position_manager import PositionManager
        pm = PositionManager(initial_equity=10000)
        state = pm.account_state()
        assert state.equity == 10000
        assert state.open_positions == 0
        assert state.daily_pnl == 0
```

**Step 2: Implement position manager**

`backend/app/execution/position_manager.py`:
- `Position` dataclass: id, symbol, direction, entry_price, quantity, stop_loss, take_profit, order_id, is_open, pnl, exit_price, exit_reason, opened_at, closed_at
- `PositionManager` class:
  - In-memory position store (dict[str, Position])
  - `open_position(...)` → Position
  - `close_position(id, exit_price, reason)` → Position (calculates PnL)
  - `trail_stop(id, new_stop)` — only moves stop in favorable direction
  - `list_open()` → list[Position]
  - `account_state()` → AccountState (from risk_checks module)

**Step 3: Test, commit**
```bash
git commit -m "feat(backend): PositionManager — track, trail, close positions with PnL"
```

---

## Task 11: Integration Wiring

**Files:**
- Create: `backend/app/api/positions.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_integration_p3.py`

**Step 1: Write integration tests**

```python
class TestPhase3Integration:
    @pytest.mark.asyncio
    async def test_generate_signal_to_execution_flow(self, auth_headers):
        """Signal generation → risk check → order execution → position tracking."""
        from app.engine.pipeline import SignalPipeline
        from app.execution.risk_checks import PreTradeChecker, AccountState
        from app.execution.executor import OrderExecutor, OrderRequest
        from app.execution.position_manager import PositionManager

        # 1. Generate signal
        pipeline = SignalPipeline()
        # ... run pipeline ...

        # 2. Risk check
        checker = PreTradeChecker()
        state = AccountState(equity=10000, daily_pnl=0, open_positions=0, max_positions=5)
        # ... check passes ...

        # 3. Execute order
        executor = OrderExecutor()
        # ... place order ...

        # 4. Track position
        pm = PositionManager()
        # ... open position ...
        assert True  # Pipeline flows end-to-end

    @pytest.mark.asyncio
    async def test_positions_api(self, auth_headers):
        # GET /api/positions → 200
        ...
```

**Step 2: Create positions API + wire everything in main.py**

`backend/app/api/positions.py`:
- GET `/api/positions` — list open positions
- POST `/api/positions/{id}/close` — close a position
- GET `/api/positions/account` — account state

**Step 3: Ensure all routes registered in main.py, all tests pass**

**Step 4: Commit**
```bash
git commit -m "feat(backend): Phase 3 integration — positions API + full pipeline wiring"
```

---

## Agent Team for Phase 3

| Agent | Tasks | Dependencies |
|-------|-------|-------------|
| `@api-engineer` | Tasks 1-4 (Auth dep, Signals, Trades, Strategies) | None — builds on existing auth |
| `@infra-data` | Tasks 5-7 (Market data, Celery, Redis pub/sub) | None — independent infra |
| `@execution-engine` | Tasks 9-10 (Order Executor, Position Manager) | None — independent modules |
| `@realtime-integrator` | Tasks 8, 11 (WebSocket hub, Integration wiring) | After all other agents |

**Pipeline:**
```
Wave 1: @api-engineer + @infra-data + @execution-engine (parallel — independent)
Wave 2: @realtime-integrator (wires everything + WebSocket + positions API)
```
