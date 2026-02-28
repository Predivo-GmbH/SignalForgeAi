import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.jwt import create_access_token
from app.main import app

TEST_USER_UUID = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def auth_headers():
    token = create_access_token(TEST_USER_UUID)
    return {"Authorization": f"Bearer {token}"}


class TestPositionsAPI:
    @pytest.mark.asyncio
    async def test_list_positions_empty(self, auth_headers):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/api/positions", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_account_state(self, auth_headers):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/api/positions/account", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "equity" in data
        assert "daily_pnl" in data
        assert "open_positions" in data

    @pytest.mark.asyncio
    async def test_positions_requires_auth(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/api/positions")
        assert resp.status_code == 401


class TestEndToEndPipeline:
    def test_signal_to_execution_flow(self):
        """Signal generation -> risk check -> order execution (paper mode)."""
        import numpy as np
        import pandas as pd

        from app.engine.pipeline import SignalPipeline
        from app.execution.executor import OrderExecutor, OrderRequest
        from app.execution.risk_checks import PreTradeChecker

        # 1. Generate signal
        rng = np.random.default_rng(42)
        n = 300
        close = 100 + np.arange(n) * 0.3 + rng.normal(0, 0.5, n)
        high = close + rng.uniform(0.5, 2, n)
        low = close - rng.uniform(0.5, 2, n)
        candles = pd.DataFrame(
            {
                "open": close,
                "high": high,
                "low": low,
                "close": close,
                "volume": rng.uniform(1000, 5000, n),
            }
        )

        pipeline = SignalPipeline()
        signal = pipeline.process("TEST/USD", "1h", candles)

        # 2. If signal is actionable, run risk check + paper execution
        if signal.action in ("BUY", "SELL"):
            checker = PreTradeChecker()
            # Use a simple mock account state for the risk check
            from dataclasses import dataclass

            @dataclass
            class MockAccountState:
                equity: float = 10000.0
                daily_pnl: float = 0.0
                open_positions: int = 0
                max_positions: int = 5

            state = MockAccountState()
            risk_amount = (signal.position_size or 0) * abs(
                (signal.stop_loss or 0) - float(candles["close"].iloc[-1])
            )
            check = checker.check(state, risk_amount)

            if check.approved:
                # 3. Execute order via paper mode (legacy sync path)
                executor = OrderExecutor()
                order = OrderRequest(
                    symbol=signal.symbol,
                    direction=signal.action,
                    quantity=signal.position_size or 0.01,
                    order_type="market",
                    price=float(candles["close"].iloc[-1]),
                    stop_loss=signal.stop_loss or 0,
                    take_profit=signal.take_profit_1 or 0,
                )
                result = executor.place_order(order)
                assert result.filled

        # Pipeline runs without error regardless of action
        assert signal.action in ("BUY", "SELL", "NO_TRADE")
