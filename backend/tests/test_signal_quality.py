"""Tests for signal quality evaluator and multi-timeframe analyzer."""

from unittest.mock import AsyncMock, patch

import pytest

from app.advisor.signal_quality import SignalQualityEvaluator, build_quality_user_message

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_signal_data():
    return {
        "action": "BUY",
        "symbol": "BTC/USDT",
        "timeframe": "1h",
        "regime": "trending",
        "trend_direction": "bullish",
        "trend_strength": 0.0035,
        "confluence_score": 68,
        "triggers": ["macd_crossover", "rsi_midline"],
        "risk_reward": 2.15,
    }


@pytest.fixture
def sample_confluence_details():
    return {
        "fibonacci_alignment": {
            "hit": True, "weight": 12, "earned": 12,
            "zone_type": "fibonacci_golden",
        },
        "sr_overlap": {
            "hit": True, "weight": 12, "earned": 12, "bounces": 4,
        },
        "vwap_proximity": {
            "hit": False, "weight": 8, "earned": 0,
            "vwap": 45200.5, "in_zone": False,
        },
        "rsi_confirmation": {
            "hit": True, "weight": 8, "earned": 8,
            "rsi": 35.2, "trend": "bullish",
        },
        "macd_momentum": {
            "hit": True, "weight": 8, "earned": 8, "histogram": 0.5,
        },
        "volume_node": {
            "hit": True, "weight": 8, "earned": 8,
            "avg_zone_vol": 1500, "avg_total_vol": 1000,
        },
        "candlestick_pattern": {"hit": False, "weight": 7, "earned": 0, "pattern": "none"},
        "multi_tf_fib": {"hit": True, "weight": 10, "earned": 10, "zone_strength": 0.75},
        "stochastic_cross": {"hit": False, "weight": 5, "earned": 0, "slow_k": 45, "slow_d": 50},
        "bollinger_position": {"hit": True, "weight": 5, "earned": 5, "bb_pct": 0.15},
        "ichimoku_cloud": {"hit": False, "weight": 5, "earned": 0, "cloud_position": "inside"},
        "obv_trend": {"hit": True, "weight": 5, "earned": 5, "obv_slope": 150.5},
        "williams_r_extreme": {"hit": False, "weight": 4, "earned": 0, "williams_r": -55.0},
        "cci_momentum": {"hit": False, "weight": 3, "earned": 0, "cci": 50.0},
    }


@pytest.fixture
def sample_candle_summary():
    return [
        {"open": 45300.0, "high": 45450.0, "low": 45200.0, "close": 45400.0, "volume": 1200.0},
        {"open": 45250.0, "high": 45350.0, "low": 45150.0, "close": 45300.0, "volume": 1100.0},
        {"open": 45100.0, "high": 45280.0, "low": 45050.0, "close": 45250.0, "volume": 950.0},
        {"open": 45050.0, "high": 45150.0, "low": 44950.0, "close": 45100.0, "volume": 800.0},
        {"open": 44900.0, "high": 45080.0, "low": 44850.0, "close": 45050.0, "volume": 900.0},
    ]


# ---------------------------------------------------------------------------
# User message building
# ---------------------------------------------------------------------------


def test_build_quality_user_message(
    sample_signal_data, sample_confluence_details, sample_candle_summary,
):
    msg = build_quality_user_message(
        sample_signal_data, sample_confluence_details, sample_candle_summary,
    )
    assert "BUY" in msg
    assert "BTC/USDT" in msg
    assert "fibonacci_alignment" in msg
    assert "HIT" in msg
    assert "MISS" in msg
    assert "45400.00" in msg  # candle close


def test_build_quality_user_message_with_mtf(
    sample_signal_data, sample_confluence_details, sample_candle_summary,
):
    mtf_data = {
        "mtf_confidence": 85,
        "timeframe_alignment": "aligned",
        "reasoning": "All timeframes bullish.",
    }
    msg = build_quality_user_message(
        sample_signal_data, sample_confluence_details, sample_candle_summary, mtf_data,
    )
    assert "Multi-timeframe analysis" in msg
    assert "aligned" in msg


# ---------------------------------------------------------------------------
# Evaluator — rejects signal when Claude unavailable
# ---------------------------------------------------------------------------


async def test_evaluator_rejects_when_claude_unavailable(
    sample_signal_data, sample_confluence_details, sample_candle_summary,
):
    """When Claude is unavailable, signals must be rejected — no trading without AI."""
    with patch("app.advisor.signal_quality.claude_client") as mock_client:
        mock_client.ask_json = AsyncMock(return_value=None)
        mock_client.available = False

        evaluator = SignalQualityEvaluator()
        result = await evaluator.evaluate(
            sample_signal_data, sample_confluence_details, sample_candle_summary,
        )

    assert result["quality_score"] == 0
    assert result["recommendation"] == "reject"
    assert result["risk_adjustments"]["position_size_factor"] == 0.0


# ---------------------------------------------------------------------------
# Evaluator — parses valid Claude response
# ---------------------------------------------------------------------------


async def test_evaluator_parses_claude_response(
    sample_signal_data, sample_confluence_details, sample_candle_summary,
):
    claude_response = {
        "quality_score": 75,
        "recommendation": "confirm",
        "reasoning": "Strong bullish setup with good confluence.",
        "risk_adjustments": {
            "position_size_factor": 0.9,
            "reasoning": "Slightly declining volume",
        },
    }

    with patch("app.advisor.signal_quality.claude_client") as mock_client:
        mock_client.ask_json = AsyncMock(return_value=claude_response)

        evaluator = SignalQualityEvaluator()
        result = await evaluator.evaluate(
            sample_signal_data, sample_confluence_details, sample_candle_summary,
        )

    assert result["quality_score"] == 75
    assert result["recommendation"] == "confirm"
    assert "Strong bullish" in result["reasoning"]
    assert result["risk_adjustments"]["position_size_factor"] == 0.9


# ---------------------------------------------------------------------------
# Evaluator — validates response bounds
# ---------------------------------------------------------------------------


async def test_evaluator_clamps_quality_score(
    sample_signal_data, sample_confluence_details, sample_candle_summary,
):
    claude_response = {
        "quality_score": 150,  # over 100 — should clamp
        "recommendation": "invalid_value",
        "reasoning": "test",
        "risk_adjustments": {"position_size_factor": 5.0},  # over 1.5 — should clamp
    }

    with patch("app.advisor.signal_quality.claude_client") as mock_client:
        mock_client.ask_json = AsyncMock(return_value=claude_response)

        evaluator = SignalQualityEvaluator()
        result = await evaluator.evaluate(
            sample_signal_data, sample_confluence_details, sample_candle_summary,
        )

    assert result["quality_score"] == 100  # clamped
    assert result["recommendation"] == "confirm"  # defaulted
    assert result["risk_adjustments"]["position_size_factor"] == 1.5  # clamped


# ---------------------------------------------------------------------------
# Evaluator — feature flag off (deliberate config, not AI unavailable)
# ---------------------------------------------------------------------------


async def test_evaluator_disabled_by_feature_flag(
    sample_signal_data, sample_confluence_details, sample_candle_summary,
):
    """When deliberately disabled by config, passthrough is OK."""
    with patch("app.advisor.signal_quality.settings") as mock_settings:
        mock_settings.ai_signal_quality_enabled = False

        evaluator = SignalQualityEvaluator()
        result = await evaluator.evaluate(
            sample_signal_data, sample_confluence_details, sample_candle_summary,
        )

    assert result["quality_score"] == 68
    assert result["recommendation"] == "confirm"
