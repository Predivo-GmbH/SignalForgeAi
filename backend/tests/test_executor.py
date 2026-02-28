import pytest


class TestPreTradeRiskChecks:
    def test_passes_within_limits(self):
        from app.execution.risk_checks import PreTradeChecker, AccountState

        checker = PreTradeChecker()
        state = AccountState(equity=10000, daily_pnl=0, open_positions=0, max_positions=5)
        result = checker.check(state, risk_amount=200)
        assert result.approved is True

    def test_rejects_daily_loss_exceeded(self):
        from app.execution.risk_checks import PreTradeChecker, AccountState

        checker = PreTradeChecker(max_daily_loss_pct=0.06)
        state = AccountState(equity=10000, daily_pnl=-700, open_positions=0, max_positions=5)
        result = checker.check(state, risk_amount=200)
        assert result.approved is False
        assert "daily_loss" in result.reason

    def test_rejects_max_positions(self):
        from app.execution.risk_checks import PreTradeChecker, AccountState

        checker = PreTradeChecker()
        state = AccountState(equity=10000, daily_pnl=0, open_positions=5, max_positions=5)
        result = checker.check(state, risk_amount=200)
        assert result.approved is False
        assert "max_positions" in result.reason

    def test_rejects_risk_too_large(self):
        from app.execution.risk_checks import PreTradeChecker, AccountState

        checker = PreTradeChecker(max_risk_per_trade_pct=0.02)
        state = AccountState(equity=10000, daily_pnl=0, open_positions=0, max_positions=5)
        result = checker.check(state, risk_amount=500)  # 5% > 2% limit
        assert result.approved is False
        assert "risk_per_trade" in result.reason


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
        assert result.status == "simulated"

    def test_simulated_order_generates_id(self):
        from app.execution.executor import OrderExecutor, OrderRequest

        executor = OrderExecutor()
        order = OrderRequest(
            symbol="BTC/USDT",
            direction="BUY",
            quantity=0.01,
            order_type="market",
            price=50000.0,
            stop_loss=49000.0,
            take_profit=52000.0,
        )
        result = executor.place_order(order)
        assert result.order_id is not None
        assert result.order_id.startswith("sim-")

    def test_market_order_fills_at_price(self):
        from app.execution.executor import OrderExecutor, OrderRequest

        executor = OrderExecutor()
        order = OrderRequest(
            symbol="ETH/USDT",
            direction="SELL",
            quantity=0.5,
            order_type="market",
            price=3000.0,
            stop_loss=3100.0,
            take_profit=2800.0,
        )
        result = executor.place_order(order)
        assert result.filled is True
        assert result.fill_price == 3000.0
