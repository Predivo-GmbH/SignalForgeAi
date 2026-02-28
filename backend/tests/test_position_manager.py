import pytest


class TestPositionManager:
    def test_open_position(self):
        from app.execution.position_manager import Position, PositionManager

        pm = PositionManager()
        pos = pm.open_position(
            symbol="BTC/USDT",
            direction="BUY",
            entry_price=50000,
            quantity=0.01,
            stop_loss=49000,
            take_profit=52000,
            order_id="sim-123",
        )
        assert isinstance(pos, Position)
        assert pos.symbol == "BTC/USDT"
        assert pos.is_open is True

    def test_close_position_calculates_pnl_long(self):
        from app.execution.position_manager import PositionManager

        pm = PositionManager()
        pos = pm.open_position(
            symbol="BTC/USDT",
            direction="BUY",
            entry_price=50000,
            quantity=0.01,
            stop_loss=49000,
            take_profit=52000,
            order_id="sim-123",
        )
        closed = pm.close_position(pos.id, exit_price=51000, reason="take_profit")
        assert closed.is_open is False
        assert closed.pnl == pytest.approx(10.0)  # (51000-50000) * 0.01

    def test_close_position_calculates_pnl_short(self):
        from app.execution.position_manager import PositionManager

        pm = PositionManager()
        pos = pm.open_position(
            symbol="ETH/USDT",
            direction="SELL",
            entry_price=3000,
            quantity=1.0,
            stop_loss=3100,
            take_profit=2800,
            order_id="sim-456",
        )
        closed = pm.close_position(pos.id, exit_price=2900, reason="take_profit")
        assert closed.pnl == pytest.approx(100.0)  # (3000-2900) * 1.0

    def test_trail_stop_moves_favorably(self):
        from app.execution.position_manager import PositionManager

        pm = PositionManager()
        pos = pm.open_position(
            symbol="BTC/USDT",
            direction="BUY",
            entry_price=50000,
            quantity=0.01,
            stop_loss=49000,
            take_profit=52000,
            order_id="sim-123",
        )
        pm.trail_stop(pos.id, new_stop=49500)
        updated = pm.get_position(pos.id)
        assert updated.stop_loss == 49500

    def test_trail_stop_rejects_unfavorable_move_long(self):
        from app.execution.position_manager import PositionManager

        pm = PositionManager()
        pos = pm.open_position(
            symbol="BTC/USDT",
            direction="BUY",
            entry_price=50000,
            quantity=0.01,
            stop_loss=49000,
            take_profit=52000,
            order_id="sim-123",
        )
        pm.trail_stop(pos.id, new_stop=48500)  # Lower than current — rejected
        updated = pm.get_position(pos.id)
        assert updated.stop_loss == 49000  # Unchanged

    def test_list_open_positions(self):
        from app.execution.position_manager import PositionManager

        pm = PositionManager()
        pm.open_position(
            symbol="BTC/USDT",
            direction="BUY",
            entry_price=50000,
            quantity=0.01,
            stop_loss=49000,
            take_profit=52000,
            order_id="sim-1",
        )
        pm.open_position(
            symbol="ETH/USDT",
            direction="SELL",
            entry_price=3000,
            quantity=0.1,
            stop_loss=3100,
            take_profit=2800,
            order_id="sim-2",
        )
        assert len(pm.list_open()) == 2

    def test_closed_not_in_open_list(self):
        from app.execution.position_manager import PositionManager

        pm = PositionManager()
        pos = pm.open_position(
            symbol="BTC/USDT",
            direction="BUY",
            entry_price=50000,
            quantity=0.01,
            stop_loss=49000,
            take_profit=52000,
            order_id="sim-1",
        )
        pm.close_position(pos.id, exit_price=51000, reason="tp")
        assert len(pm.list_open()) == 0

    def test_account_state(self):
        from app.execution.position_manager import PositionManager

        pm = PositionManager(initial_equity=10000)
        state = pm.account_state()
        assert state.equity == 10000
        assert state.open_positions == 0
        assert state.daily_pnl == 0

    def test_account_state_with_closed_trades(self):
        from app.execution.position_manager import PositionManager

        pm = PositionManager(initial_equity=10000)
        pos = pm.open_position(
            symbol="BTC/USDT",
            direction="BUY",
            entry_price=50000,
            quantity=0.01,
            stop_loss=49000,
            take_profit=52000,
            order_id="sim-1",
        )
        pm.close_position(pos.id, exit_price=51000, reason="tp")
        state = pm.account_state()
        assert state.daily_pnl == pytest.approx(10.0)
        assert state.equity == pytest.approx(10010.0)
