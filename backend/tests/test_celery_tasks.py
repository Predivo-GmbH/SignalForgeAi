"""Tests for Celery tasks configuration."""


def test_ingest_candles_task_registered():
    """Verify ingest_candles task can be imported."""
    from app.tasks.ingest_candles import ingest_candles

    assert ingest_candles.name == "ingest_candles"


def test_run_pipeline_task_registered():
    """Verify run_signal_pipeline task can be imported."""
    from app.tasks.run_pipeline import run_signal_pipeline

    assert run_signal_pipeline.name == "run_signal_pipeline"


def test_celery_beat_schedule_configured():
    """Verify Celery Beat schedule has all expected tasks."""
    from app.worker import celery_app

    schedule = celery_app.conf.beat_schedule
    expected_tasks = [
        "ingest-candles-1m",
        "run-signal-pipeline-5m",
        "execute-pending-signals-30s",
        "poll-order-status-15s",
        "manage-positions-1m",
        "send-daily-summary",
        "retrain-hmm-weekly",
        "check-correlations-5m",
        "pattern-analysis-daily",
        "adaptive-risk-tuning-daily",
        "feedback-synthesis-daily",
        "flush-ai-usage-1m",
        "snapshot-simulation-1h",
    ]
    for task_name in expected_tasks:
        assert task_name in schedule, f"Missing task: {task_name}"
