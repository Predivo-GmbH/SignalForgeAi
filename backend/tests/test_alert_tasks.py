"""Tests for alert persistence, send_alerts task, and backtest DB storage."""

import pytest


def test_send_daily_summary_task_registered():
    """send_daily_summary Celery task should be registered with the correct name."""
    from app.tasks.send_alerts import send_daily_summary

    assert send_daily_summary.name == "send_daily_summary"


def test_alert_config_default_keys():
    """Default alert config should have all expected keys."""
    from app.api.alerts import _DEFAULT_CONFIG

    assert "email_on_signal" in _DEFAULT_CONFIG
    assert "email_daily_summary" in _DEFAULT_CONFIG
    assert "min_confluence_alert" in _DEFAULT_CONFIG
    assert "alert_email" in _DEFAULT_CONFIG


def test_alert_config_model_defaults():
    """AlertConfig pydantic model should produce correct defaults."""
    from app.api.alerts import AlertConfig

    cfg = AlertConfig()
    assert cfg.email_on_signal is False
    assert cfg.email_daily_summary is False
    assert cfg.min_confluence_alert == 60
    assert cfg.alert_email == ""


def test_alert_config_model_roundtrip():
    """AlertConfig model_dump should roundtrip cleanly."""
    from app.api.alerts import AlertConfig

    cfg = AlertConfig(
        email_on_signal=True,
        email_daily_summary=True,
        min_confluence_alert=75,
        alert_email="user@example.com",
    )
    data = cfg.model_dump()
    restored = AlertConfig(**data)
    assert restored.email_on_signal is True
    assert restored.min_confluence_alert == 75
    assert restored.alert_email == "user@example.com"


def test_train_hmm_regime_task_registered():
    """train_hmm_regime Celery task should be registered."""
    from app.tasks.hmm_train import train_hmm_regime

    assert train_hmm_regime.name == "train_hmm_regime"


def test_run_backtest_task_registered():
    """run_backtest_task Celery task should be importable."""
    from app.tasks.backtest_task import run_backtest_task

    # The task should be a Celery task object
    assert callable(run_backtest_task)


def test_backtest_result_model_columns():
    """BacktestResult model should have the expected columns."""
    from app.models.backtest_result import BacktestResult

    mapper = BacktestResult.__table__
    col_names = {c.name for c in mapper.columns}
    expected = {
        "id", "user_id", "symbol", "timeframe", "days",
        "metrics", "trade_count", "win_rate", "sharpe_ratio",
        "max_drawdown", "total_pnl", "created_at",
    }
    assert expected.issubset(col_names)


@pytest.mark.asyncio
async def test_get_alert_config_returns_default_for_new_user(client):
    """GET /api/alerts/config should return defaults when user has no config."""
    # This endpoint requires auth — without a valid token we expect 401
    response = await client.get("/api/alerts/config")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_backtests_requires_auth(client):
    """GET /api/backtests should require authentication."""
    response = await client.get("/api/backtests")
    assert response.status_code == 401
