"""Tests for the DB-backed PositionManagerDB.

Uses the conftest.py test database (SQLite + aiosqlite) with auto-created
tables so we can test real async DB operations end-to-end.
"""

import uuid

import pytest
from sqlalchemy import select

from app.execution.position_manager import PositionManagerDB
from app.models.trade import Trade
from tests.conftest import test_session

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
USER_ID = str(uuid.uuid4())


# ===================================================================
# Import / smoke tests
# ===================================================================
class TestImports:
    def test_position_manager_db_importable(self):
        """Verify the DB-backed position manager can be imported."""
        assert hasattr(PositionManagerDB, "open_position")
        assert hasattr(PositionManagerDB, "close_position")
        assert hasattr(PositionManagerDB, "trail_stop")
        assert hasattr(PositionManagerDB, "update_price")
        assert hasattr(PositionManagerDB, "list_open")
        assert hasattr(PositionManagerDB, "get_position")


# ===================================================================
# PnL calculation logic (pure math, no DB)
# ===================================================================
class TestPnlCalculation:
    def test_pnl_buy(self):
        """BUY: PnL = (exit - entry) * quantity."""
        entry, exit_p, qty = 100.0, 110.0, 10.0
        assert (exit_p - entry) * qty == 100.0

    def test_pnl_sell(self):
        """SELL: PnL = (entry - exit) * quantity."""
        entry, exit_p, qty = 100.0, 90.0, 10.0
        assert (entry - exit_p) * qty == 100.0

    def test_pnl_buy_loss(self):
        entry, exit_p, qty = 50000.0, 49000.0, 0.01
        pnl = (exit_p - entry) * qty
        assert pnl == pytest.approx(-10.0)

    def test_pnl_sell_loss(self):
        entry, exit_p, qty = 3000.0, 3100.0, 1.0
        pnl = (entry - exit_p) * qty
        assert pnl == pytest.approx(-100.0)


# ===================================================================
# DB integration tests (async, uses conftest setup_db fixture)
# ===================================================================
class TestOpenPosition:
    async def test_open_creates_position(self):
        async with test_session() as db:
            pos = await PositionManagerDB.open_position(
                db,
                user_id=USER_ID,
                symbol="BTC/USDT",
                direction="BUY",
                quantity=0.01,
                entry_price=50000.0,
                stop_loss=49000.0,
                take_profit=52000.0,
                broker="paper",
            )
            await db.commit()

            assert pos.id is not None
            assert pos.symbol == "BTC/USDT"
            assert pos.direction == "BUY"
            assert pos.quantity == 0.01
            assert pos.entry_price == 50000.0
            assert pos.current_price == 50000.0
            assert pos.stop_loss == 49000.0
            assert pos.take_profit == 52000.0
            assert pos.unrealized_pnl == 0.0
            assert pos.broker == "paper"
            assert pos.is_open is True

    async def test_open_with_order_id(self):
        order_id = str(uuid.uuid4())
        async with test_session() as db:
            pos = await PositionManagerDB.open_position(
                db,
                user_id=USER_ID,
                symbol="ETH/USDT",
                direction="SELL",
                quantity=1.0,
                entry_price=3000.0,
                stop_loss=None,
                take_profit=None,
                broker="ccxt",
                order_id=order_id,
            )
            await db.commit()

            assert pos.order_id == uuid.UUID(order_id)
            assert pos.stop_loss is None
            assert pos.take_profit is None

    async def test_open_without_order_id(self):
        async with test_session() as db:
            pos = await PositionManagerDB.open_position(
                db,
                user_id=USER_ID,
                symbol="SOL/USDT",
                direction="BUY",
                quantity=10.0,
                entry_price=150.0,
                stop_loss=140.0,
                take_profit=170.0,
                broker="paper",
            )
            await db.commit()

            assert pos.order_id is None


