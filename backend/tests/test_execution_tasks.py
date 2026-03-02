"""Tests for execution Celery tasks (execute_signals + poll_orders).

Tests the actual async logic (_execute_async, _poll_async) with a
mocked task_session that uses the conftest SQLite test database.
"""

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from app.models.order import Order
from app.models.position import Position
from app.models.signal import Signal
from app.models.strategy import Strategy
from tests.conftest import test_session

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
USER_ID = uuid.uuid4()
USER_ID_STR = str(USER_ID)


def _make_strategy(user_id=USER_ID, config=None):
    """Create a Strategy instance (not yet added to session)."""
    return Strategy(
        id=uuid.uuid4(),
        user_id=user_id,
        name="test-strategy",
        is_active=True,
        config=config or {},
    )


def _make_signal(strategy_id, *, direction="BUY", status="pending",
                 position_size=0.05, user_id=None):
    """Create a Signal instance (not yet added to session)."""
    return Signal(
        id=uuid.uuid4(),
        user_id=user_id or USER_ID,
        strategy_id=strategy_id,
        symbol="BTC/USDT",
        timeframe="1h",
        direction=direction,
        entry_price=50000.0,
        stop_loss=49000.0,
        take_profit_1=52000.0,
        position_size=position_size,
        confluence_score=7,
        regime="trending",
        status=status,
    )


def _make_order(signal_id=None, *, status="pending", broker="paper",
                quantity=0.05, filled_quantity=0.0):
    """Create an Order instance (not yet added to session)."""
    return Order(
        id=uuid.uuid4(),
        user_id=USER_ID,
        signal_id=signal_id,
        symbol="BTC/USDT",
        direction="BUY",
        order_type="market",
        quantity=quantity,
        price=50000.0,
        filled_quantity=filled_quantity,
        average_fill_price=None,
        stop_loss=49000.0,
        take_profit=52000.0,
        status=status,
        broker=broker,
    )


@pytest.fixture
def mock_task_session():
    """Replace app.core.database.task_session with one that uses the test DB."""
    @asynccontextmanager
    async def _mock():
        async with test_session() as session:
            yield session
    return _mock


# ===================================================================
# Task registration smoke tests
# ===================================================================


def test_execute_signals_task_registered():
    from app.tasks.execute_signals import execute_pending_signals

    assert execute_pending_signals.name == "execute_pending_signals"


def test_poll_orders_task_registered():
    from app.tasks.poll_orders import poll_order_status

    assert poll_order_status.name == "poll_order_status"


def test_manage_positions_task_registered():
    from app.tasks.manage_positions import manage_positions

    assert manage_positions.name == "manage_positions"


def test_reconcile_task_registered():
    from app.tasks.reconcile import reconcile_broker_state

    assert reconcile_broker_state.name == "reconcile_broker_state"


# ===================================================================
# execute_pending_signals — _execute_async tests
# ===================================================================


