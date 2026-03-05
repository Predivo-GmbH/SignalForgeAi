"""Tests for the AI Usage & Cost Tracking API."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.auth.jwt import create_access_token
from app.models.ai_insight import AIInsight
from tests.conftest import test_session

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth_headers(user_id: str | None = None) -> dict[str, str]:
    """Return Authorization headers for a random (or given) user."""
    uid = user_id or str(uuid.uuid4())
    token = create_access_token(uid)
    return {"Authorization": f"Bearer {token}"}


def _make_insight(
    *,
    insight_type: str = "investment_plan",
    model_used: str = "claude-sonnet-4-6",
    cost_usd: float = 0.0045,
    input_tokens: int = 500,
    output_tokens: int = 200,
    latency_ms: int = 1200,
    created_at: datetime | None = None,
) -> AIInsight:
    """Build an AIInsight row with sensible defaults."""
    now = datetime.now(UTC)
    return AIInsight(
        id=uuid.uuid4(),
        created_at=created_at or now,
        updated_at=now,
        insight_type=insight_type,
        model_used=model_used,
        result_json={},
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
    )


async def _seed(rows):
    """Insert rows into the test DB via a separate session."""
    async with test_session() as db:
        db.add_all(rows)
        await db.commit()


# ---------------------------------------------------------------------------
# GET /api/ai-usage
# ---------------------------------------------------------------------------


class TestGetAiUsage:
    """Tests for the GET /api/ai-usage endpoint."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client):
        response = await client.get("/api/ai-usage")
        assert response.status_code == 401

    @pytest.mark.asyncio
    @patch("app.advisor.anthropic_admin.available", return_value=False)
    async def test_empty_usage(self, _mock_admin, client):
        with patch(
                "app.api.ai_usage._get_prepaid_credit",
                new_callable=AsyncMock, return_value=5.0,
            ):
            response = await client.get("/api/ai-usage", headers=_auth_headers())

        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "local"
        assert data["summary"]["total_calls"] == 0
        assert data["summary"]["total_cost_usd"] == 0.0
        assert data["by_model"] == []
        assert data["by_type"] == []
        assert data["daily_costs"] == []
        assert data["recent_calls"] == []

    @pytest.mark.asyncio
    @patch("app.advisor.anthropic_admin.available", return_value=False)
    async def test_summary_after_inserts(self, _mock_admin, client):
        await _seed([
            _make_insight(cost_usd=0.01, latency_ms=1000),
            _make_insight(cost_usd=0.02, latency_ms=2000),
            _make_insight(cost_usd=0.03, latency_ms=3000),
        ])

        with patch(
                "app.api.ai_usage._get_prepaid_credit",
                new_callable=AsyncMock, return_value=5.0,
            ):
            response = await client.get("/api/ai-usage", headers=_auth_headers())

        assert response.status_code == 200
        summary = response.json()["summary"]
        assert summary["total_calls"] == 3
        assert abs(summary["total_cost_usd"] - 0.06) < 1e-4
        assert abs(summary["avg_cost_per_call"] - 0.02) < 1e-4
        assert abs(summary["avg_latency_ms"] - 2000.0) < 1e-1

    @pytest.mark.asyncio
    @patch("app.advisor.anthropic_admin.available", return_value=False)
    async def test_by_model_breakdown(self, _mock_admin, client):
        await _seed([
            _make_insight(model_used="claude-sonnet-4-6", cost_usd=0.01, latency_ms=800),
            _make_insight(model_used="claude-sonnet-4-6", cost_usd=0.02, latency_ms=1200),
            _make_insight(model_used="claude-haiku-4-5-20251001", cost_usd=0.001, latency_ms=300),
        ])

        with patch(
                "app.api.ai_usage._get_prepaid_credit",
                new_callable=AsyncMock, return_value=0.0,
            ):
            response = await client.get("/api/ai-usage", headers=_auth_headers())

        by_model = {m["model"]: m for m in response.json()["by_model"]}
        assert "claude-sonnet-4-6" in by_model
        assert by_model["claude-sonnet-4-6"]["calls"] == 2
        assert abs(by_model["claude-sonnet-4-6"]["cost_usd"] - 0.03) < 1e-4
        assert by_model["claude-haiku-4-5-20251001"]["calls"] == 1

    @pytest.mark.asyncio
    @patch("app.advisor.anthropic_admin.available", return_value=False)
    async def test_by_type_breakdown(self, _mock_admin, client):
        await _seed([
            _make_insight(insight_type="investment_plan", cost_usd=0.01),
            _make_insight(insight_type="investment_plan", cost_usd=0.02),
            _make_insight(insight_type="signal_quality", cost_usd=0.005),
            _make_insight(insight_type="risk_tuning", cost_usd=0.003),
        ])

        with patch(
                "app.api.ai_usage._get_prepaid_credit",
                new_callable=AsyncMock, return_value=0.0,
            ):
            response = await client.get("/api/ai-usage", headers=_auth_headers())

        by_type = {t["insight_type"]: t for t in response.json()["by_type"]}
        assert len(by_type) == 3
        assert by_type["investment_plan"]["calls"] == 2
        assert abs(by_type["investment_plan"]["cost_usd"] - 0.03) < 1e-4

    @pytest.mark.asyncio
    @patch("app.advisor.anthropic_admin.available", return_value=False)
    async def test_daily_costs_aggregation(self, _mock_admin, client):
        today = datetime.now(UTC).replace(hour=12, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)

        await _seed([
            _make_insight(cost_usd=0.01, created_at=today),
            _make_insight(cost_usd=0.02, created_at=today),
            _make_insight(cost_usd=0.05, created_at=yesterday),
        ])

        with patch(
                "app.api.ai_usage._get_prepaid_credit",
                new_callable=AsyncMock, return_value=0.0,
            ):
            response = await client.get("/api/ai-usage", headers=_auth_headers())

        daily = {d["date"]: d for d in response.json()["daily_costs"]}
        assert daily[today.strftime("%Y-%m-%d")]["calls"] == 2
        assert daily[yesterday.strftime("%Y-%m-%d")]["calls"] == 1

    @pytest.mark.asyncio
    @patch("app.advisor.anthropic_admin.available", return_value=False)
    async def test_recent_calls_limit_20(self, _mock_admin, client):
        now = datetime.now(UTC)
        await _seed([
            _make_insight(cost_usd=0.001 * i, created_at=now - timedelta(minutes=i))
            for i in range(25)
        ])

        with patch(
                "app.api.ai_usage._get_prepaid_credit",
                new_callable=AsyncMock, return_value=0.0,
            ):
            response = await client.get("/api/ai-usage", headers=_auth_headers())

        recent = response.json()["recent_calls"]
        assert len(recent) == 20
        timestamps = [r["created_at"] for r in recent]
        assert timestamps == sorted(timestamps, reverse=True)

    @pytest.mark.asyncio
    @patch("app.advisor.anthropic_admin.available", return_value=False)
    async def test_recent_calls_fields(self, _mock_admin, client):
        await _seed([_make_insight(
            insight_type="risk_tuning", model_used="claude-haiku-4-5-20251001",
            cost_usd=0.002, input_tokens=100, output_tokens=50, latency_ms=450,
        )])

        with patch(
                "app.api.ai_usage._get_prepaid_credit",
                new_callable=AsyncMock, return_value=0.0,
            ):
            response = await client.get("/api/ai-usage", headers=_auth_headers())

        call = response.json()["recent_calls"][0]
        assert call["insight_type"] == "risk_tuning"
        assert call["model_used"] == "claude-haiku-4-5-20251001"
        assert call["input_tokens"] == 100
        assert "id" in call
        assert "created_at" in call

    @pytest.mark.asyncio
    @patch("app.advisor.anthropic_admin.available", return_value=False)
    async def test_credit_info_calculation(self, _mock_admin, client):
        await _seed([_make_insight(cost_usd=1.00), _make_insight(cost_usd=0.50)])

        with (
            patch(
                "app.api.ai_usage._get_prepaid_credit",
                new_callable=AsyncMock, return_value=5.0,
            ),
            patch(
                "app.api.ai_usage._get_cumulative_cost",
                new_callable=AsyncMock, return_value=1.50,
            ),
        ):
            response = await client.get(
                "/api/ai-usage", headers=_auth_headers(),
            )

        credit = response.json()["credit"]
        assert credit["prepaid_usd"] == 5.0
        assert abs(credit["spent_usd"] - 1.50) < 1e-4
        assert abs(credit["remaining_usd"] - 3.50) < 1e-2

    @pytest.mark.asyncio
    @patch("app.advisor.anthropic_admin.available", return_value=False)
    async def test_credit_remaining_floors_at_zero(
        self, _mock_admin, client,
    ):
        await _seed([_make_insight(cost_usd=10.0)])

        with (
            patch(
                "app.api.ai_usage._get_prepaid_credit",
                new_callable=AsyncMock, return_value=5.0,
            ),
            patch(
                "app.api.ai_usage._get_cumulative_cost",
                new_callable=AsyncMock, return_value=10.0,
            ),
        ):
            response = await client.get(
                "/api/ai-usage", headers=_auth_headers(),
            )

        assert response.json()["credit"]["remaining_usd"] == 0.0

    @pytest.mark.asyncio
    @patch("app.advisor.anthropic_admin.available", return_value=False)
    async def test_days_parameter_filtering(self, _mock_admin, client):
        now = datetime.now(UTC)
        await _seed([
            _make_insight(cost_usd=0.01, created_at=now),
            _make_insight(
                cost_usd=0.99,
                created_at=now - timedelta(days=60),
            ),
        ])

        with (
            patch(
                "app.api.ai_usage._get_prepaid_credit",
                new_callable=AsyncMock, return_value=5.0,
            ),
            patch(
                "app.api.ai_usage._get_cumulative_cost",
                new_callable=AsyncMock, return_value=1.00,
            ),
        ):
            response = await client.get(
                "/api/ai-usage", params={"days": 7},
                headers=_auth_headers(),
            )

        data = response.json()
        assert data["summary"]["total_calls"] == 1
        assert abs(data["summary"]["total_cost_usd"] - 0.01) < 1e-4
        # All-time spent includes old row
        assert abs(data["credit"]["spent_usd"] - 1.00) < 1e-4

    @pytest.mark.asyncio
    @patch("app.advisor.anthropic_admin.available", return_value=False)
    async def test_days_parameter_default_30(self, _mock_admin, client):
        now = datetime.now(UTC)
        await _seed([_make_insight(cost_usd=0.05, created_at=now - timedelta(days=15))])

        with patch(
                "app.api.ai_usage._get_prepaid_credit",
                new_callable=AsyncMock, return_value=0.0,
            ):
            response = await client.get("/api/ai-usage", headers=_auth_headers())

        assert response.json()["summary"]["total_calls"] == 1

    @pytest.mark.asyncio
    @patch("app.advisor.anthropic_admin.available", return_value=False)
    async def test_source_is_local_without_admin_key(self, _mock_admin, client):
        with patch(
                "app.api.ai_usage._get_prepaid_credit",
                new_callable=AsyncMock, return_value=0.0,
            ):
            response = await client.get("/api/ai-usage", headers=_auth_headers())

        assert response.json()["source"] == "local"