class TestClosePosition:
    async def test_close_buy_position(self):
        async with test_session() as db:
            pos = await PositionManagerDB.open_position(
                db,
                user_id=USER_ID,
                symbol="BTC/USDT",
                direction="BUY",
                quantity=0.01,
                entry_price=50000.0,
                stop_loss=49000.0,
                take_profit=52000.0,
                broker="paper",
            )
            await db.flush()

            result = await PositionManagerDB.close_position(
                db, str(pos.id), exit_price=51000.0, reason="take_profit"
            )
            await db.commit()

            assert result["pnl"] == pytest.approx(10.0)  # (51000 - 50000) * 0.01
            assert result["reason"] == "take_profit"

            # Position should be closed now
            refreshed = await PositionManagerDB.get_position(db, str(pos.id))
            assert refreshed is not None
            assert refreshed.is_open is False
            assert refreshed.current_price == 51000.0
            assert refreshed.unrealized_pnl == 0.0
            assert refreshed.closed_at is not None

    async def test_close_sell_position(self):
        async with test_session() as db:
            pos = await PositionManagerDB.open_position(
                db,
                user_id=USER_ID,
                symbol="ETH/USDT",
                direction="SELL",
                quantity=1.0,
                entry_price=3000.0,
                stop_loss=3100.0,
                take_profit=2800.0,
                broker="paper",
            )
            await db.flush()

            result = await PositionManagerDB.close_position(
                db, str(pos.id), exit_price=2900.0, reason="take_profit"
            )
            await db.commit()

            assert result["pnl"] == pytest.approx(100.0)  # (3000 - 2900) * 1.0

    async def test_close_creates_trade_record(self):
        async with test_session() as db:
            pos = await PositionManagerDB.open_position(
                db,
                user_id=USER_ID,
                symbol="BTC/USDT",
                direction="BUY",
                quantity=0.5,
                entry_price=40000.0,
                stop_loss=39000.0,
                take_profit=42000.0,
                broker="paper",
            )
            await db.flush()

            await PositionManagerDB.close_position(
                db, str(pos.id), exit_price=41000.0, reason="manual"
            )
            await db.commit()

            # Verify Trade was created
            res = await db.execute(
                select(Trade).where(Trade.user_id == uuid.UUID(USER_ID))
            )
            trades = list(res.scalars().all())
            assert len(trades) == 1

            trade = trades[0]
            assert trade.symbol == "BTC/USDT"
            assert trade.direction == "BUY"
            assert trade.entry_price == 40000.0
            assert trade.exit_price == 41000.0
            assert trade.position_size == 0.5
            assert trade.pnl == pytest.approx(500.0)  # (41000 - 40000) * 0.5
            assert trade.exit_reason == "manual"
            assert trade.confluence_score == 0

    async def test_close_nonexistent_raises(self):
        async with test_session() as db:
            fake_id = str(uuid.uuid4())
            with pytest.raises(ValueError, match="No open position found"):
                await PositionManagerDB.close_position(
                    db, fake_id, exit_price=100.0
                )

    async def test_close_already_closed_raises(self):
        async with test_session() as db:
            pos = await PositionManagerDB.open_position(
                db,
                user_id=USER_ID,
                symbol="BTC/USDT",
                direction="BUY",
                quantity=0.01,
                entry_price=50000.0,
                stop_loss=49000.0,
                take_profit=52000.0,
                broker="paper",
            )
            await db.flush()

            await PositionManagerDB.close_position(
                db, str(pos.id), exit_price=51000.0
            )
            await db.flush()

            # Second close should fail
            with pytest.raises(ValueError, match="No open position found"):
                await PositionManagerDB.close_position(
                    db, str(pos.id), exit_price=52000.0
                )


class TestTrailStop:
    async def test_trail_stop_updates(self):
        async with test_session() as db:
            pos = await PositionManagerDB.open_position(
                db,
                user_id=USER_ID,
                symbol="BTC/USDT",
                direction="BUY",
                quantity=0.01,
                entry_price=50000.0,
                stop_loss=49000.0,
                take_profit=52000.0,
                broker="paper",
            )
            await db.flush()

            await PositionManagerDB.trail_stop(db, str(pos.id), new_stop=49500.0)
            await db.flush()

            refreshed = await PositionManagerDB.get_position(db, str(pos.id))
            assert refreshed is not None
            assert refreshed.stop_loss == 49500.0

    async def test_trail_stop_closed_position_ignored(self):
        """Trail stop on a closed position is a no-op (not found as open)."""
        async with test_session() as db:
            pos = await PositionManagerDB.open_position(
                db,
                user_id=USER_ID,
                symbol="BTC/USDT",
                direction="BUY",
                quantity=0.01,
                entry_price=50000.0,
                stop_loss=49000.0,
                take_profit=52000.0,
                broker="paper",
            )
            await db.flush()

            await PositionManagerDB.close_position(db, str(pos.id), exit_price=51000.0)
            await db.flush()

            # trail_stop on closed position — should silently do nothing
            await PositionManagerDB.trail_stop(db, str(pos.id), new_stop=50000.0)
            await db.commit()


