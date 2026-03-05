"""Tests for the AI Advisor API endpoints: scan, plan, deploy."""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.auth.jwt import create_access_token
from app.core.rate_limit import limiter

TEST_USER_UUID = "00000000-0000-0000-0000-000000000001"


@pytest.fixture(autouse=True)
def _disable_rate_limit():
    """Disable slowapi rate limiting for all advisor tests."""
    limiter.enabled = False
    yield
    limiter.enabled = True

# ---------- Mock data ----------

MOCK_SCORED = [
    {
        "symbol": "BTC/USDT",
        "score": 75,
        "regime": "trending_up",
        "trend_direction": "bullish",
        "rsi": 62,
        "adx": 28,
        "atr_pct": 2.3,
        "recommendation": "strong_buy",
    },
    {
        "symbol": "ETH/USDT",
        "score": 68,
        "regime": "trending_up",
        "trend_direction": "bullish",
        "rsi": 58,
        "adx": 25,
        "atr_pct": 3.1,
        "recommendation": "buy",
    },
]

MOCK_TOP_PAIRS = [
    {"symbol": "BTC/USDT", "rank": 1, "volume_24h": 1_500_000_000, "change_pct_24h": 2.5},
    {"symbol": "ETH/USDT", "rank": 2, "volume_24h": 800_000_000, "change_pct_24h": 1.8},
]

MOCK_CANDLES = {
    "BTC/USDT": [[1700000000, 42000, 42500, 41800, 42300, 100]],
    "ETH/USDT": [[1700000000, 2200, 2250, 2180, 2230, 500]],
}

MOCK_MARKET_PROFILE = {
    "trending_pct": 60.0,
    "bullish_pct": 55.0,
    "avg_score": 71.5,
    "avg_adx": 26.5,
    "avg_volatility": 2.7,
    "chaotic_pct": 10.0,
}

MOCK_PLAN = {
    "summary": "Strong bullish momentum",
    "selected_cryptos": [
        {"symbol": "BTC/USDT", "reason": "Leading bullish setup"},
        {"symbol": "ETH/USDT", "reason": "Confirming trend"},
    ],
    "strategy_config": {
        "min_confluence": 45,
        "min_trigger_count": 2,
        "trigger_lookback_candles": 3,
        "ema_slope_threshold": 0.0005,
        "max_risk_per_trade": 0.02,
        "max_daily_loss": 0.06,
        "atr_sl_multiplier": 2.0,
        "min_risk_reward": 1.5,
        "timeframes": ["1h"],
        "trailing_stop_enabled": False,
        "account_equity": 10000,
    },
    "reasoning": "test reasoning",
    "expected_behavior": "test behavior",
    "warnings": [],
}


# ---------- Fixtures ----------


@pytest.fixture
def auth_headers():
    """Return valid auth headers for a deterministic test user."""
    token = create_access_token(TEST_USER_UUID)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def registered_user(client):
    """Create a test user via registration and return headers."""
    email = f"advisor-{uuid.uuid4().hex[:8]}@test.com"
    reg = await client.post("/api/auth/register", json={
        "email": email,
        "password": "Testpass123",
    })
    data = reg.json()
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    return headers


def _mock_scanner():
    """Create a mock MarketScanner instance."""
    scanner = MagicMock()
    scanner.scan_top_pairs.return_value = MOCK_TOP_PAIRS
    scanner.fetch_candles_batch.return_value = MOCK_CANDLES
    return scanner


def _mock_analyzer():
    """Create a mock TechnicalAnalyzer instance."""
    analyzer = MagicMock()
    analyzer.analyze_market.return_value = MOCK_SCORED
    analyzer.compute_market_profile.return_value = MOCK_MARKET_PROFILE
    return analyzer


# ---------- Scan endpoint ----------