class TestExecuteSignals:
    """Tests for the _execute_async function in execute_signals task."""

    @pytest.mark.asyncio
    async def test_execute_picks_up_pending_signal(
        self, setup_db, mock_task_session
    ):
        """A pending BUY signal with a valid strategy is executed:
        signal.status becomes 'active' and an Order row is created."""
        # Arrange: insert strategy + signal
        async with test_session() as db:
            strat = _make_strategy()
            db.add(strat)
            await db.flush()

            sig = _make_signal(strat.id)
            db.add(sig)
            await db.commit()
            sig_id = sig.id

        # Act: run the task logic
        with patch(
            "app.core.database.task_session", mock_task_session
        ):
            from app.tasks.execute_signals import _execute_async
            await _execute_async()

        # Assert: signal is now active and an order was created
        async with test_session() as db:
            result = await db.execute(select(Signal).where(Signal.id == sig_id))
            updated_sig = result.scalar_one()
            assert updated_sig.status == "active"

            orders = (await db.execute(select(Order))).scalars().all()
            assert len(orders) >= 1
            order = orders[0]
            assert order.symbol == "BTC/USDT"
            assert order.direction == "BUY"
            assert order.quantity == pytest.approx(0.05)

    @pytest.mark.asyncio
    async def test_execute_skips_signal_without_strategy(
        self, setup_db, mock_task_session
    ):
        """A pending signal with strategy_id=None should not be picked up."""
        async with test_session() as db:
            sig = _make_signal(strategy_id=None)
            db.add(sig)
            await db.commit()
            sig_id = sig.id

        with patch(
            "app.core.database.task_session", mock_task_session
        ):
            from app.tasks.execute_signals import _execute_async
            await _execute_async()

        # Signal should still be pending, no orders created
        async with test_session() as db:
            result = await db.execute(select(Signal).where(Signal.id == sig_id))
            sig = result.scalar_one()
            assert sig.status == "pending"

            orders = (await db.execute(select(Order))).scalars().all()
            assert len(orders) == 0

    @pytest.mark.asyncio
    async def test_execute_skips_non_pending_signal(
        self, setup_db, mock_task_session
    ):
        """A signal with status='active' should not be picked up for execution."""
        async with test_session() as db:
            strat = _make_strategy()
            db.add(strat)
            await db.flush()

            sig = _make_signal(strat.id, status="active")
            db.add(sig)
            await db.commit()
            sig_id = sig.id

        with patch(
            "app.core.database.task_session", mock_task_session
        ):
            from app.tasks.execute_signals import _execute_async
            await _execute_async()

        # Signal should still be active (unchanged), no new orders
        async with test_session() as db:
            result = await db.execute(select(Signal).where(Signal.id == sig_id))
            sig = result.scalar_one()
            assert sig.status == "active"

            orders = (await db.execute(select(Order))).scalars().all()
            assert len(orders) == 0

    @pytest.mark.asyncio
    async def test_execute_drawdown_breaker_rejects(
        self, setup_db, mock_task_session
    ):
        """When drawdown_breaker_enabled and multiplier<=0, signal is rejected."""
        async with test_session() as db:
            strat = _make_strategy(config={
                "drawdown_breaker_enabled": True,
                "max_drawdown_pct": 0.15,
            })
            db.add(strat)
            await db.flush()

            sig = _make_signal(strat.id)
            db.add(sig)
            await db.commit()
            sig_id = sig.id

        # Mock DrawdownBreaker to return multiplier=0 (halt)
        mock_instance = MagicMock()
        mock_instance.get_sizing_multiplier = AsyncMock(return_value=0.0)
        mock_breaker_cls = MagicMock(return_value=mock_instance)

        with (
            patch("app.core.database.task_session", mock_task_session),
            patch(
                "app.execution.drawdown_breaker.DrawdownBreaker",
                mock_breaker_cls,
            ),
        ):
            from app.tasks.execute_signals import _execute_async
            await _execute_async()

        # Signal should be rejected, no orders created
        async with test_session() as db:
            result = await db.execute(select(Signal).where(Signal.id == sig_id))
            sig = result.scalar_one()
            assert sig.status == "rejected"

            orders = (await db.execute(select(Order))).scalars().all()
            assert len(orders) == 0

    @pytest.mark.asyncio
    async def test_execute_drawdown_breaker_reduces_size(
        self, setup_db, mock_task_session
    ):
        """When drawdown multiplier=0.5, order quantity is halved."""
        async with test_session() as db:
            strat = _make_strategy(config={
                "drawdown_breaker_enabled": True,
                "max_drawdown_pct": 0.15,
            })
            db.add(strat)
            await db.flush()

            sig = _make_signal(strat.id, position_size=1.0)
            db.add(sig)
            await db.commit()
            sig_id = sig.id

        # Mock DrawdownBreaker to return multiplier=0.5
        mock_instance = MagicMock()
        mock_instance.get_sizing_multiplier = AsyncMock(return_value=0.5)
        mock_breaker_cls = MagicMock(return_value=mock_instance)

        with (
            patch("app.core.database.task_session", mock_task_session),
            patch(
                "app.execution.drawdown_breaker.DrawdownBreaker",
                mock_breaker_cls,
            ),
        ):
            from app.tasks.execute_signals import _execute_async
            await _execute_async()

        # Signal should be active, order quantity should be halved (1.0 * 0.5 = 0.5)
        async with test_session() as db:
            result = await db.execute(select(Signal).where(Signal.id == sig_id))
            sig = result.scalar_one()
            assert sig.status == "active"

            orders = (await db.execute(select(Order))).scalars().all()
            assert len(orders) == 1
            assert orders[0].quantity == pytest.approx(0.5)

    @pytest.mark.asyncio
    async def test_execute_handles_executor_error(
        self, setup_db, mock_task_session
    ):
        """If OrderExecutor.execute_signal raises, signal remains pending
        and error is logged (other signals can still process)."""
        async with test_session() as db:
            strat = _make_strategy()
            db.add(strat)
            await db.flush()

            sig = _make_signal(strat.id)
            db.add(sig)
            await db.commit()
            sig_id = sig.id

        # Mock the executor to raise an exception
        with (
            patch("app.core.database.task_session", mock_task_session),
            patch(
                "app.execution.executor.OrderExecutor"
            ) as mock_executor_cls,
        ):
            mock_executor_cls.return_value.execute_signal = AsyncMock(
                side_effect=RuntimeError("Broker connection failed")
            )
            from app.tasks.execute_signals import _execute_async
            await _execute_async()

        # Signal should still be pending (the except block does not set active)
        async with test_session() as db:
            result = await db.execute(select(Signal).where(Signal.id == sig_id))
            sig = result.scalar_one()
            assert sig.status == "pending"

    @pytest.mark.asyncio
    async def test_execute_sell_signal(self, setup_db, mock_task_session):
        """A pending SELL signal is executed correctly."""
        async with test_session() as db:
            strat = _make_strategy()
            db.add(strat)
            await db.flush()

            sig = _make_signal(strat.id, direction="SELL")
            db.add(sig)
            await db.commit()
            sig_id = sig.id

        with patch(
            "app.core.database.task_session", mock_task_session
        ):
            from app.tasks.execute_signals import _execute_async
            await _execute_async()

        async with test_session() as db:
            result = await db.execute(select(Signal).where(Signal.id == sig_id))
            updated_sig = result.scalar_one()
            assert updated_sig.status == "active"

            orders = (await db.execute(select(Order))).scalars().all()
            assert len(orders) == 1
            assert orders[0].direction == "SELL"

    @pytest.mark.asyncio
    async def test_execute_uses_default_quantity_when_none(
        self, setup_db, mock_task_session
    ):
        """When signal.position_size is None, the default quantity of 0.01 is used."""
        async with test_session() as db:
            strat = _make_strategy()
            db.add(strat)
            await db.flush()

            sig = _make_signal(strat.id, position_size=None)
            db.add(sig)
            await db.commit()
            sig_id = sig.id

        with patch(
            "app.core.database.task_session", mock_task_session
        ):
            from app.tasks.execute_signals import _execute_async
            await _execute_async()

        async with test_session() as db:
            result = await db.execute(select(Signal).where(Signal.id == sig_id))
            sig = result.scalar_one()
            assert sig.status == "active"

            orders = (await db.execute(select(Order))).scalars().all()
            assert len(orders) == 1
            assert orders[0].quantity == pytest.approx(0.01)

    @pytest.mark.asyncio
    async def test_execute_skips_signal_with_orphan_strategy_id(
        self, setup_db, mock_task_session
    ):
        """Signal has a strategy_id but the strategy doesn't exist in DB -- skipped."""
        fake_strategy_id = uuid.uuid4()
        async with test_session() as db:
            sig = _make_signal(fake_strategy_id)
            db.add(sig)
            await db.commit()
            sig_id = sig.id

        with patch(
            "app.core.database.task_session", mock_task_session
        ):
            from app.tasks.execute_signals import _execute_async
            await _execute_async()

        # Signal should remain pending — the strategy was not found
        async with test_session() as db:
            result = await db.execute(select(Signal).where(Signal.id == sig_id))
            sig = result.scalar_one()
            assert sig.status == "pending"

            orders = (await db.execute(select(Order))).scalars().all()
            assert len(orders) == 0


