"""Tests for market data and engine status endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.jwt import create_access_token
from app.main import app

TEST_USER_UUID = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def auth_headers():
    token = create_access_token(TEST_USER_UUID)
    return {"Authorization": f"Bearer {token}"}


class TestMarketAPI:
    @pytest.mark.asyncio
    async def test_list_symbols(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/api/market/symbols")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "BTC/USDT" in data

    @pytest.mark.asyncio
    async def test_symbols_contains_forex_and_equities(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/api/market/symbols")
        data = resp.json()
        # Should have crypto, forex, and equity symbols
        assert "EUR/USD" in data
        assert "SPY" in data

    @pytest.mark.asyncio
    async def test_get_candles_returns_structure(self, auth_headers):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/api/market/candles/BTC-USDT/1h", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == "BTC/USDT"
        assert data["timeframe"] == "1h"
        assert "candles" in data
        assert "count" in data

    @pytest.mark.asyncio
    async def test_get_candles_default_limit(self, auth_headers):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/api/market/candles/ETH-USDT/5m", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == "ETH/USDT"
        assert data["timeframe"] == "5m"

    @pytest.mark.asyncio
    async def test_engine_status(self, auth_headers):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/api/engine/status", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "layers" in data
        assert "active" in data
        assert data["active"] is True
        assert isinstance(data["layers"], list)
        assert len(data["layers"]) == 6

    @pytest.mark.asyncio
    async def test_engine_status_has_supported_symbols(self, auth_headers):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/api/engine/status", headers=auth_headers)
        data = resp.json()
        assert "supported_symbols" in data
        assert "supported_timeframes" in data
        assert "BTC/USDT" in data["supported_symbols"]
        assert "1h" in data["supported_timeframes"]
