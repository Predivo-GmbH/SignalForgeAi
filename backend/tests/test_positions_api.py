"""Smoke tests for the positions API router."""

import uuid

import pytest

from app.auth.jwt import create_access_token


@pytest.fixture
def auth_headers():
    user_id = str(uuid.uuid4())
    token = create_access_token(user_id)
    return user_id, {"Authorization": f"Bearer {token}"}


class TestPositionsSmoke:
    @pytest.mark.asyncio
    async def test_list_empty(self, client, auth_headers):
        _, headers = auth_headers
        resp = await client.get("/api/positions", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_close_not_found(self, client, auth_headers):
        _, headers = auth_headers
        fake_id = str(uuid.uuid4())
        resp = await client.post(
            f"/api/positions/{fake_id}/close",
            json={"exit_price": 100.0},
            headers=headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_account_state(self, client, auth_headers):
        _, headers = auth_headers
        resp = await client.get("/api/positions/account", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "equity" in data
        assert "daily_pnl" in data


class TestPositionsAuth:
    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client):
        assert (await client.get("/api/positions")).status_code == 401

    @pytest.mark.asyncio
    async def test_account_requires_auth(self, client):
        assert (await client.get("/api/positions/account")).status_code == 401
