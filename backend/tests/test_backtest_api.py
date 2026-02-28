"""Tests for Celery backtest task and backtest API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


class TestBacktestTask:
    def test_run_backtest_task_returns_result(self):
        from app.tasks.backtest_task import run_backtest_task

        result = run_backtest_task("BTC/USDT", "1h", 30)
        assert "metrics" in result
        assert "trade_count" in result
        assert result["symbol"] == "BTC/USDT"
        assert result["timeframe"] == "1h"
        assert result["days"] == 30
        assert isinstance(result["metrics"], dict)

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
        assert "metrics" in result
        assert result["trade_count"] >= 0

    def test_backtest_metrics_have_expected_keys(self):
        from app.tasks.backtest_task import run_backtest_task

        result = run_backtest_task("BTC/USDT", "1h", 10)
        metrics = result["metrics"]
        expected_keys = [
            "total_trades",
            "win_rate",
            "profit_factor",
            "total_return_pct",
            "max_drawdown_pct",
            "sharpe_ratio",
            "avg_risk_reward",
        ]
        for key in expected_keys:
            assert key in metrics, f"Missing metric key: {key}"


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
    async def test_run_backtest_endpoint(self):
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
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == "BTC/USDT"
        assert "metrics" in data
        assert "trade_count" in data

    @pytest.mark.asyncio
    async def test_run_backtest_with_params(self):
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
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["timeframe"] == "4h"

    @pytest.mark.asyncio
    async def test_list_backtests_endpoint(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/api/backtests")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
