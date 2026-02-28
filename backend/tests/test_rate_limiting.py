"""Tests for rate limiting and health check."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "db" in data


class TestRequestID:
    @pytest.mark.asyncio
    async def test_request_id_header(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/health")
        assert "x-request-id" in resp.headers
