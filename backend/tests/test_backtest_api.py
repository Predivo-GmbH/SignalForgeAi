"""Tests for Celery backtest task and backtest API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.jwt import create_access_token
from app.main import app

TEST_USER_UUID = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def auth_headers():
    token = create_access_token(TEST_USER_UUID)
    return {"Authorization": f"Bearer {token}"}


class TestBacktestTask:
    def test_run_backtest_task_returns_result(self):
        from app.tasks.backtest_task import run_backtest_task

        result = run_backtest_task("BTC/USDT", "1h", 30)
        assert result["symbol"] == "BTC/USDT"
        assert result["timeframe"] == "1h"
        assert result["days"] == 30
        assert "total_trades" in result
        assert "total_return" in result
        assert "win_rate" in result
        assert "equity_curve" in result

    def test_backtest_with_custom_params(self):
        from app.tasks.backtest_task import run_backtest_task

        result = run_backtest_task("ETH/USDT", "4h", 7, {"min_confluence": 40})
        assert result["timeframe"] == "4h"
        assert result["symbol"] == "ETH/USDT"
        assert result["days"] == 7

    def test_backtest_generates_enough_bars(self):
        from app.tasks.backtest_task import run_backtest_task

        # Even with 1 day, should still produce a result (min 300 bars)
        result = run_backtest_task("SOL/USDT", "1h", 1)
        assert "total_trades" in result
        assert result["total_trades"] >= 0

    def test_backtest_result_has_expected_keys(self):
        from app.tasks.backtest_task import run_backtest_task

        result = run_backtest_task("BTC/USDT", "1h", 10)
        expected_keys = [
            "total_trades",
            "win_rate",
            "profit_factor",
            "total_return",
            "max_drawdown",
            "sharpe_ratio",
        ]
        for key in expected_keys:
            assert key in result, f"Missing result key: {key}"


class TestCeleryConfig:
    def test_celery_app_exists(self):
        from app.worker import celery_app

        assert celery_app is not None
        assert celery_app.main == "signalforge"

    def test_celery_serializer_config(self):
        from app.worker import celery_app

        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.result_serializer == "json"
        assert "json" in celery_app.conf.accept_content

    def test_celery_broker_url_configured(self):
        from app.config import settings

        assert settings.celery_broker_url.startswith("redis://")

    def test_celery_result_backend_configured(self):
        from app.config import settings

        assert settings.celery_result_backend.startswith("redis://")


class TestBacktestAPI:
    @pytest.mark.asyncio
    async def test_run_backtest_endpoint(self, auth_headers):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.post(
                "/api/backtests",
                json={
                    "symbol": "BTC/USDT",
                    "timeframe": "1h",
                    "days": 10,
                },
                headers=auth_headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == "BTC/USDT"
        assert "total_return" in data
        assert "total_trades" in data

    @pytest.mark.asyncio
    async def test_run_backtest_with_params(self, auth_headers):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.post(
                "/api/backtests",
                json={
                    "symbol": "ETH/USDT",
                    "timeframe": "4h",
                    "days": 7,
                    "params": {"min_confluence": 40},
                },
                headers=auth_headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["timeframe"] == "4h"

    @pytest.mark.asyncio
    async def test_list_backtests_endpoint(self, auth_headers):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/api/backtests", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
