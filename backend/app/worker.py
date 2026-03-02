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
    "app.tasks.send_alerts",
    "app.tasks.hmm_train",
    "app.tasks.backtest_task",
    "app.tasks.check_correlations",
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
    "reconcile-broker-state-5m": {
        "task": "reconcile_broker_state",
        "schedule": 300.0,
    },
    "send-daily-summary": {
        "task": "send_daily_summary",
        "schedule": crontab(hour=17, minute=0),
    },
    "retrain-hmm-weekly": {
        "task": "train_hmm_regime",
        "schedule": crontab(hour=2, minute=0, day_of_week="sunday"),
    },
    "check-correlations-5m": {
        "task": "check_correlations",
        "schedule": 300.0,
    },
}
