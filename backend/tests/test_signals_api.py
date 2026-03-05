"""Tests for the Signals REST API."""

import uuid

import pytest

from app.auth.jwt import create_access_token
from app.models.signal import Signal


@pytest.fixture
def test_user_id():
    """Return a stable test user UUID."""
    return str(uuid.uuid4())


@pytest.fixture
def auth_headers(test_user_id):
    """Return valid auth headers for a test user."""
    token = create_access_token(test_user_id)
    return {"Authorization": f"Bearer {token}"}


class TestGenerateSignal:
    @pytest.mark.asyncio
    async def test_generate_signal_returns_200(self, client, auth_headers):
        response = await client.post(
            "/api/signals/generate",
            json={"symbol": "BTC/USDT", "timeframe": "1h"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "action" in data
        assert data["action"] in ("BUY", "SELL", "NO_TRADE")
        assert data["symbol"] == "BTC/USDT"
        assert data["timeframe"] == "1h"

    @pytest.mark.asyncio
    async def test_generate_requires_auth(self, client):
        response = await client.post(
            "/api/signals/generate",
            json={"symbol": "BTC/USDT", "timeframe": "1h"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_generate_with_invalid_token(self, client):
        response = await client.post(
            "/api/signals/generate",
            json={"symbol": "BTC/USDT", "timeframe": "1h"},
            headers={"Authorization": "Bearer bad-token"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_generate_default_symbol_and_timeframe(self, client, auth_headers):
        """If no body is given, defaults should be used."""
        response = await client.post(
            "/api/signals/generate",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "BTC/USDT"
        assert data["timeframe"] == "1h"


class TestListSignals:
    @pytest.mark.asyncio
    async def test_list_signals_empty(self, client, auth_headers):
        response = await client.get("/api/signals", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["signals"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_signals_requires_auth(self, client):
        response = await client.get("/api/signals")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_signals_pagination(self, client, auth_headers):
        response = await client.get(
            "/api/signals", params={"limit": 5, "offset": 0}, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "signals" in data
        assert "total" in data


class TestGetSignal:
    @pytest.mark.asyncio
    async def test_get_signal_not_found(self, client, auth_headers):
        fake_id = str(uuid.uuid4())
        response = await client.get(f"/api/signals/{fake_id}", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_signal_requires_auth(self, client):
        fake_id = str(uuid.uuid4())
        response = await client.get(f"/api/signals/{fake_id}")
        assert response.status_code == 401


class TestListSignalsByStrategy:
    @pytest.mark.asyncio
    async def test_filter_by_strategy_id(
        self, client, auth_headers, test_user_id,
    ):
        """Signals should be filterable by strategy_id."""
        from app.core.database import get_db
        from app.main import app as test_app

        db_gen = test_app.dependency_overrides[get_db]()
        db = await db_gen.__anext__()

        uid = uuid.UUID(test_user_id)
        strategy_id = uuid.uuid4()
        # Insert a signal WITH strategy_id
        sig1 = Signal(
            user_id=uid,
            strategy_id=strategy_id,
            symbol="BTC/USDT",
            timeframe="1h",
            direction="BUY",
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit_1=51000.0,
            confluence_score=70,
            regime="trending",
            status="active",
        )
        # Insert a signal WITHOUT strategy_id
        sig2 = Signal(
            user_id=uid,
            symbol="ETH/USDT",
            timeframe="1h",
            direction="SELL",
            entry_price=2000.0,
            stop_loss=2100.0,
            take_profit_1=1900.0,
            confluence_score=60,
            regime="ranging",
            status="active",
        )
        db.add_all([sig1, sig2])
        await db.commit()

        # Filter by strategy_id should return only the matching signal
        response = await client.get(
            "/api/signals",
            params={"strategy_id": str(strategy_id)},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["signals"][0]["symbol"] == "BTC/USDT"
        assert data["signals"][0]["strategy_id"] == str(strategy_id)

    @pytest.mark.asyncio
    async def test_no_filter_returns_all(self, client, auth_headers):
        """Without strategy_id filter, all signals should be returned."""
        response = await client.get("/api/signals", headers=auth_headers)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_filter_nonexistent_strategy(self, client, auth_headers):
        """Filtering by a nonexistent strategy_id should return empty."""
        response = await client.get(
            "/api/signals",
            params={"strategy_id": str(uuid.uuid4())},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["signals"] == []
