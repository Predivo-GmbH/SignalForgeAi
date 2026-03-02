"""Tests for portfolio backtest runner and strategy backtest API endpoint."""

import numpy as np
import pandas as pd
import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.jwt import create_access_token
from app.main import app

TEST_USER_UUID = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def auth_headers():
    token = create_access_token(TEST_USER_UUID)
    return {"Authorization": f"Bearer {token}"}


def _make_sample_plan(symbols=None):
    """Build a plan dict matching the shape from /advisor/plan."""
    if symbols is None:
        symbols = ["BTC/USDT", "ETH/USDT"]
    return {
        "summary": "Test plan",
        "selected_cryptos": [{"symbol": s, "reason": "test"} for s in symbols],
        "strategy_config": {
            "account_equity": 10000,
            "min_confluence": 50,
            "max_risk_per_trade": 0.02,
            "max_daily_loss": 0.06,
            "atr_sl_multiplier": 2.0,
            "min_risk_reward": 1.5,
            "min_trigger_count": 1,
            "trigger_lookback_candles": 3,
            "ema_slope_threshold": 0.0005,
            "timeframes": ["1h"],
        },
        "reasoning": "Test reasoning",
        "expected_behavior": "Test",
        "warnings": [],
    }


class TestPortfolioRunner:
    def test_run_portfolio_backtest_returns_expected_shape(self):
        from app.backtest.portfolio_runner import run_portfolio_backtest

        config = {
            "symbols": ["TEST/USD"],
            "timeframes": ["1h"],
            "account_equity": 10000,
            "min_confluence": 50,
            "max_risk_per_trade": 0.02,
            "atr_sl_multiplier": 2.0,
        }
        result = run_portfolio_backtest(config, days=10, strategy_name="Test")

        assert result["strategy_name"] == "Test"
        assert result["symbols_count"] == 1
        assert result["days"] == 10
        assert "portfolio" in result
        assert "per_symbol" in result
        assert "config_summary" in result

        portfolio = result["portfolio"]
        assert "total_return" in portfolio
        assert "win_rate" in portfolio
        assert "profit_factor" in portfolio
        assert "max_drawdown" in portfolio
        assert "total_trades" in portfolio
        assert "sharpe_ratio" in portfolio
        assert "equity_curve" in portfolio

    def test_portfolio_per_symbol_results(self):
        from app.backtest.portfolio_runner import run_portfolio_backtest

        config = {
            "symbols": ["TEST/USD", "FAKE/USD"],
            "timeframes": ["1h"],
            "account_equity": 10000,
            "min_confluence": 50,
            "max_risk_per_trade": 0.02,
            "atr_sl_multiplier": 2.0,
        }
        result = run_portfolio_backtest(config, days=10)

        assert len(result["per_symbol"]) == 2
        for sym_result in result["per_symbol"]:
            assert "symbol" in sym_result
            assert "total_return" in sym_result
            assert "win_rate" in sym_result
            assert "total_trades" in sym_result

    def test_empty_symbols_returns_empty_result(self):
        from app.backtest.portfolio_runner import run_portfolio_backtest

        config = {"symbols": [], "timeframes": ["1h"], "account_equity": 10000}
        result = run_portfolio_backtest(config, days=30)

        assert result["symbols_count"] == 0
        assert result["portfolio"]["total_trades"] == 0

    def test_config_summary_reflects_params(self):
        from app.backtest.portfolio_runner import run_portfolio_backtest

        config = {
            "symbols": ["TEST/USD"],
            "timeframes": ["4h"],
            "account_equity": 5000,
            "min_confluence": 70,
            "max_risk_per_trade": 0.01,
            "atr_sl_multiplier": 2.5,
        }
        result = run_portfolio_backtest(config, days=30)

        summary = result["config_summary"]
        assert summary["min_confluence"] == 70
        assert summary["max_risk_per_trade"] == 0.01
        assert summary["atr_sl_multiplier"] == 2.5
        assert summary["timeframes"] == ["4h"]
        assert summary["account_equity"] == 5000

    def test_infer_preset_conservative(self):
        from app.backtest.portfolio_runner import run_portfolio_backtest

        config = {
            "symbols": ["TEST/USD"],
            "timeframes": ["4h"],
            "account_equity": 10000,
            "min_confluence": 70,
            "max_risk_per_trade": 0.01,
            "atr_sl_multiplier": 2.5,
        }
        result = run_portfolio_backtest(config, days=10)
        assert result["preset"] == "conservative_swing"

    def test_infer_preset_aggressive(self):
        from app.backtest.portfolio_runner import run_portfolio_backtest

        config = {
            "symbols": ["TEST/USD"],
            "timeframes": ["1h"],
            "account_equity": 10000,
            "min_confluence": 35,
            "max_risk_per_trade": 0.03,
            "atr_sl_multiplier": 1.5,
        }
        result = run_portfolio_backtest(config, days=10)
        assert result["preset"] == "aggressive_scalper"

    def test_portfolio_equity_curve_is_list_of_dicts(self):
        from app.backtest.portfolio_runner import run_portfolio_backtest

        config = {
            "symbols": ["TEST/USD"],
            "timeframes": ["1h"],
            "account_equity": 10000,
            "min_confluence": 50,
            "max_risk_per_trade": 0.02,
            "atr_sl_multiplier": 2.0,
        }
        result = run_portfolio_backtest(config, days=10)

        ec = result["portfolio"]["equity_curve"]
        assert isinstance(ec, list)
        if ec:
            assert "time" in ec[0]
            assert "value" in ec[0]