class TestUpdatePrice:
    async def test_update_price_buy(self):
        async with test_session() as db:
            pos = await PositionManagerDB.open_position(
                db,
                user_id=USER_ID,
                symbol="BTC/USDT",
                direction="BUY",
                quantity=0.01,
                entry_price=50000.0,
                stop_loss=49000.0,
                take_profit=52000.0,
                broker="paper",
            )
            await db.flush()

            await PositionManagerDB.update_price(db, str(pos.id), current_price=51000.0)
            await db.flush()

            refreshed = await PositionManagerDB.get_position(db, str(pos.id))
            assert refreshed is not None
            assert refreshed.current_price == 51000.0
            assert refreshed.unrealized_pnl == pytest.approx(10.0)  # (51000 - 50000) * 0.01

    async def test_update_price_sell(self):
        async with test_session() as db:
            pos = await PositionManagerDB.open_position(
                db,
                user_id=USER_ID,
                symbol="ETH/USDT",
                direction="SELL",
                quantity=1.0,
                entry_price=3000.0,
                stop_loss=3100.0,
                take_profit=2800.0,
                broker="paper",
            )
            await db.flush()

            await PositionManagerDB.update_price(db, str(pos.id), current_price=2900.0)
            await db.flush()

            refreshed = await PositionManagerDB.get_position(db, str(pos.id))
            assert refreshed is not None
            assert refreshed.current_price == 2900.0
            assert refreshed.unrealized_pnl == pytest.approx(100.0)  # (3000 - 2900) * 1.0


class TestListOpen:
    async def test_list_open_returns_only_open(self):
        async with test_session() as db:
            # Open two positions
            pos1 = await PositionManagerDB.open_position(
                db,
                user_id=USER_ID,
                symbol="BTC/USDT",
                direction="BUY",
                quantity=0.01,
                entry_price=50000.0,
                stop_loss=49000.0,
                take_profit=52000.0,
                broker="paper",
            )
            await PositionManagerDB.open_position(
                db,
                user_id=USER_ID,
                symbol="ETH/USDT",
                direction="SELL",
                quantity=1.0,
                entry_price=3000.0,
                stop_loss=3100.0,
                take_profit=2800.0,
                broker="paper",
            )
            await db.flush()

            open_positions = await PositionManagerDB.list_open(db, USER_ID)
            assert len(open_positions) == 2

            # Close one
            await PositionManagerDB.close_position(db, str(pos1.id), exit_price=51000.0)
            await db.flush()

            open_positions = await PositionManagerDB.list_open(db, USER_ID)
            assert len(open_positions) == 1
            assert open_positions[0].symbol == "ETH/USDT"

    async def test_list_open_empty(self):
        async with test_session() as db:
            open_positions = await PositionManagerDB.list_open(db, USER_ID)
            assert open_positions == []

    async def test_list_open_filters_by_user(self):
        other_user = str(uuid.uuid4())
        async with test_session() as db:
            await PositionManagerDB.open_position(
                db,
                user_id=USER_ID,
                symbol="BTC/USDT",
                direction="BUY",
                quantity=0.01,
                entry_price=50000.0,
                stop_loss=49000.0,
                take_profit=52000.0,
                broker="paper",
            )
            await PositionManagerDB.open_position(
                db,
                user_id=other_user,
                symbol="ETH/USDT",
                direction="BUY",
                quantity=1.0,
                entry_price=3000.0,
                stop_loss=2900.0,
                take_profit=3200.0,
                broker="paper",
            )
            await db.flush()

            user1_positions = await PositionManagerDB.list_open(db, USER_ID)
            assert len(user1_positions) == 1
            assert user1_positions[0].symbol == "BTC/USDT"

            user2_positions = await PositionManagerDB.list_open(db, other_user)
            assert len(user2_positions) == 1
            assert user2_positions[0].symbol == "ETH/USDT"


class TestGetPosition:
    async def test_get_existing(self):
        async with test_session() as db:
            pos = await PositionManagerDB.open_position(
                db,
                user_id=USER_ID,
                symbol="BTC/USDT",
                direction="BUY",
                quantity=0.01,
                entry_price=50000.0,
                stop_loss=49000.0,
                take_profit=52000.0,
                broker="paper",
            )
            await db.flush()

            found = await PositionManagerDB.get_position(db, str(pos.id))
            assert found is not None
            assert found.id == pos.id

    async def test_get_nonexistent(self):
        async with test_session() as db:
            found = await PositionManagerDB.get_position(db, str(uuid.uuid4()))
            assert found is None
