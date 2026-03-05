"""Tests for the Strategies CRUD API."""

import uuid

import pytest

from app.auth.jwt import create_access_token


@pytest.fixture
async def test_user(client):
    """Create a test user via registration and return (user_id, headers)."""
    reg = await client.post("/api/auth/register", json={
        "email": f"strat-{uuid.uuid4().hex[:8]}@test.com",
        "password": "Testpass123",
    })
    data = reg.json()
    from app.auth.jwt import decode_token
    payload = decode_token(data["access_token"])
    user_id = payload["sub"]
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    return user_id, headers


@pytest.fixture
def auth_headers():
    """Return valid auth headers for a random user (no DB user)."""
    user_id = str(uuid.uuid4())
    token = create_access_token(user_id)
    return user_id, {"Authorization": f"Bearer {token}"}


class TestCreateStrategy:
    @pytest.mark.asyncio
    async def test_create_strategy(self, client, test_user):
        _user_id, headers = test_user
        response = await client.post(
            "/api/strategies",
            json={"name": "EMA Crossover", "config": {"ema_fast": 9, "ema_slow": 21}},
            headers=headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "EMA Crossover"
        assert data["config"] == {"ema_fast": 9, "ema_slow": 21}
        assert data["is_active"] is False
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_requires_auth(self, client):
        response = await client.post(
            "/api/strategies",
            json={"name": "Test", "config": {}},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_requires_name(self, client, test_user):
        _user_id, headers = test_user
        response = await client.post(
            "/api/strategies",
            json={"config": {}},
            headers=headers,
        )
        assert response.status_code == 422


class TestListStrategies:
    @pytest.mark.asyncio
    async def test_list_strategies_empty(self, client, auth_headers):
        _user_id, headers = auth_headers
        response = await client.get("/api/strategies", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["strategies"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_strategies_returns_own(self, client, test_user):
        _user_id, headers = test_user
        # Create 2 strategies
        await client.post(
            "/api/strategies",
            json={"name": "Strategy A", "config": {}},
            headers=headers,
        )
        await client.post(
            "/api/strategies",
            json={"name": "Strategy B", "config": {}},
            headers=headers,
        )

        response = await client.get("/api/strategies", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        names = [s["name"] for s in data["strategies"]]
        assert "Strategy A" in names
        assert "Strategy B" in names

    @pytest.mark.asyncio
    async def test_list_strategies_scoped_to_user(self, client, test_user):
        _user_id, headers = test_user
        await client.post(
            "/api/strategies",
            json={"name": "My Strategy", "config": {}},
            headers=headers,
        )

        # Different user should see 0
        other_id = str(uuid.uuid4())
        other_token = create_access_token(other_id)
        other_headers = {"Authorization": f"Bearer {other_token}"}
        response = await client.get("/api/strategies", headers=other_headers)
        assert response.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client):
        response = await client.get("/api/strategies")
        assert response.status_code == 401


class TestGetStrategy:
    @pytest.mark.asyncio
    async def test_get_strategy(self, client, test_user):
        _user_id, headers = test_user
        create = await client.post(
            "/api/strategies",
            json={"name": "Get Me", "config": {"key": "value"}},
            headers=headers,
        )
        strategy_id = create.json()["id"]

        response = await client.get(f"/api/strategies/{strategy_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["name"] == "Get Me"

    @pytest.mark.asyncio
    async def test_get_strategy_not_found(self, client, auth_headers):
        _user_id, headers = auth_headers
        fake_id = str(uuid.uuid4())
        response = await client.get(f"/api/strategies/{fake_id}", headers=headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_requires_auth(self, client):
        fake_id = str(uuid.uuid4())
        response = await client.get(f"/api/strategies/{fake_id}")
        assert response.status_code == 401


class TestUpdateStrategy:
    @pytest.mark.asyncio
    async def test_update_strategy(self, client, test_user):
        _user_id, headers = test_user
        create = await client.post(
            "/api/strategies",
            json={"name": "Original", "config": {"a": 1}},
            headers=headers,
        )
        strategy_id = create.json()["id"]

        response = await client.put(
            f"/api/strategies/{strategy_id}",
            json={"name": "Updated", "config": {"b": 2}},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated"
        assert data["config"] == {"b": 2}

    @pytest.mark.asyncio
    async def test_update_partial(self, client, test_user):
        """Can update just the name without changing config."""
        _user_id, headers = test_user
        create = await client.post(
            "/api/strategies",
            json={"name": "Original", "config": {"keep": True}},
            headers=headers,
        )
        strategy_id = create.json()["id"]

        response = await client.put(
            f"/api/strategies/{strategy_id}",
            json={"name": "New Name"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["config"] == {"keep": True}

    @pytest.mark.asyncio
    async def test_update_not_found(self, client, auth_headers):
        _user_id, headers = auth_headers
        fake_id = str(uuid.uuid4())
        response = await client.put(
            f"/api/strategies/{fake_id}",
            json={"name": "X"},
            headers=headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_requires_auth(self, client):
        fake_id = str(uuid.uuid4())
        response = await client.put(
            f"/api/strategies/{fake_id}",
            json={"name": "X"},
        )
        assert response.status_code == 401


class TestActivateStrategy:
    @pytest.mark.asyncio
    async def test_activate_strategy(self, client, test_user):
        _user_id, headers = test_user
        create = await client.post(
            "/api/strategies",
            json={"name": "To Activate", "config": {}},
            headers=headers,
        )
        strategy_id = create.json()["id"]
        assert create.json()["is_active"] is False

        response = await client.post(
            f"/api/strategies/{strategy_id}/activate", headers=headers
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is True

        # Toggle again
        response2 = await client.post(
            f"/api/strategies/{strategy_id}/activate", headers=headers
        )
        assert response2.status_code == 200
        assert response2.json()["is_active"] is False

    @pytest.mark.asyncio
    async def test_activate_not_found(self, client, auth_headers):
        _user_id, headers = auth_headers
        fake_id = str(uuid.uuid4())
        response = await client.post(
            f"/api/strategies/{fake_id}/activate", headers=headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_activate_requires_auth(self, client):
        fake_id = str(uuid.uuid4())
        response = await client.post(f"/api/strategies/{fake_id}/activate")
        assert response.status_code == 401


class TestDeleteStrategy:
    @pytest.mark.asyncio
    async def test_delete_strategy(self, client, test_user):
        _user_id, headers = test_user
        create = await client.post(
            "/api/strategies",
            json={"name": "To Delete", "config": {}},
            headers=headers,
        )
        strategy_id = create.json()["id"]

        response = await client.delete(
            f"/api/strategies/{strategy_id}", headers=headers
        )
        assert response.status_code == 204

        # Verify it's gone
        get_response = await client.get(
            f"/api/strategies/{strategy_id}", headers=headers
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client, auth_headers):
        _user_id, headers = auth_headers
        fake_id = str(uuid.uuid4())
        response = await client.delete(
            f"/api/strategies/{fake_id}", headers=headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_requires_auth(self, client):
        fake_id = str(uuid.uuid4())
        response = await client.delete(f"/api/strategies/{fake_id}")
        assert response.status_code == 401
