"""AI Usage & Cost Tracking API.

Uses the Anthropic Admin API (Cost & Usage reports) when an admin key
is configured. Falls back to local ai_insights table otherwise.
"""

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.models.ai_insight import AIInsight

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ai-usage"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class UsageSummary(BaseModel):
    total_cost_usd: float
    total_calls: int
    avg_cost_per_call: float
    avg_latency_ms: float


class ModelBreakdown(BaseModel):
    model: str
    calls: int
    cost_usd: float
    avg_latency_ms: float


class TypeBreakdown(BaseModel):
    insight_type: str
    calls: int
    cost_usd: float


class DailyCost(BaseModel):
    date: str
    cost_usd: float
    calls: int


class RecentCall(BaseModel):
    id: str
    created_at: str
    insight_type: str
    model_used: str
    cost_usd: float
    latency_ms: int
    input_tokens: int
    output_tokens: int


class CreditInfo(BaseModel):
    prepaid_usd: float
    spent_usd: float
    remaining_usd: float


class AiUsageResponse(BaseModel):
    source: str  # "anthropic_api" or "local"
    summary: UsageSummary
    by_model: list[ModelBreakdown]
    by_type: list[TypeBreakdown]
    daily_costs: list[DailyCost]
    recent_calls: list[RecentCall]
    credit: CreditInfo


