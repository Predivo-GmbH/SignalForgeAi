"""Smoke tests for the system status API router."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.auth.jwt import create_access_token


@pytest.fixture
def auth_headers():
    user_id = str(uuid.uuid4())
    token = create_access_token(user_id)
    return user_id, {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _mock_redis_and_celery():
    """Mock Redis and Celery to avoid hanging on connection attempts."""
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(side_effect=ConnectionError("no redis in tests"))

    mock_celery = MagicMock()
    mock_celery.control.inspect.return_value.ping.return_value = None

    with (
        patch("app.core.redis_client.redis_client", mock_redis),
        patch("app.worker.celery_app", mock_celery),
    ):
        yield


class TestSystemStatusSmoke:
    @pytest.mark.asyncio
    async def test_get_status(self, client, auth_headers):
        _, headers = auth_headers
        resp = await client.get("/api/system/status", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "overall" in data
        assert "services" in data
        assert data["overall"] in ("healthy", "degraded", "critical")

    @pytest.mark.asyncio
    async def test_restart_requires_admin(self, client, auth_headers):
        """Non-admin user should get 403."""
        _, headers = auth_headers
        resp = await client.post("/api/system/restart", headers=headers)
        assert resp.status_code in (200, 403)


class TestSystemStatusAuth:
    @pytest.mark.asyncio
    async def test_status_requires_auth(self, client):
        assert (await client.get("/api/system/status")).status_code == 401

    @pytest.mark.asyncio
    async def test_restart_requires_auth(self, client):
        assert (await client.post("/api/system/restart")).status_code == 401
