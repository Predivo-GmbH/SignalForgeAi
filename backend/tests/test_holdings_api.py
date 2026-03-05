"""Smoke tests for the holdings API router."""

import uuid

import pytest

from app.auth.jwt import create_access_token


@pytest.fixture
def auth_headers():
    user_id = str(uuid.uuid4())
    token = create_access_token(user_id)
    return user_id, {"Authorization": f"Bearer {token}"}


class TestManualHoldings:
    @pytest.mark.asyncio
    async def test_list_empty(self, client, auth_headers):
        _, headers = auth_headers
        resp = await client.get("/api/holdings/manual", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_add(self, client, auth_headers):
        _, headers = auth_headers
        resp = await client.post(
            "/api/holdings/manual",
            json={"symbol": "BTC", "quantity": 0.5},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["symbol"] == "BTC"
        assert data["quantity"] == 0.5

    @pytest.mark.asyncio
    async def test_add_then_list(self, client, auth_headers):
        _, headers = auth_headers
        await client.post(
            "/api/holdings/manual",
            json={"symbol": "ETH", "quantity": 10.0},
            headers=headers,
        )
        resp = await client.get("/api/holdings/manual", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["symbol"] == "ETH"

    @pytest.mark.asyncio
    async def test_delete(self, client, auth_headers):
        _, headers = auth_headers
        create = await client.post(
            "/api/holdings/manual",
            json={"symbol": "SOL", "quantity": 5.0},
            headers=headers,
        )
        holding_id = create.json()["id"]
        resp = await client.delete(
            f"/api/holdings/manual/{holding_id}", headers=headers,
        )
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client, auth_headers):
        _, headers = auth_headers
        fake_id = str(uuid.uuid4())
        resp = await client.delete(
            f"/api/holdings/manual/{fake_id}", headers=headers,
        )
        assert resp.status_code == 404


class TestCostBasis:
    @pytest.mark.asyncio
    async def test_list_empty(self, client, auth_headers):
        _, headers = auth_headers
        resp = await client.get("/api/holdings/cost-basis", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_upsert(self, client, auth_headers):
        _, headers = auth_headers
        resp = await client.put(
            "/api/holdings/cost-basis/BTC",
            json={"symbol": "BTC", "purchase_price": 60000.0},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["symbol"] == "BTC"
        assert resp.json()["purchase_price"] == 60000.0


class TestHoldingsAuth:
    @pytest.mark.asyncio
    async def test_manual_requires_auth(self, client):
        assert (await client.get("/api/holdings/manual")).status_code == 401

    @pytest.mark.asyncio
    async def test_cost_basis_requires_auth(self, client):
        assert (await client.get("/api/holdings/cost-basis")).status_code == 401
