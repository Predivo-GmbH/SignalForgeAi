"""Import smoke test -- ensures every module in the app loads without errors.

This catches:
  - Missing function/class imports (like _fetch_trading_holdings)
  - Circular imports
  - Missing third-party dependencies
  - Syntax errors

If this test fails, the app CANNOT start. Fix it before committing.
"""

import importlib
import pkgutil

import pytest

import app

# ---------------------------------------------------------------------------
# Level A: All modules under app/ must import cleanly
# ---------------------------------------------------------------------------


def _iter_modules(package):
    """Recursively yield all module paths under a package."""
    prefix = package.__name__ + "."
    for _importer, modname, _ispkg in pkgutil.walk_packages(
        package.__path__, prefix=prefix,
    ):
        yield modname


# __main__ calls sys.exit() via argparse — skip it
ALL_MODULES = sorted(
    m for m in _iter_modules(app) if m != "app.__main__"
)


@pytest.mark.parametrize("module_path", ALL_MODULES)
def test_module_imports(module_path):
    """Every module under app/ must import without errors."""
    importlib.import_module(module_path)


# ---------------------------------------------------------------------------
# Level B: Deferred imports (inside function bodies) must resolve
#
# These are "from X import Y" statements inside route handlers and helpers.
# Python only evaluates them at call time, so a simple module import won't
# catch a missing attribute. We validate each one explicitly.
#
# MAINTAINER NOTE: When you add a deferred import to any file under app/,
# add a corresponding entry here.
# ---------------------------------------------------------------------------

DEFERRED_IMPORTS = [
    # --- app/api/simulation.py ---
    ("app.api.holdings", "_fetch_exchange_holdings"),
    ("app.api.holdings", "_fetch_manual_holdings"),
    ("app.api.holdings", "_fetch_trading_holdings"),
    ("app.api.holdings", "_fetch_prices"),
    ("app.execution.position_manager", "PositionManagerDB"),
    # --- app/api/holdings.py ---
    ("app.core.redis_client", "redis_client"),
    ("app.data.coingecko", "fetch_coin_metadata"),
    ("app.data.coingecko", "fetch_prices"),
    # --- app/api/ai_usage.py ---
    ("app.advisor.anthropic_admin", "available"),
    ("app.advisor.anthropic_admin", "fetch_cost_report"),
    ("app.advisor.anthropic_admin", "fetch_usage_report"),
    ("app.core.database", "async_session"),
    # --- app/api/system_status.py ---
    ("app.worker", "celery_app"),
    ("app.models.candle", "Candle"),
    ("app.models.pipeline_log", "PipelineLog"),
    ("app.models.signal", "Signal"),
    # --- app/api/positions.py ---
    ("app.execution.correlation_monitor", "CorrelationMonitor"),
    ("app.execution.drawdown_breaker", "DrawdownBreaker"),
    ("app.execution.cppi", "CPPIManager"),
    ("app.models.strategy", "Strategy"),
    # --- app/api/strategies.py ---
    ("app.auth.totp", "decrypt_totp_secret"),
    ("app.auth.totp", "verify_backup_code"),
    ("app.auth.totp", "verify_totp_code"),
    ("app.advisor.risk_tuner", "RiskTuner"),
    ("app.advisor.feedback_synthesizer", "FeedbackSynthesizer"),
    ("app.models.ai_insight", "FeedbackRule"),
    ("app.models.ai_insight", "AIInsight"),
    ("app.models.position", "Position"),
    # --- app/api/advisor.py ---
    ("app.advisor.analyzer", "TechnicalAnalyzer"),
    ("app.advisor.scanner", "MarketScanner"),
    ("app.advisor.planner", "InvestmentPlanner"),
    ("app.api.strategies", "StrategyConfig"),
    # --- app/api/backtests.py ---
    ("app.tasks.backtest_task", "run_backtest_task"),
    ("app.models.backtest_result", "BacktestResult"),
    ("app.backtest.optimizer", "WalkForwardOptimizer"),
    ("app.backtest.portfolio_runner", "run_portfolio_backtest"),
    # --- app/api/market.py ---
    ("app.data.ingestion", "CCXTIngestion"),
    ("app.data.coingecko", "fetch_ohlc"),
    # --- app/api/regime.py ---
    ("app.engine.layers.hmm_regime", "HMMRegimeModel"),
    ("app.execution.regime_allocator", "RegimeAllocator"),
    # --- app/api/alerts.py ---
    ("app.models.user", "User"),
    # --- app/api/analytics.py ---
    ("app.data.storage", "CandleStorage"),
    # --- app/auth/router.py ---
    ("app.core.token_blacklist", "is_token_blacklisted"),
    ("app.core.token_blacklist", "are_user_tokens_invalid"),
    ("app.core.token_blacklist", "blacklist_token"),
    ("app.core.token_blacklist", "blacklist_all_user_tokens"),
    # --- app/tasks (Celery tasks) ---
    ("app.tasks.task_utils", "task_lock"),
    ("app.core.database", "task_session"),
    ("app.engine.pipeline", "SignalPipeline"),
    ("app.engine.layers.feedback_filter", "FeedbackFilter"),
    ("app.engine.layers.risk", "RiskConfig"),
    ("app.engine.layers.trend", "TrendFilter"),
    ("app.execution.kelly", "KellyCalculator"),
    ("app.advisor.multi_tf_analyzer", "MultiTimeframeAnalyzer"),
    ("app.advisor.signal_quality", "SignalQualityEvaluator"),
    ("app.core.email", "send_email"),
]


@pytest.mark.parametrize(
    "module_path,attr_name",
    DEFERRED_IMPORTS,
    ids=[f"{m}.{a}" for m, a in DEFERRED_IMPORTS],
)
def test_deferred_import_exists(module_path, attr_name):
    """Validate that functions imported inside route handlers actually exist."""
    mod = importlib.import_module(module_path)
    assert hasattr(mod, attr_name), (
        f"{module_path}.{attr_name} does not exist! "
        f"A module is importing this but it was never defined."
    )


# ---------------------------------------------------------------------------
# Level C: FastAPI app loads and routes are registered
# ---------------------------------------------------------------------------


def test_fastapi_app_loads():
    """The FastAPI app must load without errors."""
    from app.main import app as fastapi_app

    assert fastapi_app is not None
    route_paths = [
        getattr(r, "path", "") for r in fastapi_app.routes
    ]
    # Verify key routers are mounted
    assert any("/simulation" in p for p in route_paths), "simulation router not mounted"
    assert any("/holdings" in p for p in route_paths), "holdings router not mounted"
    assert any("/engine" in p for p in route_paths), "engine router not mounted"
    assert any("/system" in p for p in route_paths), "system status router not mounted"
    assert any("/positions" in p for p in route_paths), "positions router not mounted"