# ---------------------------------------------------------------------------
# PUT /api/ai-usage/credit
# ---------------------------------------------------------------------------


class TestUpdateCredit:

    @pytest.mark.asyncio
    async def test_requires_auth(self, client):
        response = await client.put("/api/ai-usage/credit", json={"prepaid_usd": 10.0})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_credit(self, client):
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()

        with patch("app.core.redis_client.redis_client", mock_redis):
            response = await client.put(
                "/api/ai-usage/credit",
                json={"prepaid_usd": 12.50},
                headers=_auth_headers(),
            )

        assert response.status_code == 200
        assert response.json()["prepaid_usd"] == 12.50
        mock_redis.set.assert_awaited_once_with("ai_prepaid_credit", "12.5")

    @pytest.mark.asyncio
    async def test_update_credit_zero(self, client):
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()

        with patch("app.core.redis_client.redis_client", mock_redis):
            response = await client.put(
                "/api/ai-usage/credit",
                json={"prepaid_usd": 0.0},
                headers=_auth_headers(),
            )

        assert response.status_code == 200
        assert response.json()["prepaid_usd"] == 0.0

    @pytest.mark.asyncio
    async def test_update_credit_missing_field(self, client):
        response = await client.put(
            "/api/ai-usage/credit", json={}, headers=_auth_headers()
        )
        assert response.status_code == 422
