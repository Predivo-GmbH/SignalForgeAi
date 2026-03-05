"""Smoke tests for the simulation API router.

Verifies endpoints don't crash (no 500s, no ImportErrors).
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.auth.jwt import create_access_token


@pytest.fixture
def auth_headers():
    user_id = str(uuid.uuid4())
    token = create_access_token(user_id)
    return user_id, {"Authorization": f"Bearer {token}"}


class TestSimulationSmoke:
    @pytest.mark.asyncio
    async def test_start_no_holdings_returns_400(self, client, auth_headers):
        """Start simulation with no holdings should return 400, not 500."""
        _uid, headers = auth_headers
        # Mock the Redis-dependent holdings functions to avoid hanging
        with (
            patch(
                "app.api.holdings._fetch_exchange_holdings",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.api.holdings._fetch_manual_holdings",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.api.holdings._fetch_trading_holdings",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            resp = await client.post("/api/simulation/start", headers=headers)
        assert resp.status_code == 400
        assert "No holdings" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_active_empty(self, client, auth_headers):
        """No active simulation should return 200 null."""
        _, headers = auth_headers
        resp = await client.get("/api/simulation/active", headers=headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_latest_empty(self, client, auth_headers):
        """No simulations should return 200 null."""
        _, headers = auth_headers
        resp = await client.get("/api/simulation/latest", headers=headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_comparison_not_found(self, client, auth_headers):
        """Invalid sim ID should return 404."""
        _, headers = auth_headers
        fake_id = str(uuid.uuid4())
        resp = await client.get(
            f"/api/simulation/{fake_id}/comparison", headers=headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_stop_not_found(self, client, auth_headers):
        """Stop non-existent simulation should return 404."""
        _, headers = auth_headers
        fake_id = str(uuid.uuid4())
        resp = await client.post(
            f"/api/simulation/{fake_id}/stop", headers=headers,
        )
        assert resp.status_code == 404


class TestSimulationAuth:
    @pytest.mark.asyncio
    async def test_start_requires_auth(self, client):
        resp = await client.post("/api/simulation/start")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_active_requires_auth(self, client):
        resp = await client.get("/api/simulation/active")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_latest_requires_auth(self, client):
        resp = await client.get("/api/simulation/latest")
        assert resp.status_code == 401
