"""Tests for adaptive risk tuner."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from app.advisor.risk_tuner import RiskTuner


def _make_trade(pnl, confluence_score=55, exit_reason="target_hit", risk_reward=1.8):
    """Create a mock trade object."""
    t = MagicMock()
    t.pnl = pnl
    t.confluence_score = confluence_score
    t.exit_reason = exit_reason
    t.risk_reward = risk_reward
    t.exit_time = datetime.now(timezone.utc)
    t.created_at = datetime.now(timezone.utc)
    return t


# ---------------------------------------------------------------------------
# Metrics computation
# ---------------------------------------------------------------------------


def test_compute_metrics_basic():
    tuner = RiskTuner()
    trades = [
        _make_trade(100),
        _make_trade(50),
        _make_trade(-30, exit_reason="stop_loss"),
        _make_trade(-20, exit_reason="stop_loss"),
        _make_trade(80),
    ]
    metrics = tuner._compute_metrics(trades)

    assert metrics["total_trades"] == 5
    assert metrics["win_rate"] == 0.6
    assert metrics["stop_loss_hit_rate"] == 1.0  # 2/2 losses are SL


def test_compute_metrics_empty():
    tuner = RiskTuner()
    metrics = tuner._compute_metrics([])
    assert metrics["total_trades"] == 0
    assert metrics["win_rate"] == 0


# ---------------------------------------------------------------------------
# Validation — parameter bounds
# ---------------------------------------------------------------------------


def test_validate_adjustments_clamps_to_bounds():
    tuner = RiskTuner()
    current = {"min_confluence": 50, "max_risk_per_trade": 0.02}

    adjustments = {
        "min_confluence": 200,  # Over max (100)
        "max_risk_per_trade": 0.001,  # Under min (0.005)
    }

    validated = tuner._validate_adjustments(adjustments, current)

    # min_confluence: 200 clamped to 100, but max 20% change from 50 = 60
    assert validated["min_confluence"] <= 60

    # max_risk_per_trade: 0.001 clamped to 0.005, but 20% of 0.02 = 0.004, so 0.02-0.004=0.016
    assert validated["max_risk_per_trade"] >= 0.005


def test_validate_adjustments_20pct_limit():
    tuner = RiskTuner()
    current = {"min_confluence": 50}

    # Try to change from 50 to 80 (60% change — should be limited)
    adjustments = {"min_confluence": 80}
    validated = tuner._validate_adjustments(adjustments, current)

    assert validated["min_confluence"] == 60  # 50 + 20% = 60


def test_validate_adjustments_ignores_unknown_params():
    tuner = RiskTuner()
    current = {"min_confluence": 50}
    adjustments = {"unknown_param": 42, "min_confluence": 55}
    validated = tuner._validate_adjustments(adjustments, current)
    assert "unknown_param" not in validated
    assert "min_confluence" in validated


def test_validate_adjustments_skips_unchanged():
    tuner = RiskTuner()
    current = {"min_confluence": 50}
    adjustments = {"min_confluence": 50}  # No change
    validated = tuner._validate_adjustments(adjustments, current)
    assert validated == {}


# ---------------------------------------------------------------------------
# Algorithmic fallback
# ---------------------------------------------------------------------------


def test_algorithmic_fallback_low_win_rate():
    tuner = RiskTuner()
    metrics = {
        "win_rate": 0.30,
        "stop_loss_hit_rate": 0.40,
        "max_drawdown_pct": 0.05,
    }
    current = {
        "min_confluence": 50,
        "max_risk_per_trade": 0.02,
        "atr_sl_multiplier": 2.0,
    }
    result = tuner._algorithmic_fallback(metrics, current)
    assert result["adjustments"]["min_confluence"] == 55


def test_algorithmic_fallback_high_sl_rate():
    tuner = RiskTuner()
    metrics = {
        "win_rate": 0.50,
        "stop_loss_hit_rate": 0.70,
        "max_drawdown_pct": 0.05,
    }
    current = {
        "min_confluence": 50,
        "max_risk_per_trade": 0.02,
        "atr_sl_multiplier": 2.0,
    }
    result = tuner._algorithmic_fallback(metrics, current)
    assert result["adjustments"]["atr_sl_multiplier"] == 2.2


def test_algorithmic_fallback_no_changes_needed():
    tuner = RiskTuner()
    metrics = {
        "win_rate": 0.55,
        "stop_loss_hit_rate": 0.40,
        "max_drawdown_pct": 0.05,
    }
    current = {
        "min_confluence": 50,
        "max_risk_per_trade": 0.02,
        "atr_sl_multiplier": 2.0,
    }
    result = tuner._algorithmic_fallback(metrics, current)
    assert result["adjustments"] == {}


# ---------------------------------------------------------------------------
# Full tune — insufficient trades
# ---------------------------------------------------------------------------


async def test_tune_insufficient_trades():
    tuner = RiskTuner()
    strategy = MagicMock()
    strategy.id = "test-id"
    strategy.config = {"min_confluence": 50}
    strategy.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    # First execute: signal count query (returns > 0 to skip no-signal fallback)
    signal_count_result = MagicMock()
    signal_count_result.scalar.return_value = 5

    # Second execute: trades query (returns < 5 trades)
    trade_result = MagicMock()
    trade_result.scalars.return_value.all.return_value = [
        _make_trade(100),
        _make_trade(-50),
    ]

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[signal_count_result, trade_result])

    result = await tuner.tune(strategy, mock_db)
    assert result["adjustments"] == {}
    assert "Insufficient" in result["reasoning"]


async def test_tune_no_signals_fallback():
    """Strategy active 48h+ with zero signals should trigger pipeline loosening."""
    tuner = RiskTuner()
    strategy = MagicMock()
    strategy.id = "test-id"
    strategy.config = {
        "min_confluence": 50,
        "min_trigger_count": 2,
        "trigger_lookback_candles": 1,
        "ema_slope_threshold": 0.001,
    }
    strategy.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    # Signal count = 0
    signal_count_result = MagicMock()
    signal_count_result.scalar.return_value = 0

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=signal_count_result)

    result = await tuner.tune(strategy, mock_db)
    adj = result["adjustments"]
    # Should loosen at least one pipeline sensitivity param
    assert adj.get("min_trigger_count", 2) < 2 or adj.get("trigger_lookback_candles", 1) > 1
    assert "zero signals" in result["reasoning"]
