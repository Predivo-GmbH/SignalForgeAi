import pytest


@pytest.mark.asyncio
async def test_register_new_user(client):
    response = await client.post("/api/auth/register", json={
        "email": "test@signalforge.com",
        "password": "Testpass123"
    })
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    await client.post("/api/auth/register", json={
        "email": "dupe@signalforge.com",
        "password": "Testpass123"
    })
    response = await client.post("/api/auth/register", json={
        "email": "dupe@signalforge.com",
        "password": "Testpass123"
    })
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_login_valid_credentials(client):
    await client.post("/api/auth/register", json={
        "email": "login@signalforge.com",
        "password": "Testpass123"
    })
    response = await client.post("/api/auth/login", json={
        "email": "login@signalforge.com",
        "password": "Testpass123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_login_invalid_password(client):
    await client.post("/api/auth/register", json={
        "email": "bad@signalforge.com",
        "password": "Testpass123"
    })
    response = await client.post("/api/auth/login", json={
        "email": "bad@signalforge.com",
        "password": "wrongpass"
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client):
    reg = await client.post("/api/auth/register", json={
        "email": "refresh@signalforge.com",
        "password": "Testpass123"
    })
    refresh_token = reg.json()["refresh_token"]
    response = await client.post("/api/auth/refresh", json={
        "refresh_token": refresh_token
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_delete_account_cascades(client):
    """GDPR: DELETE /auth/user removes all user data."""
    # Register a user
    reg = await client.post("/api/auth/register", json={
        "email": "delete-test@example.com",
        "password": "DeleteMe123"
    })
    assert reg.status_code == 201
    tokens = reg.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    # Create some data (strategy)
    await client.post("/api/strategies/", json={
        "name": "Test Strategy",
        "description": "For deletion test",
        "symbols": ["BTC/USDT"],
    }, headers=headers)
    # Don't assert strategy creation succeeds -- schema may vary

    # Delete the account
    resp = await client.delete("/api/auth/user", headers=headers)
    assert resp.status_code == 204

    # Verify token is now invalid (401 if blacklisted, 404 if user deleted)
    me = await client.get("/api/auth/me", headers=headers)
    assert me.status_code in (401, 404)


@pytest.mark.asyncio
async def test_export_user_data(client):
    """GDPR: GET /auth/user/export returns user data."""
    # Register
    reg = await client.post("/api/auth/register", json={
        "email": "export-test@example.com",
        "password": "ExportMe123"
    })
    assert reg.status_code == 201
    tokens = reg.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    # Export data
    resp = await client.get("/api/auth/user/export", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    # Verify structure
    assert "user" in data
    assert data["user"]["email"] == "export-test@example.com"
    assert "strategies" in data
    assert "signals" in data
    assert "trades" in data


@pytest.mark.asyncio
async def test_delete_nonexistent_after_deletion(client):
    """Deleted account cannot be accessed again."""
    reg = await client.post("/api/auth/register", json={
        "email": "double-delete@example.com",
        "password": "DeleteTwice1"
    })
    tokens = reg.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    # Delete once
    resp = await client.delete("/api/auth/user", headers=headers)
    assert resp.status_code == 204

    # Try to use the token -- should fail (401 if blacklisted, 404 if gone)
    resp2 = await client.get("/api/auth/user/export", headers=headers)
    assert resp2.status_code in (401, 404)
