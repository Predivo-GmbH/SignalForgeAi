"""System status API — comprehensive health monitoring for all services."""

import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status")
@limiter.limit("60/minute")
async def get_system_status(
    request: Request,
    _user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return comprehensive system health — DB, Redis, worker, beat, data freshness."""
    now = datetime.now(timezone.utc)

    result = {
        "overall": "healthy",
        "checked_at": now.isoformat(),
        "services": {
            "database": {"status": "unknown"},
            "redis": {"status": "unknown"},
            "worker": {"status": "unknown"},
            "beat": {"status": "unknown"},
        },
        "data": {
            "candles_fresh": False,
            "last_candle_at": None,
            "candle_age_seconds": None,
            "pipeline_fresh": False,
            "last_signal_at": None,
            "signal_age_seconds": None,
        },
        "issues": [],
    }

    # --- 1. Database ---
    try:
        await db.execute(text("SELECT 1"))
        result["services"]["database"] = {"status": "ok"}
    except Exception:
        logger.warning("DB health check failed", exc_info=True)
        result["services"]["database"] = {"status": "error", "detail": "Connection failed"}
        result["issues"].append("Database is unreachable")
        result["overall"] = "critical"

    # --- 2. Redis ---
    try:
        from app.core.redis_client import redis_client

        await redis_client.ping()
        result["services"]["redis"] = {"status": "ok"}
    except Exception:
        logger.warning("Redis health check failed", exc_info=True)
        result["services"]["redis"] = {"status": "error", "detail": "Connection failed"}
        result["issues"].append("Redis is unreachable")
        result["overall"] = "critical"

    # --- 3. Celery worker ---
    try:
        from app.worker import celery_app

        def _check_worker():
            insp = celery_app.control.inspect(timeout=2.0)
            return insp.ping()

        ping_result = await asyncio.to_thread(_check_worker)
        if ping_result:
            result["services"]["worker"] = {"status": "ok"}
        else:
            result["services"]["worker"] = {"status": "down"}
            result["issues"].append("Celery worker is not responding")
            if result["overall"] != "critical":
                result["overall"] = "degraded"
    except Exception:
        logger.warning("Celery worker health check failed", exc_info=True)
        result["services"]["worker"] = {"status": "error", "detail": "Connection failed"}
        result["issues"].append("Cannot reach Celery worker")
        if result["overall"] != "critical":
            result["overall"] = "degraded"

    # --- 4. Beat scheduler (inferred from data freshness) ---
    # Beat doesn't have a direct ping. We detect it by checking if scheduled
    # tasks are producing results — specifically candle ingestion (runs every 60s).
    try:
        from app.models.candle import Candle

        last_candle_row = await db.execute(
            select(func.max(Candle.time))
        )
        last_candle_time = last_candle_row.scalar()

        if last_candle_time:
            if last_candle_time.tzinfo is None:
                last_candle_time = last_candle_time.replace(tzinfo=timezone.utc)
            age = (now - last_candle_time).total_seconds()
            result["data"]["last_candle_at"] = last_candle_time.isoformat()
            result["data"]["candle_age_seconds"] = round(age)

            # Candles ingest every 60s. If last candle is older than 5 min,
            # beat is likely down or ingestion is failing.
            if age < 300:
                result["data"]["candles_fresh"] = True
                result["services"]["beat"] = {"status": "ok", "last_candle_age_s": round(age)}
            else:
                result["data"]["candles_fresh"] = False
                result["services"]["beat"] = {
                    "status": "stale",
                    "last_candle_age_s": round(age),
                    "detail": f"Last candle {round(age / 60)}m ago (expected <5m)",
                }
                result["issues"].append(
                    f"Beat scheduler may be down — no candles for {round(age / 60)}m"
                )
                if result["overall"] == "healthy":
                    result["overall"] = "degraded"
        else:
            result["data"]["candles_fresh"] = False
            result["services"]["beat"] = {
                "status": "stale",
                "detail": "No candles in database at all",
            }
            result["issues"].append(
                "No candles in database — beat scheduler or ingestion is not running"
            )
            if result["overall"] == "healthy":
                result["overall"] = "degraded"
    except Exception:
        logger.warning("Beat scheduler health check failed", exc_info=True)
        result["services"]["beat"] = {"status": "unknown", "detail": "Check failed"}

    # --- 5. Pipeline run freshness (from PipelineLog) ---
    # PipelineLog tracks ALL evaluations, including blocked ones.
    # This shows when the pipeline last ran, regardless of whether
    # any signals passed.
    try:
        from app.models.pipeline_log import PipelineLog

        last_eval_row = await db.execute(
            select(func.max(PipelineLog.created_at))
        )
        last_eval_time = last_eval_row.scalar()

        if last_eval_time:
            if last_eval_time.tzinfo is None:
                last_eval_time = last_eval_time.replace(tzinfo=timezone.utc)
            eval_age = (now - last_eval_time).total_seconds()
            result["data"]["last_pipeline_run_at"] = last_eval_time.isoformat()
            result["data"]["pipeline_age_seconds"] = round(eval_age)
            # Pipeline runs every 5min. Fresh if under 10min.
            result["data"]["pipeline_fresh"] = eval_age < 600
        else:
            result["data"]["last_pipeline_run_at"] = None
            result["data"]["pipeline_age_seconds"] = None
            result["data"]["pipeline_fresh"] = result["data"]["candles_fresh"]
    except Exception:
        logger.warning("Failed to check pipeline run freshness", exc_info=True)

    # --- 6. Signal freshness (actionable signals only) ---
    try:
        from app.models.signal import Signal

        last_signal_row = await db.execute(
            select(func.max(Signal.created_at))
        )
        last_signal_time = last_signal_row.scalar()

        if last_signal_time:
            if last_signal_time.tzinfo is None:
                last_signal_time = last_signal_time.replace(tzinfo=timezone.utc)
            sig_age = (now - last_signal_time).total_seconds()
            result["data"]["last_signal_at"] = last_signal_time.isoformat()
            result["data"]["signal_age_seconds"] = round(sig_age)
    except Exception:
        logger.warning("Failed to check signal freshness", exc_info=True)

    return result


@router.post("/restart")
@limiter.limit("5/minute")
async def restart_worker(
    request: Request,
    _user_id: str = Depends(get_current_user),
):
    """Soft-restart the Celery worker pool (cycles worker processes)."""
    if settings.admin_user_id and str(_user_id) != settings.admin_user_id:
        raise HTTPException(status_code=403, detail="Admin access required")

    from app.worker import celery_app

    def _restart():
        celery_app.control.pool_restart(reload=True)

    try:
        await asyncio.to_thread(_restart)
        return {"status": "ok", "detail": "Worker pool restart initiated"}
    except Exception:
        logger.exception("Worker restart failed")
        return {"status": "error", "detail": "Restart failed"}
