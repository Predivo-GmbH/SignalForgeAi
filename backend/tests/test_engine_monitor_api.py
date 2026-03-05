"""Smoke tests for the engine monitor API router."""

import uuid

import pytest

from app.auth.jwt import create_access_token


@pytest.fixture
def auth_headers():
    user_id = str(uuid.uuid4())
    token = create_access_token(user_id)
    return user_id, {"Authorization": f"Bearer {token}"}


class TestEngineMonitorSmoke:
    @pytest.mark.asyncio
    async def test_get_log_empty(self, client, auth_headers):
        _, headers = auth_headers
        resp = await client.get("/api/engine/log", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_summary_empty(self, client, auth_headers):
        _, headers = auth_headers
        resp = await client.get("/api/engine/log/summary", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_evaluations"] == 0

    @pytest.mark.asyncio
    async def test_get_runs_empty(self, client, auth_headers):
        _, headers = auth_headers
        resp = await client.get("/api/engine/log/runs", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["runs"] == []


class TestEngineMonitorAuth:
    @pytest.mark.asyncio
    async def test_log_requires_auth(self, client):
        assert (await client.get("/api/engine/log")).status_code == 401

    @pytest.mark.asyncio
    async def test_summary_requires_auth(self, client):
        assert (await client.get("/api/engine/log/summary")).status_code == 401

    @pytest.mark.asyncio
    async def test_runs_requires_auth(self, client):
        assert (await client.get("/api/engine/log/runs")).status_code == 401