class CreditUpdate(BaseModel):
    prepaid_usd: float


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/ai-usage", response_model=AiUsageResponse)
async def get_ai_usage(
    days: int = Query(default=30, ge=1, le=365),
    _user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return AI usage and cost data.

    Tries Anthropic Admin API first (real billing data).
    Falls back to local ai_insights table.
    """
    from app.advisor import anthropic_admin

    anthropic_data = None
    if anthropic_admin.available():
        anthropic_data = await _fetch_anthropic_data(days)

    # Always query local DB for per-feature breakdown + recent calls
    local = await _query_local(db, days)

    if anthropic_data is not None:
        # Merge: Anthropic for costs, local for feature breakdown
        return _build_response_from_anthropic(
            anthropic_data, local, days,
        )

    return _build_response_from_local(local, days)


@router.put("/ai-usage/credit")
async def update_credit(
    body: CreditUpdate,
    _user_id: str = Depends(get_current_user),
):
    """Set the prepaid credit amount (from Anthropic console)."""
    from app.core.redis_client import redis_client

    await redis_client.set("ai_prepaid_credit", str(body.prepaid_usd))
    return {"prepaid_usd": body.prepaid_usd}


# ---------------------------------------------------------------------------
# Anthropic Admin API
# ---------------------------------------------------------------------------


async def _fetch_anthropic_data(
    days: int,
) -> dict | None:
    """Fetch cost + usage from Anthropic Admin API."""
    from app.advisor import anthropic_admin

    cost_data = await anthropic_admin.fetch_cost_report(days)
    usage_data = await anthropic_admin.fetch_usage_report(days)

    if cost_data is None and usage_data is None:
        return None

    return {"cost": cost_data or [], "usage": usage_data or []}


def _build_response_from_anthropic(
    api_data: dict,
    local: dict,
    days: int,
) -> AiUsageResponse:
    """Build response using Anthropic API for costs, local for details."""
    cost_buckets = api_data["cost"]
    usage_buckets = api_data["usage"]

    # Aggregate daily costs from Anthropic cost report
    daily_map: dict[str, float] = {}
    total_cost = 0.0
    for bucket in cost_buckets:
        date_str = bucket.get("bucket_start_time", "")[:10]
        # Cost API returns amount in cents as string
        amount_str = bucket.get("amount", "0")
        amount = float(amount_str) / 100.0  # cents → dollars
        daily_map[date_str] = daily_map.get(date_str, 0) + amount
        total_cost += amount

    daily_costs = [
        DailyCost(date=d, cost_usd=round(c, 6), calls=0)
        for d, c in sorted(daily_map.items())
    ]

    # Model breakdown from usage report
    model_totals: dict[str, dict] = {}
    total_requests = 0
    for bucket in usage_buckets:
        model = bucket.get("model", "unknown")
        tokens = (
            bucket.get("input_tokens", 0)
            + bucket.get("output_tokens", 0)
        )
        requests = bucket.get("request_count", 0)
        if model not in model_totals:
            model_totals[model] = {
                "calls": 0, "tokens": 0,
            }
        model_totals[model]["calls"] += requests
        model_totals[model]["tokens"] += tokens
        total_requests += requests

    by_model = [
        ModelBreakdown(
            model=m,
            calls=v["calls"],
            cost_usd=0,  # cost not split by model in cost API
            avg_latency_ms=local.get("model_latency", {}).get(m, 0),
        )
        for m, v in sorted(
            model_totals.items(),
            key=lambda x: x[1]["calls"],
            reverse=True,
        )
    ]

    avg_cost = total_cost / total_requests if total_requests else 0

    return AiUsageResponse(
        source="anthropic_api",
        summary=UsageSummary(
            total_cost_usd=round(total_cost, 6),
            total_calls=total_requests,
            avg_cost_per_call=round(avg_cost, 6),
            avg_latency_ms=local["avg_latency"],
        ),
        by_model=by_model,
        by_type=local["by_type"],
        daily_costs=daily_costs,
        recent_calls=local["recent_calls"],
        credit=local["credit"],
    )


# ---------------------------------------------------------------------------
# Local DB queries
# ---------------------------------------------------------------------------


async def _query_local(
    db: AsyncSession, days: int,
) -> dict:
    """Query local ai_insights table for all data."""
    cutoff = datetime.now(UTC) - timedelta(days=days)

    # Summary
    summary_q = select(
        func.count(AIInsight.id).label("total_calls"),
        func.coalesce(func.sum(AIInsight.cost_usd), 0.0).label("cost"),
        func.coalesce(func.avg(AIInsight.cost_usd), 0.0).label("avg_c"),
        func.coalesce(func.avg(AIInsight.latency_ms), 0.0).label("lat"),
    ).where(AIInsight.created_at >= cutoff)
    row = (await db.execute(summary_q)).one()

    total_calls = row.total_calls or 0
    total_cost = float(row.cost or 0)
    avg_cost = float(row.avg_c or 0)
    avg_latency = float(row.lat or 0)

    # By model
    model_q = (
        select(
            AIInsight.model_used,
            func.count(AIInsight.id).label("calls"),
            func.coalesce(func.sum(AIInsight.cost_usd), 0.0).label("cost"),
            func.coalesce(func.avg(AIInsight.latency_ms), 0.0).label("lat"),
        )
        .where(AIInsight.created_at >= cutoff)
        .group_by(AIInsight.model_used)
        .order_by(func.sum(AIInsight.cost_usd).desc())
    )
    model_rows = (await db.execute(model_q)).all()
    by_model = [
        ModelBreakdown(
            model=r.model_used,
            calls=r.calls,
            cost_usd=round(float(r.cost), 6),
            avg_latency_ms=round(float(r.lat), 1),
        )
        for r in model_rows
    ]
    model_latency = {
        r.model_used: round(float(r.lat), 1) for r in model_rows
    }

    # By type
    type_q = (
        select(
            AIInsight.insight_type,
            func.count(AIInsight.id).label("calls"),
            func.coalesce(func.sum(AIInsight.cost_usd), 0.0).label("cost"),
        )
        .where(AIInsight.created_at >= cutoff)
        .group_by(AIInsight.insight_type)
        .order_by(func.sum(AIInsight.cost_usd).desc())
    )
    type_rows = (await db.execute(type_q)).all()
    by_type = [
        TypeBreakdown(
            insight_type=r.insight_type,
            calls=r.calls,
            cost_usd=round(float(r.cost), 6),
        )
        for r in type_rows
    ]

    # Daily costs
    date_expr = func.date(AIInsight.created_at)
    daily_q = (
        select(
            date_expr.label("day"),
            func.coalesce(func.sum(AIInsight.cost_usd), 0.0).label("cost"),
            func.count(AIInsight.id).label("calls"),
        )
        .where(AIInsight.created_at >= cutoff)
        .group_by(date_expr)
        .order_by(date_expr)
    )
    daily_rows = (await db.execute(daily_q)).all()
    daily_costs = [
        DailyCost(
            date=str(r.day),
            cost_usd=round(float(r.cost), 6),
            calls=r.calls,
        )
        for r in daily_rows
    ]

    # Recent calls (last 20)
    recent_q = (
        select(AIInsight)
        .where(AIInsight.created_at >= cutoff)
        .order_by(AIInsight.created_at.desc())
        .limit(20)
    )
    recent_rows = (await db.execute(recent_q)).scalars().all()
    recent_calls = [
        RecentCall(
            id=str(r.id),
            created_at=r.created_at.isoformat(),
            insight_type=r.insight_type,
            model_used=r.model_used,
            cost_usd=round(r.cost_usd or 0, 6),
            latency_ms=r.latency_ms or 0,
            input_tokens=r.input_tokens or 0,
            output_tokens=r.output_tokens or 0,
        )
        for r in recent_rows
    ]

    # Credit — for Anthropic source we use total from their API
    # For local, use all-time local sum
    prepaid = await _get_prepaid_credit()
    all_time_q = select(
        func.coalesce(func.sum(AIInsight.cost_usd), 0.0),
    )
    all_time_spent = float(
        (await db.execute(all_time_q)).scalar() or 0,
    )

    return {
        "total_calls": total_calls,
        "total_cost": total_cost,
        "avg_cost": avg_cost,
        "avg_latency": avg_latency,
        "by_model": by_model,
        "model_latency": model_latency,
        "by_type": by_type,
        "daily_costs": daily_costs,
        "recent_calls": recent_calls,
        "credit": CreditInfo(
            prepaid_usd=round(prepaid, 2),
            spent_usd=round(all_time_spent, 6),
            remaining_usd=round(max(prepaid - all_time_spent, 0), 2),
        ),
    }


def _build_response_from_local(
    local: dict, days: int,
) -> AiUsageResponse:
    """Build response using only local ai_insights data."""
    total_calls = local["total_calls"]
    return AiUsageResponse(
        source="local",
        summary=UsageSummary(
            total_cost_usd=round(local["total_cost"], 6),
            total_calls=total_calls,
            avg_cost_per_call=round(local["avg_cost"], 6),
            avg_latency_ms=round(local["avg_latency"], 1),
        ),
        by_model=local["by_model"],
        by_type=local["by_type"],
        daily_costs=local["daily_costs"],
        recent_calls=local["recent_calls"],
        credit=local["credit"],
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_prepaid_credit() -> float:
    """Read prepaid credit from Redis, falling back to config."""
    try:
        from app.core.redis_client import redis_client

        val = await redis_client.get("ai_prepaid_credit")
        if val is not None:
            return float(val)
    except Exception:
        pass
    from app.config import settings

    return settings.ai_prepaid_credit_usd