class TestStrategyBacktestAPI:
    @pytest.mark.asyncio
    async def test_strategy_backtest_with_plan(self, auth_headers):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.post(
                "/api/backtests/strategy",
                json={
                    "plan": _make_sample_plan(["BTC/USDT"]),
                    "days": 10,
                },
                headers=auth_headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "portfolio" in data
        assert "per_symbol" in data
        assert data["symbols_count"] == 1
        assert data["days"] == 10
        assert "AI Advisor" in data["strategy_name"]

    @pytest.mark.asyncio
    async def test_strategy_backtest_requires_source(self, auth_headers):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.post(
                "/api/backtests/strategy",
                json={"days": 30},
                headers=auth_headers,
            )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_strategy_backtest_empty_plan_rejected(self, auth_headers):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.post(
                "/api/backtests/strategy",
                json={
                    "plan": {"selected_cryptos": []},
                    "days": 30,
                },
                headers=auth_headers,
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_strategy_backtest_invalid_strategy_id(self, auth_headers):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.post(
                "/api/backtests/strategy",
                json={
                    "strategy_id": "00000000-0000-0000-0000-000000000099",
                    "days": 30,
                },
                headers=auth_headers,
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_strategy_backtest_conservative_preset(self, auth_headers):
        plan = _make_sample_plan(["BTC/USDT"], preset="conservative_swing")
        plan["risk_config"]["min_confluence"] = 70
        plan["risk_config"]["max_risk_per_trade"] = 0.01
        plan["risk_config"]["atr_sl_multiplier"] = 2.5

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.post(
                "/api/backtests/strategy",
                json={"plan": plan, "days": 10},
                headers=auth_headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["config_summary"]["min_confluence"] == 70
        assert data["config_summary"]["max_risk_per_trade"] == 0.01

    @pytest.mark.asyncio
    async def test_strategy_backtest_multi_symbol(self, auth_headers):
        plan = _make_sample_plan(["BTC/USDT", "ETH/USDT", "SOL/USDT"])

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.post(
                "/api/backtests/strategy",
                json={"plan": plan, "days": 10},
                headers=auth_headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["symbols_count"] == 3
        assert len(data["per_symbol"]) == 3
