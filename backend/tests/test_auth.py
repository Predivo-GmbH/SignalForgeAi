import pytest


@pytest.mark.asyncio
async def test_register_new_user(client):
    response = await client.post("/api/auth/register", json={
        "email": "test@signalforge.com",
        "password": "testpass123"
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
        "password": "testpass123"
    })
    response = await client.post("/api/auth/register", json={
        "email": "dupe@signalforge.com",
        "password": "testpass123"
    })
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_login_valid_credentials(client):
    await client.post("/api/auth/register", json={
        "email": "login@signalforge.com",
        "password": "testpass123"
    })
    response = await client.post("/api/auth/login", json={
        "email": "login@signalforge.com",
        "password": "testpass123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_login_invalid_password(client):
    await client.post("/api/auth/register", json={
        "email": "bad@signalforge.com",
        "password": "testpass123"
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
        "password": "testpass123"
    })
    refresh_token = reg.json()["refresh_token"]
    response = await client.post("/api/auth/refresh", json={
        "refresh_token": refresh_token
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
