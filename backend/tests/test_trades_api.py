"""Tests for the Trades REST API."""

import uuid
from datetime import datetime, timezone

import pytest

from app.auth.jwt import create_access_token
from app.models.trade import Trade


@pytest.fixture
async def test_user(client):
    """Create a test user via registration and return (user_id, headers)."""
    reg = await client.post("/api/auth/register", json={
        "email": f"trades-{uuid.uuid4().hex[:8]}@test.com",
        "password": "testpass123",
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


class TestListTrades:
    @pytest.mark.asyncio
    async def test_list_trades_empty(self, client, auth_headers):
        _user_id, headers = auth_headers
        response = await client.get("/api/trades", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["trades"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_trades_requires_auth(self, client):
        response = await client.get("/api/trades")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_trades_scoped_to_user(self, client, test_user):
        """Trades belong to a specific user — other users shouldn't see them."""
        user_id, headers = test_user

        # Insert a trade for this user directly via DB
        from app.core.database import get_db
        from app.main import app as test_app

        db_gen = test_app.dependency_overrides[get_db]()
        db = await db_gen.__anext__()
        trade = Trade(
            user_id=uuid.UUID(user_id),
            symbol="ETH/USDT",
            direction="BUY",
            entry_price=2000.0,
            position_size=0.5,
            stop_loss=1950.0,
            take_profit=2100.0,
            confluence_score=75,
        )
        db.add(trade)
        await db.commit()

        response = await client.get("/api/trades", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["trades"][0]["symbol"] == "ETH/USDT"

        # A different user should see 0 trades
        other_id = str(uuid.uuid4())
        other_token = create_access_token(other_id)
        other_headers = {"Authorization": f"Bearer {other_token}"}
        response2 = await client.get("/api/trades", headers=other_headers)
        assert response2.json()["total"] == 0


class TestGetTrade:
    @pytest.mark.asyncio
    async def test_get_trade_not_found(self, client, auth_headers):
        _user_id, headers = auth_headers
        fake_id = str(uuid.uuid4())
        response = await client.get(f"/api/trades/{fake_id}", headers=headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_trade_requires_auth(self, client):
        fake_id = str(uuid.uuid4())
        response = await client.get(f"/api/trades/{fake_id}")
        assert response.status_code == 401


class TestTradeStats:
    @pytest.mark.asyncio
    async def test_stats_empty(self, client, auth_headers):
        _user_id, headers = auth_headers
        response = await client.get("/api/trades/stats", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_trades"] == 0
        assert data["win_rate"] == 0.0
        assert data["profit_factor"] == 0.0
        assert data["total_pnl"] == 0.0

    @pytest.mark.asyncio
    async def test_stats_with_trades(self, client, test_user):
        user_id, headers = test_user

        from app.core.database import get_db
        from app.main import app as test_app

        db_gen = test_app.dependency_overrides[get_db]()
        db = await db_gen.__anext__()

        # Insert 2 winning trades and 1 losing trade
        for pnl in [100.0, 50.0, -30.0]:
            trade = Trade(
                user_id=uuid.UUID(user_id),
                symbol="BTC/USDT",
                direction="BUY",
                entry_price=50000.0,
                exit_price=50000.0 + pnl,
                position_size=1.0,
                stop_loss=49000.0,
                take_profit=51000.0,
                pnl=pnl,
                pnl_pct=pnl / 50000.0 * 100,
                confluence_score=70,
                exit_time=datetime.now(timezone.utc),
            )
            db.add(trade)
        await db.commit()

        response = await client.get("/api/trades/stats", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_trades"] == 3
        # 2 winning out of 3
        assert abs(data["win_rate"] - 66.67) < 1.0
        # profit_factor = sum(wins) / abs(sum(losses)) = 150 / 30 = 5.0
        assert abs(data["profit_factor"] - 5.0) < 0.01
        assert abs(data["total_pnl"] - 120.0) < 0.01

    @pytest.mark.asyncio
    async def test_stats_requires_auth(self, client):
        response = await client.get("/api/trades/stats")
        assert response.status_code == 401