class TestScanMarket:
    """Tests for POST /api/advisor/scan."""

    @pytest.mark.asyncio
    async def test_scan_returns_scored_results(self, client, auth_headers):
        scanner = _mock_scanner()
        analyzer = _mock_analyzer()

        with (
            patch("app.advisor.scanner.MarketScanner", return_value=scanner),
            patch("app.advisor.analyzer.TechnicalAnalyzer", return_value=analyzer),
        ):
            response = await client.post(
                "/api/advisor/scan",
                json={"top_n": 50},
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["pairs_scanned"] == 2
        assert data["pairs_scored"] == 2
        assert len(data["results"]) == 2
        assert data["results"][0]["symbol"] == "BTC/USDT"
        assert data["results"][0]["score"] == 75
        assert "market_profile" in data
        assert data["market_profile"]["trending_pct"] == 60.0

        scanner.scan_top_pairs.assert_called_once_with(top_n=50)
        analyzer.analyze_market.assert_called_once()

    @pytest.mark.asyncio
    async def test_scan_default_top_n(self, client, auth_headers):
        """When no body is provided, top_n defaults to 100."""
        scanner = _mock_scanner()
        analyzer = _mock_analyzer()

        with (
            patch("app.advisor.scanner.MarketScanner", return_value=scanner),
            patch("app.advisor.analyzer.TechnicalAnalyzer", return_value=analyzer),
        ):
            response = await client.post(
                "/api/advisor/scan",
                headers=auth_headers,
            )

        assert response.status_code == 200
        scanner.scan_top_pairs.assert_called_once_with(top_n=100)

    @pytest.mark.asyncio
    async def test_scan_merges_ticker_data(self, client, auth_headers):
        """Scan results should include volume_24h and change_pct_24h from ticker data."""
        scanner = _mock_scanner()
        analyzer = _mock_analyzer()

        with (
            patch("app.advisor.scanner.MarketScanner", return_value=scanner),
            patch("app.advisor.analyzer.TechnicalAnalyzer", return_value=analyzer),
        ):
            response = await client.post(
                "/api/advisor/scan",
                headers=auth_headers,
            )

        data = response.json()
        btc_result = data["results"][0]
        assert btc_result["volume_24h"] == 1_500_000_000
        assert btc_result["change_pct_24h"] == 2.5

    @pytest.mark.asyncio
    async def test_scan_requires_auth(self, client):
        response = await client.post("/api/advisor/scan", json={"top_n": 50})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_scan_binance_connection_failure(self, client, auth_headers):
        with patch(
            "app.advisor.scanner.MarketScanner",
            side_effect=Exception("Connection refused"),
        ):
            response = await client.post(
                "/api/advisor/scan",
                json={"top_n": 50},
                headers=auth_headers,
            )

        assert response.status_code == 502
        assert "Cannot connect to exchange" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_scan_market_fetch_failure(self, client, auth_headers):
        scanner = MagicMock()
        scanner.scan_top_pairs.side_effect = Exception("Rate limited")

        with patch("app.advisor.scanner.MarketScanner", return_value=scanner):
            response = await client.post(
                "/api/advisor/scan",
                json={"top_n": 50},
                headers=auth_headers,
            )

        assert response.status_code == 502
        assert "Failed to fetch market data" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_scan_empty_results(self, client, auth_headers):
        scanner = MagicMock()
        scanner.scan_top_pairs.return_value = []

        with patch("app.advisor.scanner.MarketScanner", return_value=scanner):
            response = await client.post(
                "/api/advisor/scan",
                json={"top_n": 50},
                headers=auth_headers,
            )

        assert response.status_code == 404
        assert "No liquid trading pairs found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_scan_candle_fetch_failure(self, client, auth_headers):
        scanner = MagicMock()
        scanner.scan_top_pairs.return_value = MOCK_TOP_PAIRS
        scanner.fetch_candles_batch.side_effect = Exception("Timeout")

        with patch("app.advisor.scanner.MarketScanner", return_value=scanner):
            response = await client.post(
                "/api/advisor/scan",
                headers=auth_headers,
            )

        assert response.status_code == 502
        assert "Failed to fetch candle data" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_scan_empty_candle_data(self, client, auth_headers):
        scanner = MagicMock()
        scanner.scan_top_pairs.return_value = MOCK_TOP_PAIRS
        scanner.fetch_candles_batch.return_value = {}

        with patch("app.advisor.scanner.MarketScanner", return_value=scanner):
            response = await client.post(
                "/api/advisor/scan",
                headers=auth_headers,
            )

        assert response.status_code == 502
        assert "no candle data returned" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_scan_analysis_failure(self, client, auth_headers):
        scanner = _mock_scanner()
        analyzer = MagicMock()
        analyzer.analyze_market.side_effect = Exception("NaN in indicators")

        with (
            patch("app.advisor.scanner.MarketScanner", return_value=scanner),
            patch("app.advisor.analyzer.TechnicalAnalyzer", return_value=analyzer),
        ):
            response = await client.post(
                "/api/advisor/scan",
                headers=auth_headers,
            )

        assert response.status_code == 500
        assert "Technical analysis failed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_scan_validates_top_n_range(self, client, auth_headers):
        """top_n must be between 10 and 200."""
        response = await client.post(
            "/api/advisor/scan",
            json={"top_n": 5},
            headers=auth_headers,
        )
        assert response.status_code == 422

        response = await client.post(
            "/api/advisor/scan",
            json={"top_n": 300},
            headers=auth_headers,
        )
        assert response.status_code == 422


# ---------- Plan endpoint ----------


class TestGeneratePlan:
    """Tests for POST /api/advisor/plan."""

    @pytest.mark.asyncio
    async def test_plan_with_scan_results(self, client, auth_headers):
        planner = MagicMock()
        planner.generate_plan.return_value = MOCK_PLAN

        with patch("app.advisor.planner.InvestmentPlanner", return_value=planner):
            response = await client.post(
                "/api/advisor/plan",
                json={
                    "amount": 10000,
                    "scan_results": MOCK_SCORED,
                },
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["summary"] == "Strong bullish momentum"
        assert len(data["selected_cryptos"]) == 2
        assert data["selected_cryptos"][0]["symbol"] == "BTC/USDT"
        assert data["strategy_config"]["min_confluence"] == 45
        assert data["reasoning"] == "test reasoning"
        assert data["warnings"] == []

        planner.generate_plan.assert_called_once_with(MOCK_SCORED, 10000, None)

    @pytest.mark.asyncio
    async def test_plan_ai_unavailable_returns_503(self, client, auth_headers):
        planner = MagicMock()
        planner.generate_plan.return_value = None

        with patch("app.advisor.planner.InvestmentPlanner", return_value=planner):
            response = await client.post(
                "/api/advisor/plan",
                json={
                    "amount": 10000,
                    "scan_results": MOCK_SCORED,
                },
                headers=auth_headers,
            )

        assert response.status_code == 503
        assert "AI advisor is currently unavailable" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_plan_requires_auth(self, client):
        response = await client.post(
            "/api/advisor/plan",
            json={"amount": 10000, "scan_results": MOCK_SCORED},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_plan_fresh_scan_when_no_scan_results(self, client, auth_headers):
        """When scan_results is None, the endpoint runs a fresh scan first."""
        scanner = _mock_scanner()
        analyzer = _mock_analyzer()
        planner = MagicMock()
        planner.generate_plan.return_value = MOCK_PLAN

        with (
            patch("app.advisor.scanner.MarketScanner", return_value=scanner),
            patch("app.advisor.analyzer.TechnicalAnalyzer", return_value=analyzer),
            patch("app.advisor.planner.InvestmentPlanner", return_value=planner),
        ):
            response = await client.post(
                "/api/advisor/plan",
                json={"amount": 5000},
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["summary"] == "Strong bullish momentum"

        # Verify the fresh scan was executed
        scanner.scan_top_pairs.assert_called_once_with(top_n=100)
        scanner.fetch_candles_batch.assert_called_once()
        analyzer.analyze_market.assert_called_once()

        # Planner should receive the scanned data and market profile
        planner.generate_plan.assert_called_once_with(
            MOCK_SCORED, 5000, MOCK_MARKET_PROFILE,
        )

    @pytest.mark.asyncio
    async def test_plan_fresh_scan_failure_returns_502(self, client, auth_headers):
        """When a fresh scan fails, the endpoint returns 502."""
        with patch(
            "app.advisor.scanner.MarketScanner",
            side_effect=Exception("Binance down"),
        ):
            response = await client.post(
                "/api/advisor/plan",
                json={"amount": 10000},
                headers=auth_headers,
            )

        assert response.status_code == 502
        assert "Market scan failed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_plan_generation_exception_returns_500(self, client, auth_headers):
        planner = MagicMock()
        planner.generate_plan.side_effect = Exception("Claude API error")

        with patch("app.advisor.planner.InvestmentPlanner", return_value=planner):
            response = await client.post(
                "/api/advisor/plan",
                json={
                    "amount": 10000,
                    "scan_results": MOCK_SCORED,
                },
                headers=auth_headers,
            )

        assert response.status_code == 500
        assert "Plan generation failed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_plan_validates_amount_range(self, client, auth_headers):
        """Amount must be between 100 and 10,000,000."""
        response = await client.post(
            "/api/advisor/plan",
            json={"amount": 50, "scan_results": MOCK_SCORED},
            headers=auth_headers,
        )
        assert response.status_code == 422

        response = await client.post(
            "/api/advisor/plan",
            json={"amount": 20_000_000, "scan_results": MOCK_SCORED},
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_plan_default_amount(self, client, auth_headers):
        """When amount is not provided, defaults to 10000."""
        planner = MagicMock()
        planner.generate_plan.return_value = MOCK_PLAN

        with patch("app.advisor.planner.InvestmentPlanner", return_value=planner):
            response = await client.post(
                "/api/advisor/plan",
                json={"scan_results": MOCK_SCORED},
                headers=auth_headers,
            )

        assert response.status_code == 200
        planner.generate_plan.assert_called_once_with(MOCK_SCORED, 10000, None)

    @pytest.mark.asyncio
    async def test_plan_custom_amount(self, client, auth_headers):
        """Custom investment amount is passed to the planner."""
        planner = MagicMock()
        planner.generate_plan.return_value = MOCK_PLAN

        with patch("app.advisor.planner.InvestmentPlanner", return_value=planner):
            response = await client.post(
                "/api/advisor/plan",
                json={"amount": 50000, "scan_results": MOCK_SCORED},
                headers=auth_headers,
            )

        assert response.status_code == 200
        planner.generate_plan.assert_called_once_with(MOCK_SCORED, 50000, None)


# ---------- Deploy endpoint ----------


class TestDeployPlan:
    """Tests for POST /api/advisor/deploy."""

    @pytest.mark.asyncio
    async def test_deploy_creates_active_strategy(self, client, registered_user):
        with patch("app.worker.celery_app"):
            response = await client.post(
                "/api/advisor/deploy",
                json={"plan": MOCK_PLAN},
                headers=registered_user,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["strategy_name"] == "AI Advisor \u2014 Optimal"
        assert data["symbols_count"] == 2
        assert "strategy_id" in data
        assert "deployed" in data["message"].lower() or "symbols" in data["message"].lower()

        # Validate the strategy_id is a valid UUID
        uuid.UUID(data["strategy_id"])

    @pytest.mark.asyncio
    async def test_deploy_response_model(self, client, registered_user):
        with patch("app.worker.celery_app"):
            response = await client.post(
                "/api/advisor/deploy",
                json={"plan": MOCK_PLAN},
                headers=registered_user,
            )

        assert response.status_code == 200
        data = response.json()
        # DeployResponse has exactly these keys
        assert "strategy_id" in data
        assert "strategy_name" in data
        assert "symbols_count" in data
        assert "message" in data

    @pytest.mark.asyncio
    async def test_deploy_strategy_is_active_in_db(self, client, registered_user):
        """The deployed strategy should be marked is_active=True in the database."""
        with patch("app.worker.celery_app"):
            deploy_resp = await client.post(
                "/api/advisor/deploy",
                json={"plan": MOCK_PLAN},
                headers=registered_user,
            )

        strategy_id = deploy_resp.json()["strategy_id"]

        # Fetch the strategy via the strategies API to verify is_active
        get_resp = await client.get(
            f"/api/strategies/{strategy_id}",
            headers=registered_user,
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["is_active"] is True

    @pytest.mark.asyncio
    async def test_deploy_strategy_config_has_symbols(self, client, registered_user):
        """The deployed strategy config should contain the selected symbols."""
        with patch("app.worker.celery_app"):
            deploy_resp = await client.post(
                "/api/advisor/deploy",
                json={"plan": MOCK_PLAN},
                headers=registered_user,
            )

        strategy_id = deploy_resp.json()["strategy_id"]
        get_resp = await client.get(
            f"/api/strategies/{strategy_id}",
            headers=registered_user,
        )
        config = get_resp.json()["config"]
        assert "BTC/USDT" in config["symbols"]
        assert "ETH/USDT" in config["symbols"]

    @pytest.mark.asyncio
    async def test_deploy_empty_selected_cryptos_returns_400(self, client, registered_user):
        empty_plan = {
            "selected_cryptos": [],
            "strategy_config": MOCK_PLAN["strategy_config"],
        }
        response = await client.post(
            "/api/advisor/deploy",
            json={"plan": empty_plan},
            headers=registered_user,
        )
        assert response.status_code == 400
        assert "no selected cryptos" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_deploy_missing_selected_cryptos_returns_400(self, client, registered_user):
        plan_without_cryptos = {
            "strategy_config": MOCK_PLAN["strategy_config"],
        }
        response = await client.post(
            "/api/advisor/deploy",
            json={"plan": plan_without_cryptos},
            headers=registered_user,
        )
        # Pydantic validator fires before endpoint handler → 422
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_deploy_requires_auth(self, client):
        response = await client.post(
            "/api/advisor/deploy",
            json={"plan": MOCK_PLAN},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_deploy_triggers_backfill_task(self, client, registered_user):
        with patch("app.worker.celery_app") as mock_celery:
            response = await client.post(
                "/api/advisor/deploy",
                json={"plan": MOCK_PLAN},
                headers=registered_user,
            )

        assert response.status_code == 200
        mock_celery.send_task.assert_called_once_with(
            "backfill_symbols",
            args=[["BTC/USDT", "ETH/USDT"], ["1h"]],
        )

    @pytest.mark.asyncio
    async def test_deploy_backfill_failure_does_not_break(self, client, registered_user):
        """Even if the backfill task fails to dispatch, deploy should still succeed."""
        with patch("app.worker.celery_app") as mock_celery:
            mock_celery.send_task.side_effect = Exception("Redis connection refused")
            response = await client.post(
                "/api/advisor/deploy",
                json={"plan": MOCK_PLAN},
                headers=registered_user,
            )

        # Deploy succeeds despite backfill failure (it's logged as a warning)
        assert response.status_code == 200
        data = response.json()
        assert data["symbols_count"] == 2

    @pytest.mark.asyncio
    async def test_deploy_uses_strategy_config_timeframes(self, client, registered_user):
        """Timeframes from strategy_config should be used for the backfill task."""
        plan_4h = {
            **MOCK_PLAN,
            "strategy_config": {
                **MOCK_PLAN["strategy_config"],
                "timeframes": ["4h"],
            },
        }
        with patch("app.worker.celery_app") as mock_celery:
            response = await client.post(
                "/api/advisor/deploy",
                json={"plan": plan_4h},
                headers=registered_user,
            )

        assert response.status_code == 200
        mock_celery.send_task.assert_called_once_with(
            "backfill_symbols",
            args=[["BTC/USDT", "ETH/USDT"], ["4h"]],
        )

    @pytest.mark.asyncio
    async def test_deploy_single_crypto(self, client, registered_user):
        """Deploy with a single selected crypto."""
        single_plan = {
            **MOCK_PLAN,
            "selected_cryptos": [
                {"symbol": "BTC/USDT", "reason": "Only strong setup"},
            ],
        }
        with patch("app.worker.celery_app"):
            response = await client.post(
                "/api/advisor/deploy",
                json={"plan": single_plan},
                headers=registered_user,
            )

        assert response.status_code == 200
        assert response.json()["symbols_count"] == 1

    @pytest.mark.asyncio
    async def test_deploy_multiple_strategies_independent(self, client, registered_user):
        """Deploying twice creates two separate strategies."""
        with patch("app.worker.celery_app"):
            resp1 = await client.post(
                "/api/advisor/deploy",
                json={"plan": MOCK_PLAN},
                headers=registered_user,
            )
            resp2 = await client.post(
                "/api/advisor/deploy",
                json={"plan": MOCK_PLAN},
                headers=registered_user,
            )

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json()["strategy_id"] != resp2.json()["strategy_id"]