# ===================================================================
# poll_order_status — _poll_async tests
# ===================================================================


class TestPollOrders:
    """Tests for the _poll_async function in poll_orders task."""

    @pytest.mark.asyncio
    async def test_poll_fills_paper_order(self, setup_db, mock_task_session):
        """A paper order with status='pending' is marked 'filled' after polling."""
        async with test_session() as db:
            order = _make_order(status="pending", broker="paper", quantity=0.05)
            db.add(order)
            await db.commit()
            order_id = order.id

        with (
            patch("app.core.database.task_session", mock_task_session),
            patch(
                "app.execution.position_manager.PositionManagerDB"
            ) as mock_pm,
        ):
            mock_pm.open_position = AsyncMock(return_value=Position(
                id=uuid.uuid4(),
                user_id=USER_ID,
                symbol="BTC/USDT",
                direction="BUY",
                quantity=0.05,
                entry_price=50000.0,
                broker="paper",
                is_open=True,
            ))
            from app.tasks.poll_orders import _poll_async
            await _poll_async()

        async with test_session() as db:
            result = await db.execute(select(Order).where(Order.id == order_id))
            updated_order = result.scalar_one()
            assert updated_order.status == "filled"
            assert updated_order.filled_quantity == pytest.approx(0.05)

    @pytest.mark.asyncio
    async def test_poll_creates_position_from_filled_order(
        self, setup_db, mock_task_session
    ):
        """After a paper order is filled, PositionManagerDB.open_position is called."""
        async with test_session() as db:
            order = _make_order(status="pending", broker="paper", quantity=0.1)
            db.add(order)
            await db.commit()
            order_id = order.id

        mock_position = Position(
            id=uuid.uuid4(),
            user_id=USER_ID,
            symbol="BTC/USDT",
            direction="BUY",
            quantity=0.1,
            entry_price=50000.0,
            broker="paper",
            is_open=True,
        )

        with (
            patch("app.core.database.task_session", mock_task_session),
            patch(
                "app.execution.position_manager.PositionManagerDB"
            ) as mock_pm,
        ):
            mock_pm.open_position = AsyncMock(return_value=mock_position)
            from app.tasks.poll_orders import _poll_async
            await _poll_async()

            # Verify open_position was called with correct parameters
            mock_pm.open_position.assert_called_once()
            call_kwargs = mock_pm.open_position.call_args
            assert call_kwargs.kwargs["symbol"] == "BTC/USDT"
            assert call_kwargs.kwargs["direction"] == "BUY"
            assert call_kwargs.kwargs["quantity"] == pytest.approx(0.1)
            assert call_kwargs.kwargs["broker"] == "paper"
            assert call_kwargs.kwargs["stop_loss"] == pytest.approx(49000.0)
            assert call_kwargs.kwargs["take_profit"] == pytest.approx(52000.0)
            assert call_kwargs.kwargs["order_id"] == str(order_id)

    @pytest.mark.asyncio
    async def test_poll_ignores_already_filled_orders(
        self, setup_db, mock_task_session
    ):
        """Orders with status='filled' are terminal and should not be re-processed."""
        async with test_session() as db:
            order = _make_order(
                status="filled", broker="paper",
                quantity=0.05, filled_quantity=0.05,
            )
            db.add(order)
            await db.commit()
            order_id = order.id

        with (
            patch("app.core.database.task_session", mock_task_session),
            patch(
                "app.execution.position_manager.PositionManagerDB"
            ) as mock_pm,
        ):
            mock_pm.open_position = AsyncMock()
            from app.tasks.poll_orders import _poll_async
            await _poll_async()

            # 'filled' is not in the query filter (only pending/submitted/partial)
            # so open_position should NOT have been called
            mock_pm.open_position.assert_not_called()

    @pytest.mark.asyncio
    async def test_poll_handles_error_gracefully(
        self, setup_db, mock_task_session
    ):
        """If PositionManagerDB.open_position fails for one order,
        other orders should still be processed."""
        async with test_session() as db:
            # Order 1: will fail on position creation
            order1 = _make_order(status="pending", broker="paper", quantity=0.1)
            # Order 2: should succeed
            order2 = Order(
                id=uuid.uuid4(),
                user_id=USER_ID,
                signal_id=None,
                symbol="ETH/USDT",
                direction="SELL",
                order_type="market",
                quantity=1.0,
                price=3000.0,
                filled_quantity=0.0,
                stop_loss=3100.0,
                take_profit=2800.0,
                status="pending",
                broker="paper",
            )
            db.add(order1)
            db.add(order2)
            await db.commit()
            order1_id = order1.id
            order2_id = order2.id

        call_count = 0

        async def side_effect_open_position(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("DB constraint error")
            return Position(
                id=uuid.uuid4(),
                user_id=USER_ID,
                symbol=kwargs["symbol"],
                direction=kwargs["direction"],
                quantity=kwargs["quantity"],
                entry_price=kwargs["entry_price"],
                broker=kwargs["broker"],
                is_open=True,
            )

        with (
            patch("app.core.database.task_session", mock_task_session),
            patch(
                "app.execution.position_manager.PositionManagerDB"
            ) as mock_pm,
        ):
            mock_pm.open_position = AsyncMock(side_effect=side_effect_open_position)
            from app.tasks.poll_orders import _poll_async
            await _poll_async()

        # Both orders should have been filled (paper + pending -> filled)
        async with test_session() as db:
            r1 = await db.execute(select(Order).where(Order.id == order1_id))
            r2 = await db.execute(select(Order).where(Order.id == order2_id))
            o1 = r1.scalar_one()
            o2 = r2.scalar_one()
            # Both should be filled (paper pending -> filled happens before
            # open_position, so both are marked filled regardless of the error)
            assert o1.status == "filled"
            assert o2.status == "filled"

        # open_position was attempted for both orders (2 calls total)
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_poll_resolves_strategy_from_signal(
        self, setup_db, mock_task_session
    ):
        """When an order has a signal_id, poll resolves strategy_id from that signal."""
        strat_id = uuid.uuid4()
        sig_id = uuid.uuid4()

        async with test_session() as db:
            # Create strategy
            strat = Strategy(
                id=strat_id, user_id=USER_ID,
                name="test", is_active=True, config={},
            )
            db.add(strat)
            await db.flush()

            # Create signal linked to strategy
            sig = Signal(
                id=sig_id,
                user_id=USER_ID,
                strategy_id=strat_id,
                symbol="BTC/USDT",
                timeframe="1h",
                direction="BUY",
                entry_price=50000.0,
                stop_loss=49000.0,
                take_profit_1=52000.0,
                confluence_score=7,
                regime="trending",
                status="active",
            )
            db.add(sig)
            await db.flush()

            # Create order linked to signal
            order = Order(
                id=uuid.uuid4(),
                user_id=USER_ID,
                signal_id=sig_id,
                symbol="BTC/USDT",
                direction="BUY",
                order_type="market",
                quantity=0.05,
                price=50000.0,
                filled_quantity=0.0,
                stop_loss=49000.0,
                take_profit=52000.0,
                status="pending",
                broker="paper",
            )
            db.add(order)
            await db.commit()

        mock_position = Position(
            id=uuid.uuid4(),
            user_id=USER_ID,
            symbol="BTC/USDT",
            direction="BUY",
            quantity=0.05,
            entry_price=50000.0,
            broker="paper",
            is_open=True,
        )

        with (
            patch("app.core.database.task_session", mock_task_session),
            patch(
                "app.execution.position_manager.PositionManagerDB"
            ) as mock_pm,
        ):
            mock_pm.open_position = AsyncMock(return_value=mock_position)
            from app.tasks.poll_orders import _poll_async
            await _poll_async()

            # Verify strategy_id was passed through
            mock_pm.open_position.assert_called_once()
            call_kwargs = mock_pm.open_position.call_args.kwargs
            assert call_kwargs["strategy_id"] == str(strat_id)

    @pytest.mark.asyncio
    async def test_poll_no_pending_orders_is_noop(
        self, setup_db, mock_task_session
    ):
        """When there are no pending/submitted/partial orders, nothing happens."""
        with (
            patch("app.core.database.task_session", mock_task_session),
            patch(
                "app.execution.position_manager.PositionManagerDB"
            ) as mock_pm,
        ):
            mock_pm.open_position = AsyncMock()
            from app.tasks.poll_orders import _poll_async
            await _poll_async()

            mock_pm.open_position.assert_not_called()

    @pytest.mark.asyncio
    async def test_poll_non_paper_pending_order_not_auto_filled(
        self, setup_db, mock_task_session
    ):
        """A non-paper order with status='pending' should NOT be auto-filled
        (auto-fill is only for paper broker)."""
        async with test_session() as db:
            order = _make_order(status="pending", broker="ccxt", quantity=0.05)
            db.add(order)
            await db.commit()
            order_id = order.id

        with (
            patch("app.core.database.task_session", mock_task_session),
            patch(
                "app.execution.position_manager.PositionManagerDB"
            ) as mock_pm,
        ):
            mock_pm.open_position = AsyncMock()
            from app.tasks.poll_orders import _poll_async
            await _poll_async()

        # Order should still be pending (not auto-filled since broker != paper)
        async with test_session() as db:
            result = await db.execute(select(Order).where(Order.id == order_id))
            order = result.scalar_one()
            assert order.status == "pending"

            # No position should have been created
            mock_pm.open_position.assert_not_called()
