"""Regime allocator API — current regime status and allocation state."""

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models.strategy import Strategy

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/regime", tags=["regime"])


@router.get("/status")
@limiter.limit("60/minute")
async def get_regime_status(
    request: Request,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return current regime allocator state for the authenticated user."""
    import uuid

    # Load active strategy config
    uid = uuid.UUID(user_id)
    strat_result = await db.execute(
        select(Strategy).where(
            Strategy.user_id == uid, Strategy.is_active == True  # noqa: E712
        ).limit(1)
    )
    strategy = strat_result.scalar_one_or_none()
    cfg = (strategy.config if strategy else None) or {}

    enabled = cfg.get("regime_allocator_enabled", False)
    allocation_table = cfg.get("regime_allocation_table", "moderate")
    smoothing_bars = cfg.get("regime_smoothing_bars", 3)
    symbols = cfg.get("symbols", ["BTC/USDT"])

    result = {
        "regime_allocator_enabled": enabled,
        "current_regime": "unknown",
        "regime_probabilities": {},
        "target_allocation_pct": 100.0,
        "current_allocation_pct": 100.0,
        "allocation_table": allocation_table if isinstance(allocation_table, str) else "custom",
        "smoothing_bars": smoothing_bars,
        "cooldown_hours": cfg.get("cooldown_hours", 0),
    }

    if not enabled:
        return result

    # Read current regime label from Redis
    try:
        from app.core.redis_client import redis_client

        regime_symbol = symbols[0] if symbols else "BTC/USDT"
        label = await redis_client.get(f"signalforge:hmm_regime_label:{regime_symbol}")
        if label:
            result["current_regime"] = label.decode() if isinstance(label, bytes) else label

        # Read regime probabilities from model if available
        model_data = await redis_client.get(f"signalforge:hmm_regime:{regime_symbol}")
        if model_data:
            from app.engine.layers.hmm_regime import HMMRegimeModel

            model = HMMRegimeModel.deserialize(model_data)
            # Probabilities need candle data — skip for now, just show label
            result["regime_probabilities"] = {}
    except Exception:
        logger.exception("Failed to read regime from Redis for user %s", user_id)

    # Read allocation state from Redis
    try:
        from app.execution.regime_allocator import RegimeAllocator

        allocator = RegimeAllocator(
            allocation_table=allocation_table,
            smoothing_bars=smoothing_bars,
        )
        state = await allocator.get_state(user_id)
        if state:
            result["target_allocation_pct"] = round(state.target_pct * 100, 1)
            result["current_allocation_pct"] = round(state.current_pct * 100, 1)
            result["current_regime"] = state.regime
    except Exception:
        logger.exception("Failed to read regime allocation state for user %s", user_id)

    return result
