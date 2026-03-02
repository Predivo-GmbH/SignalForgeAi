"""Tests for the flush_ai_usage Celery task."""

import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.models.ai_insight import AIInsight
from tests.conftest import test_session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeRedis:
    """Minimal Redis stub that supports lpop on a pre-loaded queue."""

    def __init__(self, items=None):
        self._queue = list(items or [])

    def lpop(self, key):
        if self._queue:
            return self._queue.pop(0)
        return None


def _make_record(**overrides) -> dict:
    """Return a valid AI usage record dict, with optional field overrides."""
    base = {
        "insight_type": "investment_plan",
        "model_used": "claude-sonnet-4-6-20250627",
        "input_tokens": 500,
        "output_tokens": 200,
        "latency_ms": 1200,
        "cost_usd": 0.0045,
        "created_at": "2026-03-02T10:00:00+00:00",
    }
    base.update(overrides)
    return base


@pytest.fixture
def mock_task_session():
    """Yield an async-context-manager that uses the SQLite test session."""

    @asynccontextmanager
    async def _mock():
        async with test_session() as session:
            yield session

    return _mock


# ---------------------------------------------------------------------------
# Task registration
# ---------------------------------------------------------------------------

def test_flush_task_registered():
    """flush_ai_usage is registered with the correct Celery task name."""
    from app.tasks.flush_ai_usage import flush_ai_usage

    assert flush_ai_usage.name == "flush_ai_usage"


# ---------------------------------------------------------------------------
# Core flush behaviour (testing _flush_async directly)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_flush_empty_queue(mock_task_session):
    """An empty Redis queue results in {\"flushed\": 0} and no DB rows."""
    from app.tasks.flush_ai_usage import _flush_async

    fake_redis = FakeRedis(items=[])

    with (
        patch("redis.from_url", return_value=fake_redis),
        patch("app.core.database.task_session", mock_task_session),
    ):
        result = await _flush_async()

    assert result == {"flushed": 0}


@pytest.mark.asyncio
async def test_flush_single_record(mock_task_session):
    """One record in the queue is flushed and persisted as an AIInsight row."""
    from app.tasks.flush_ai_usage import _flush_async

    record = _make_record()
    fake_redis = FakeRedis(items=[json.dumps(record)])

    with (
        patch("redis.from_url", return_value=fake_redis),
        patch("app.core.database.task_session", mock_task_session),
    ):
        result = await _flush_async()

    assert result == {"flushed": 1}

    async with test_session() as session:
        rows = (await session.execute(select(AIInsight))).scalars().all()
        assert len(rows) == 1


@pytest.mark.asyncio
async def test_flush_multiple_records(mock_task_session):
    """Multiple records are all flushed in a single run."""
    from app.tasks.flush_ai_usage import _flush_async

    records = [
        json.dumps(_make_record(insight_type="investment_plan")),
        json.dumps(_make_record(insight_type="risk_tuning")),
        json.dumps(_make_record(insight_type="trade_feedback")),
    ]
    fake_redis = FakeRedis(items=records)

    with (
        patch("redis.from_url", return_value=fake_redis),
        patch("app.core.database.task_session", mock_task_session),
    ):
        result = await _flush_async()

    assert result == {"flushed": 3}

    async with test_session() as session:
        rows = (await session.execute(select(AIInsight))).scalars().all()
        assert len(rows) == 3


@pytest.mark.asyncio
async def test_flush_skips_malformed_json(mock_task_session):
    """Malformed JSON entries are silently skipped; valid ones still flush."""
    from app.tasks.flush_ai_usage import _flush_async

    items = [
        json.dumps(_make_record()),
        "NOT-VALID-JSON{{{",
    ]
    fake_redis = FakeRedis(items=items)

    with (
        patch("redis.from_url", return_value=fake_redis),
        patch("app.core.database.task_session", mock_task_session),
    ):
        result = await _flush_async()

    assert result == {"flushed": 1}

    async with test_session() as session:
        rows = (await session.execute(select(AIInsight))).scalars().all()
        assert len(rows) == 1


@pytest.mark.asyncio
async def test_flush_record_fields_correct(mock_task_session):
    """All fields from the usage record are correctly stored on AIInsight."""
    from app.tasks.flush_ai_usage import _flush_async

    record = _make_record(
        insight_type="signal_quality",
        model_used="claude-sonnet-4-6-20250627",
        input_tokens=750,
        output_tokens=320,
        latency_ms=980,
        cost_usd=0.0062,
        created_at="2026-03-02T14:30:00+00:00",
    )
    fake_redis = FakeRedis(items=[json.dumps(record)])

    with (
        patch("redis.from_url", return_value=fake_redis),
        patch("app.core.database.task_session", mock_task_session),
    ):
        result = await _flush_async()

    assert result == {"flushed": 1}

    async with test_session() as session:
        row = (await session.execute(select(AIInsight))).scalar_one()

        assert row.insight_type == "signal_quality"
        assert row.model_used == "claude-sonnet-4-6-20250627"
        assert row.input_tokens == 750
        assert row.output_tokens == 320
        assert row.latency_ms == 980
        assert row.cost_usd == pytest.approx(0.0062)
        expected_dt = datetime(2026, 3, 2, 14, 30)
        assert row.created_at.replace(tzinfo=None) == expected_dt
