import pytest


@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code in (200, 503)
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert data["service"] == "SignalForge"
    # Enhanced health check always includes component statuses
    assert "db" in data
    assert "redis" in data
