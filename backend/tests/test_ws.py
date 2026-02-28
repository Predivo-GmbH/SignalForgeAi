import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.jwt import create_access_token
from app.main import app


class TestWebSocketSetup:
    @pytest.mark.asyncio
    async def test_health_still_works(self):
        """Verify adding WS routes doesn't break REST."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/health")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_ws_routes_registered(self):
        """Verify WebSocket routes exist."""
        route_paths = [getattr(r, "path", None) for r in app.routes]
        assert "/ws/signals" in route_paths
        assert "/ws/prices" in route_paths


class TestConnectionManager:
    def test_manager_has_channels(self):
        from app.ws.hub import manager

        assert "signals" in manager.active_connections
        assert "prices" in manager.active_connections

    @pytest.mark.asyncio
    async def test_broadcast_handles_empty(self):
        from app.ws.hub import manager

        # Should not raise even with no connections
        await manager.broadcast("signals", {"test": True})
