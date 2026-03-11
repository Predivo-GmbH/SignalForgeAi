"""Celery application for SignalForge async tasks."""

from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "signalforge",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Global task timeouts — override per-task for long-running ones
    task_time_limit=600,        # 10 min hard kill
    task_soft_time_limit=540,   # 9 min soft warning (raises SoftTimeLimitExceeded)
    # Acknowledge tasks after they complete (not before)
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# Auto-discover tasks in the app.tasks package
celery_app.autodiscover_tasks(["app.tasks"])

# Explicit includes as fallback for autodiscovery
celery_app.conf.include = [
    "app.tasks.ingest_candles",
    "app.tasks.run_pipeline",
    "app.tasks.execute_signals",
    "app.tasks.poll_orders",
    "app.tasks.manage_positions",
    "app.tasks.reconcile",
    "app.tasks.hmm_train",
    "app.tasks.backtest_task",
    "app.tasks.risk_tuning",
    "app.tasks.feedback_synthesis",
    "app.tasks.pattern_analysis",
    "app.tasks.flush_ai_usage",
    "app.tasks.simulation_snapshot",
    "app.tasks.sync_portfolio_symbols",
    "app.tasks.expand_symbol_universe",
    "app.tasks.promote_universe_candidates",
]

# ---------------------------------------------------------------------------
# Celery Beat schedule — periodic tasks
# ---------------------------------------------------------------------------
celery_app.conf.beat_schedule = {
    "ingest-candles-1m": {
        "task": "ingest_candles",
        "schedule": 60.0,
    },
    "run-signal-pipeline-5m": {
        "task": "run_signal_pipeline",
        "schedule": 300.0,
    },
    "execute-pending-signals-30s": {
        "task": "execute_pending_signals",
        "schedule": 30.0,
    },
    "poll-order-status-15s": {
        "task": "poll_order_status",
        "schedule": 15.0,
    },
    "manage-positions-1m": {
        "task": "manage_positions",
        "schedule": 60.0,
    },
    # reconcile-broker-state: disabled (no-op until live broker sync is implemented)
    "retrain-hmm-weekly": {
        "task": "train_hmm_regime",
        "schedule": crontab(hour=2, minute=0, day_of_week="sunday"),
    },
    "pattern-analysis-daily": {
        "task": "periodic_pattern_analysis",
        "schedule": crontab(hour=2, minute=30),
    },
    "adaptive-risk-tuning-daily": {
        "task": "adaptive_risk_tuning",
        "schedule": crontab(hour=3, minute=0),
    },
    "feedback-synthesis-daily": {
        "task": "synthesize_feedback_rules",
        "schedule": crontab(hour=4, minute=0),
    },
    "flush-ai-usage-1m": {
        "task": "flush_ai_usage",
        "schedule": 60.0,
    },
    "snapshot-simulation-1h": {
        "task": "snapshot_simulation",
        "schedule": 3600.0,
    },
    "sync-portfolio-symbols-5m": {
        "task": "sync_portfolio_symbols",
        "schedule": 300.0,
    },
    "expand-symbol-universe-6h": {
        "task": "expand_symbol_universe",
        "schedule": 21600.0,
    },
}
