"""Engine monitor API — pipeline decision log and summary stats."""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.models.pipeline_log import PipelineLog
from app.models.strategy import Strategy

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/engine", tags=["engine"])


@router.get("/log")
async def get_pipeline_log(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    symbol: str | None = Query(None),
    block_reason: str | None = Query(None),
    action: str | None = Query(None),
    since: str | None = Query(None),
):
    """Paginated pipeline decision log for the user's strategies."""
    uid = uuid.UUID(user_id)

    # Get user's strategy IDs
    strat_result = await db.execute(
        select(Strategy.id).where(Strategy.user_id == uid)
    )
    strategy_ids = [row[0] for row in strat_result.all()]
    if not strategy_ids:
        return {"items": [], "total": 0, "page": page, "per_page": per_page}

    # Build query
    base = select(PipelineLog).where(PipelineLog.strategy_id.in_(strategy_ids))
    count_q = select(func.count(PipelineLog.id)).where(PipelineLog.strategy_id.in_(strategy_ids))

    if symbol:
        base = base.where(PipelineLog.symbol == symbol)
        count_q = count_q.where(PipelineLog.symbol == symbol)
    if block_reason:
        if block_reason == "passed":
            base = base.where(PipelineLog.block_reason.is_(None))
            count_q = count_q.where(PipelineLog.block_reason.is_(None))
        else:
            base = base.where(PipelineLog.block_reason == block_reason)
            count_q = count_q.where(PipelineLog.block_reason == block_reason)
    if action:
        base = base.where(PipelineLog.action == action)
        count_q = count_q.where(PipelineLog.action == action)
    if since:
        try:
            since_dt = datetime.fromisoformat(since)
            base = base.where(PipelineLog.created_at >= since_dt)
            count_q = count_q.where(PipelineLog.created_at >= since_dt)
        except ValueError:
            pass

    total = (await db.execute(count_q)).scalar() or 0
    offset = (page - 1) * per_page
    rows = (
        await db.execute(
            base.order_by(PipelineLog.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
    ).scalars().all()

    return {
        "items": [
            {
                "id": str(r.id),
                "symbol": r.symbol,
                "timeframe": r.timeframe,
                "action": r.action,
                "block_reason": r.block_reason,
                "confluence_score": r.confluence_score,
                "regime": r.regime,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/log/summary")
async def get_pipeline_summary(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    since: str | None = Query(None),
):
    """Aggregated pipeline stats — block reason distribution."""
    uid = uuid.UUID(user_id)

    strat_result = await db.execute(
        select(Strategy.id).where(Strategy.user_id == uid)
    )
    strategy_ids = [row[0] for row in strat_result.all()]
    if not strategy_ids:
        return {
            "total_evaluations": 0, "passed": 0, "blocked": 0,
            "block_reasons": {}, "symbols_evaluated": 0,
            "last_run_at": None, "period_start": None,
        }

    # Default to today
    if since:
        try:
            period_start = datetime.fromisoformat(since)
        except ValueError:
            period_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        period_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    base_filter = [
        PipelineLog.strategy_id.in_(strategy_ids),
        PipelineLog.created_at >= period_start,
    ]

    # Total evaluations
    total = (await db.execute(
        select(func.count(PipelineLog.id)).where(*base_filter)
    )).scalar() or 0

    # Passed (block_reason is NULL)
    passed = (await db.execute(
        select(func.count(PipelineLog.id)).where(
            *base_filter, PipelineLog.block_reason.is_(None),
        )
    )).scalar() or 0

    # Block reason distribution
    reason_rows = (await db.execute(
        select(PipelineLog.block_reason, func.count(PipelineLog.id))
        .where(*base_filter, PipelineLog.block_reason.is_not(None))
        .group_by(PipelineLog.block_reason)
        .order_by(func.count(PipelineLog.id).desc())
    )).all()
    block_reasons = {row[0]: row[1] for row in reason_rows}

    # Distinct symbols
    symbols_count = (await db.execute(
        select(func.count(func.distinct(PipelineLog.symbol))).where(*base_filter)
    )).scalar() or 0

    # Last run
    last_run = (await db.execute(
        select(func.max(PipelineLog.created_at)).where(
            PipelineLog.strategy_id.in_(strategy_ids),
        )
    )).scalar()

    return {
        "total_evaluations": total,
        "passed": passed,
        "blocked": total - passed,
        "block_reasons": block_reasons,
        "symbols_evaluated": symbols_count,
        "last_run_at": last_run.isoformat() if last_run else None,
        "period_start": period_start.isoformat(),
    }
