"""Tests for the rewritten OrderExecutor with BrokerRouter integration."""

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.execution.adapters.base import OrderSide, OrderStatus, OrderType
from app.execution.adapters.paper import PaperAdapter
from app.execution.broker_router import BrokerRouter

# ---------------------------------------------------------------------------
# Sync / import tests
# ---------------------------------------------------------------------------


class TestOrderExecutorImports:
    def test_order_executor_imports(self):
        """Verify executor can be imported with new interface."""
        from app.execution.executor import OrderExecutor

        paper = PaperAdapter()
        router = BrokerRouter(paper_adapter=paper)
        executor = OrderExecutor(broker_router=router)
        assert executor is not None

    def test_legacy_classes_still_importable(self):
        """OrderRequest and OrderResult must remain importable for backward compat."""
        from app.execution.executor import OrderRequest, OrderResult

        req = OrderRequest(
            symbol="BTC/USDT",
            direction="BUY",
            quantity=0.1,
            order_type="market",
            price=50000.0,
            stop_loss=49000.0,
            take_profit=52000.0,
        )
        assert req.symbol == "BTC/USDT"
        assert OrderResult is not None

    def test_legacy_paper_mode_default(self):
        """Constructing without a router enables legacy paper_mode."""
        from app.execution.executor import OrderExecutor

        executor = OrderExecutor()
        assert executor.paper_mode is True

    def test_legacy_place_order_works(self):
        """Legacy synchronous paper-mode place_order still works."""
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
        assert result.status == "simulated"
        assert result.filled is True
        assert result.fill_price == 50000.0
        assert result.order_id.startswith("sim-")


# ---------------------------------------------------------------------------
# Async / BrokerRouter integration tests
# ---------------------------------------------------------------------------


class TestOrderExecutorAsync:
    @pytest.mark.asyncio
    async def test_router_place_order_via_paper(self):
        """BrokerRouter correctly routes through PaperAdapter."""
        paper = PaperAdapter()
        router = BrokerRouter(paper_adapter=paper)
        result = await router.place_order(
            "BTC/USDT", OrderSide.BUY, OrderType.MARKET, 0.1, 50000.0
        )
        assert result.status == OrderStatus.FILLED
        assert result.broker == "paper"
        assert result.filled_quantity == 0.1

    @pytest.mark.asyncio
    async def test_execute_signal_creates_order_in_db(self, setup_db):
        """execute_signal persists an Order row and fills it via paper adapter."""
        from app.execution.executor import OrderExecutor
        from app.models.order import Order
        from tests.conftest import test_session

        paper = PaperAdapter()
        router = BrokerRouter(paper_adapter=paper)
        executor = OrderExecutor(broker_router=router)

        user_id = str(uuid4())
        signal = {
            "symbol": "BTC/USDT",
            "direction": "BUY",
            "quantity": 0.05,
            "price": 60000.0,
            "order_type": "market",
            "signal_id": None,
            "stop_loss": 58000.0,
            "take_profit": 65000.0,
        }

        async with test_session() as db:
            order = await executor.execute_signal(db, user_id, signal)
            await db.commit()

            # Verify returned object
            assert order.symbol == "BTC/USDT"
            assert order.direction == "BUY"
            assert order.status == "filled"
            assert order.broker == "paper"
            assert order.filled_quantity == 0.05
            assert order.average_fill_price is not None
            assert order.error_message is None

            # Verify it was actually persisted
            result = await db.execute(select(Order).where(Order.id == order.id))
            persisted = result.scalar_one()
            assert persisted.status == "filled"
            assert persisted.broker == "paper"

    @pytest.mark.asyncio
    async def test_execute_signal_sell_direction(self, setup_db):
        """execute_signal correctly maps SELL direction."""
        from app.execution.executor import OrderExecutor
        from tests.conftest import test_session

        paper = PaperAdapter()
        router = BrokerRouter(paper_adapter=paper)
        executor = OrderExecutor(broker_router=router)

        signal = {
            "symbol": "ETH/USDT",
            "direction": "SELL",
            "quantity": 1.0,
            "price": 3000.0,
            "order_type": "market",
        }

        async with test_session() as db:
            order = await executor.execute_signal(db, str(uuid4()), signal)
            await db.commit()

            assert order.direction == "SELL"
            assert order.status == "filled"
            assert order.filled_quantity == 1.0

    @pytest.mark.asyncio
    async def test_execute_signal_with_signal_id(self, setup_db):
        """execute_signal stores signal_id when provided."""
        from app.execution.executor import OrderExecutor
        from tests.conftest import test_session

        paper = PaperAdapter()
        router = BrokerRouter(paper_adapter=paper)
        executor = OrderExecutor(broker_router=router)

        sig_id = str(uuid4())
        signal = {
            "symbol": "AAPL",
            "direction": "BUY",
            "quantity": 10,
            "price": 175.0,
            "order_type": "market",
            "signal_id": sig_id,
        }

        async with test_session() as db:
            order = await executor.execute_signal(db, str(uuid4()), signal)
            await db.commit()

            assert str(order.signal_id) == sig_id

    @pytest.mark.asyncio
    async def test_execute_signal_handles_broker_error(self, setup_db):
        """If the broker raises, the Order is marked rejected with error_message."""
        from app.execution.executor import OrderExecutor
        from tests.conftest import test_session

        # Router with no adapters at all -> will raise ValueError
        router = BrokerRouter()
        executor = OrderExecutor(broker_router=router)

        signal = {
            "symbol": "BTC/USDT",
            "direction": "BUY",
            "quantity": 0.1,
            "price": 50000.0,
            "order_type": "market",
        }

        async with test_session() as db:
            order = await executor.execute_signal(db, str(uuid4()), signal)
            await db.commit()

            assert order.status == "rejected"
            assert order.error_message is not None
            assert "No" in order.error_message or "adapter" in order.error_message.lower()

    @pytest.mark.asyncio
    async def test_execute_signal_requires_router(self):
        """execute_signal raises RuntimeError when no router is configured."""
        from app.execution.executor import OrderExecutor
        from tests.conftest import test_session

        executor = OrderExecutor()  # no router

        async with test_session() as db:
            with pytest.raises(RuntimeError, match="BrokerRouter"):
                await executor.execute_signal(db, str(uuid4()), {"symbol": "X", "direction": "BUY"})

    @pytest.mark.asyncio
    async def test_execute_signal_defaults(self, setup_db):
        """execute_signal uses sensible defaults for missing optional fields."""
        from app.execution.executor import OrderExecutor
        from tests.conftest import test_session

        paper = PaperAdapter()
        router = BrokerRouter(paper_adapter=paper)
        executor = OrderExecutor(broker_router=router)

        # Minimal signal -- only required fields
        signal = {
            "symbol": "TSLA",
            "direction": "BUY",
        }

        async with test_session() as db:
            order = await executor.execute_signal(db, str(uuid4()), signal)
            await db.commit()

            assert order.quantity == 0.0
            assert order.price is None
            assert order.order_type == "market"
            assert order.stop_loss is None
            assert order.take_profit is None
            assert order.signal_id is None
