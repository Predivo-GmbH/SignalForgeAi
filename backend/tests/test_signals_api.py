"""Tests for the Signals REST API."""

import uuid

import pytest

from app.auth.jwt import create_access_token


@pytest.fixture
def auth_headers():
    """Return valid auth headers for a test user."""
    user_id = str(uuid.uuid4())
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


class TestGenerateSignal:
    @pytest.mark.asyncio
    async def test_generate_signal_returns_200(self, client, auth_headers):
        response = await client.post(
            "/api/signals/generate",
            json={"symbol": "BTC/USDT", "timeframe": "1h"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "action" in data
        assert data["action"] in ("BUY", "SELL", "NO_TRADE")
        assert data["symbol"] == "BTC/USDT"
        assert data["timeframe"] == "1h"

    @pytest.mark.asyncio
    async def test_generate_requires_auth(self, client):
        response = await client.post(
            "/api/signals/generate",
            json={"symbol": "BTC/USDT", "timeframe": "1h"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_generate_with_invalid_token(self, client):
        response = await client.post(
            "/api/signals/generate",
            json={"symbol": "BTC/USDT", "timeframe": "1h"},
            headers={"Authorization": "Bearer bad-token"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_generate_default_symbol_and_timeframe(self, client, auth_headers):
        """If no body is given, defaults should be used."""
        response = await client.post(
            "/api/signals/generate",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "BTC/USDT"
        assert data["timeframe"] == "1h"


class TestListSignals:
    @pytest.mark.asyncio
    async def test_list_signals_empty(self, client, auth_headers):
        response = await client.get("/api/signals", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["signals"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_signals_requires_auth(self, client):
        response = await client.get("/api/signals")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_signals_pagination(self, client, auth_headers):
        response = await client.get(
            "/api/signals", params={"limit": 5, "offset": 0}, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "signals" in data
        assert "total" in data


class TestGetSignal:
    @pytest.mark.asyncio
    async def test_get_signal_not_found(self, client, auth_headers):
        fake_id = str(uuid.uuid4())
        response = await client.get(f"/api/signals/{fake_id}", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_signal_requires_auth(self, client):
        fake_id = str(uuid.uuid4())
        response = await client.get(f"/api/signals/{fake_id}")
        assert response.status_code == 401
