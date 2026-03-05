"""Strategies CRUD API — create, list, get, update, activate, delete."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models.strategy import BrokerConnection, Strategy
from app.models.user import User

router = APIRouter(prefix="/strategies", tags=["strategies"])

# ---------- Strategy Config Validation ----------


class StrategyConfig(BaseModel):
    """Schema for strategy configuration JSON."""
    symbols: list[str] = Field(default=["BTC/USDT", "ETH/USDT", "SOL/USDT"])
    timeframes: list[str] = Field(default=["1h"])
    account_equity: float = Field(default=10000.0, ge=100, le=10_000_000)
    min_confluence: int = Field(default=50, ge=10, le=100)
    max_risk_per_trade: float = Field(default=0.02, ge=0.001, le=0.10)
    max_daily_loss: float = Field(default=0.06, ge=0.01, le=0.20)
    atr_sl_multiplier: float = Field(default=2.0, ge=0.5, le=5.0)
    min_risk_reward: float = Field(default=1.5, ge=0.5, le=5.0)
    # -- Risk Management Features --
    # Feature 1: ATR-adaptive trailing stop-loss
    trailing_stop_enabled: bool = Field(default=False)
    atr_trail_multiplier: float = Field(default=2.0, ge=0.5, le=5.0)
    # Feature 2: Portfolio drawdown circuit breaker
    drawdown_breaker_enabled: bool = Field(default=False)
    max_drawdown_pct: float = Field(default=0.15, ge=0.05, le=0.50)
    # Feature 3: Kelly criterion position sizing
    kelly_enabled: bool = Field(default=False)
    kelly_fraction: float = Field(default=0.5, ge=0.1, le=1.0)
    kelly_min_trades: int = Field(default=20, ge=10, le=100)
    kelly_lookback: int = Field(default=50, ge=20, le=200)
    # Feature 4: Break-even stop automation
    break_even_enabled: bool = Field(default=False)
    break_even_r_multiple: float = Field(default=1.0, ge=0.5, le=3.0)
    # Feature 6: CPPI portfolio insurance
    cppi_enabled: bool = Field(default=False)
    cppi_multiplier: float = Field(default=3.0, ge=1.0, le=10.0)
    cppi_max_drawdown_pct: float = Field(default=0.15, ge=0.05, le=0.50)
    # Feature 7: Time-based stops
    max_hold_hours: float = Field(default=24.0, ge=1.0, le=168.0)
    time_stop_profit_threshold_pct: float = Field(default=1.0, ge=0.0, le=10.0)
    # Feature 8: Correlation exposure alerts
    correlation_monitor_enabled: bool = Field(default=False)
    correlation_threshold: float = Field(default=0.7, ge=0.3, le=0.95)
    correlation_auto_reduce: bool = Field(default=False)
    # -- Pipeline Sensitivity (AI-controlled) --
    min_trigger_count: int = Field(default=2, ge=1, le=5)
    trigger_lookback_candles: int = Field(default=1, ge=1, le=10)
    ema_slope_threshold: float = Field(default=0.001, ge=0.0001, le=0.01)


STRATEGY_PRESETS: dict[str, dict] = {
    "conservative_swing": {
        "name": "Conservative Swing",
        "description": (
            "Low risk, high confluence required. Fewer trades, "
            "larger moves. Best for patient traders who want "
            "high-probability setups only."
        ),
        "config": {
            "symbols": ["BTC/USDT", "ETH/USDT"],
            "timeframes": ["4h"],
            "account_equity": 10000,
            "min_confluence": 70,
            "max_risk_per_trade": 0.01,
            "max_daily_loss": 0.04,
            "atr_sl_multiplier": 2.5,
            "min_risk_reward": 2.0,
            "trailing_stop_enabled": True,
            "atr_trail_multiplier": 2.5,
            "drawdown_breaker_enabled": True,
            "max_drawdown_pct": 0.10,
            "break_even_enabled": True,
            "break_even_r_multiple": 1.0,
            "cppi_enabled": True,
            "cppi_multiplier": 3.0,
            "cppi_max_drawdown_pct": 0.10,
            "max_hold_hours": 48,
            "time_stop_profit_threshold_pct": 1.0,
            "correlation_monitor_enabled": True,
            "correlation_threshold": 0.7,
        },
    },
    "balanced_momentum": {
        "name": "Balanced Momentum",
        "description": (
            "Default balanced approach with moderate risk. "
            "Good starting point for most traders. "
            "Trades the top 3 cryptos on 1-hour timeframe."
        ),
        "config": {
            "symbols": ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
            "timeframes": ["1h"],
            "account_equity": 10000,
            "min_confluence": 50,
            "max_risk_per_trade": 0.02,
            "max_daily_loss": 0.06,
            "atr_sl_multiplier": 2.0,
            "min_risk_reward": 1.5,
            "drawdown_breaker_enabled": True,
            "max_drawdown_pct": 0.15,
            "break_even_enabled": True,
            "break_even_r_multiple": 1.0,
            "max_hold_hours": 24,
            "time_stop_profit_threshold_pct": 1.0,
            "correlation_monitor_enabled": True,
            "correlation_threshold": 0.7,
        },
    },
    "aggressive_scalper": {
        "name": "Aggressive Scalper",
        "description": (
            "More trades, higher risk per trade. Scans multiple "
            "timeframes for opportunities. For experienced traders "
            "comfortable with higher drawdowns."
        ),
        "config": {
            "symbols": ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
            "timeframes": ["1h", "4h"],
            "account_equity": 10000,
            "min_confluence": 35,
            "max_risk_per_trade": 0.03,
            "max_daily_loss": 0.08,
            "atr_sl_multiplier": 1.5,
            "min_risk_reward": 1.2,
            "trailing_stop_enabled": True,
            "atr_trail_multiplier": 1.5,
            "max_drawdown_pct": 0.20,
            "break_even_r_multiple": 1.5,
            "max_hold_hours": 8,
            "time_stop_profit_threshold_pct": 1.5,
        },
    },
}

# ---------- Schemas ----------


class CreateStrategyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    config: dict = {}
    preset: str | None = None


class UpdateStrategyRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    config: dict | None = None


class StrategyResponse(BaseModel):
    id: str
    user_id: str
    name: str
    is_active: bool
    config: dict
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class StrategyListResponse(BaseModel):
    strategies: list[StrategyResponse]
    total: int


# ---------- Helpers ----------


def _strategy_to_response(s: Strategy) -> StrategyResponse:
    return StrategyResponse(
        id=str(s.id),
        user_id=str(s.user_id),
        name=s.name,
        is_active=s.is_active,
        config=s.config,
        created_at=s.created_at.isoformat() if s.created_at else "",
        updated_at=s.updated_at.isoformat() if s.updated_at else "",
    )


async def _get_user_strategy(
    strategy_id: uuid.UUID, user_id: str, db: AsyncSession
) -> Strategy:
    """Fetch a strategy owned by the user, or raise 404."""
    uid = uuid.UUID(user_id)
    result = await db.execute(
        select(Strategy).where(Strategy.id == strategy_id, Strategy.user_id == uid)
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found"
        )
    return strategy


# ---------- Routes ----------


@router.post("", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_strategy(
    request: Request,
    body: CreateStrategyRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new strategy."""
    config = body.config
    if body.preset and body.preset in STRATEGY_PRESETS:
        config = STRATEGY_PRESETS[body.preset]["config"].copy()
    # Validate config shape (raises ValidationError -> 422 if invalid)
    if config:
        StrategyConfig(**config)
    strategy = Strategy(
        user_id=uuid.UUID(user_id),
        name=body.name,
        config=config,
        is_active=False,
    )
    db.add(strategy)
    await db.commit()
    await db.refresh(strategy)
    return _strategy_to_response(strategy)


@router.get("", response_model=StrategyListResponse)
@limiter.limit("60/minute")
async def list_strategies(
    request: Request,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List strategies for the authenticated user."""
    uid = uuid.UUID(user_id)

    count_result = await db.execute(
        select(func.count()).select_from(Strategy).where(Strategy.user_id == uid)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Strategy)
        .where(Strategy.user_id == uid)
        .order_by(Strategy.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    strategies = result.scalars().all()

    return StrategyListResponse(
        strategies=[_strategy_to_response(s) for s in strategies],
        total=total,
    )


@router.get("/presets")
@limiter.limit("60/minute")
async def list_presets(request: Request, _user_id: str = Depends(get_current_user)):
    """Return available strategy presets."""
    return {"presets": STRATEGY_PRESETS}


@router.get("/{strategy_id}", response_model=StrategyResponse)
@limiter.limit("60/minute")
async def get_strategy(
    request: Request,
    strategy_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single strategy by ID."""
    strategy = await _get_user_strategy(strategy_id, user_id, db)
    return _strategy_to_response(strategy)


@router.put("/{strategy_id}", response_model=StrategyResponse)
@limiter.limit("20/minute")
async def update_strategy(
    request: Request,
    strategy_id: uuid.UUID,
    body: UpdateStrategyRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a strategy's name and/or config."""
    strategy = await _get_user_strategy(strategy_id, user_id, db)

    if body.name is not None:
        strategy.name = body.name
    if body.config is not None:
        if body.config:
            StrategyConfig(**body.config)
        strategy.config = body.config

    await db.commit()
    await db.refresh(strategy)
    return _strategy_to_response(strategy)


class ActivateRequest(BaseModel):
    totp_code: str | None = None


@router.post("/{strategy_id}/activate", response_model=StrategyResponse)
@limiter.limit("20/minute")
async def activate_strategy(
    request: Request,
    strategy_id: uuid.UUID,
    body: ActivateRequest | None = None,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle the is_active flag on a strategy.

    When activating with live broker connections, 2FA verification is required.
    Deactivation is always allowed without 2FA.
    """
    strategy = await _get_user_strategy(strategy_id, user_id, db)

    # Only enforce 2FA when ACTIVATING (not deactivating)
    if not strategy.is_active:
        # Check if user has live (non-paper) broker connections
        live_result = await db.execute(
            select(BrokerConnection).where(
                BrokerConnection.user_id == uuid.UUID(user_id),
                BrokerConnection.is_paper.is_(False),
            ).limit(1)
        )
        has_live = live_result.scalar_one_or_none() is not None

        if has_live:
            user_result = await db.execute(
                select(User).where(User.id == uuid.UUID(user_id))
            )
            user = user_result.scalar_one_or_none()

            if not user or not user.totp_enabled:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Enable two-factor authentication before activating live trading",
                )

            totp_code = body.totp_code if body else None
            if not totp_code:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="2FA code required to activate live trading",
                )

            from app.auth.totp import decrypt_totp_secret, verify_backup_code, verify_totp_code

            secret = decrypt_totp_secret(user.totp_secret_enc)  # type: ignore[arg-type]
            code_valid = verify_totp_code(secret, totp_code)
            if not code_valid and user.backup_codes_hash:
                idx = verify_backup_code(totp_code, user.backup_codes_hash)
                if idx is not None:
                    code_valid = True
                    codes = list(user.backup_codes_hash)
                    codes.pop(idx)
                    user.backup_codes_hash = codes

            if not code_valid:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid 2FA code",
                )

    strategy.is_active = not strategy.is_active
    await db.commit()
    await db.refresh(strategy)
    return _strategy_to_response(strategy)


@router.post("/{strategy_id}/tune")
@limiter.limit("5/minute")
async def tune_strategy_risk(
    request: Request,
    strategy_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger on-demand AI risk tuning for a strategy."""
    strategy = await _get_user_strategy(strategy_id, user_id, db)

    from app.advisor.risk_tuner import RiskTuner

    tuner = RiskTuner()
    result = await tuner.tune(strategy, db)
    adjustments = result.get("adjustments", {})

    if adjustments:
        cfg = dict(strategy.config or {})
        cfg.update(adjustments)
        strategy.config = cfg
        await db.commit()
        await db.refresh(strategy)

    return {
        "adjustments": adjustments,
        "reasoning": result.get("reasoning", ""),
        "metrics_snapshot": result.get("metrics_snapshot", {}),
        "strategy": _strategy_to_response(strategy),
    }


@router.get("/{strategy_id}/feedback-rules")
@limiter.limit("60/minute")
async def list_feedback_rules(
    request: Request,
    strategy_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List active feedback rules for a strategy."""
    from app.models.ai_insight import FeedbackRule

    _ = await _get_user_strategy(strategy_id, user_id, db)

    result = await db.execute(
        select(FeedbackRule)
        .where(FeedbackRule.strategy_id == strategy_id)
        .order_by(FeedbackRule.created_at.desc())
        .limit(100)
    )
    rules = result.scalars().all()
    return {
        "rules": [
            {
                "id": str(r.id),
                "rule_type": r.rule_type,
                "description": r.description,
                "conditions": r.conditions_json,
                "confidence": r.confidence,
                "is_active": r.is_active,
                "expires_at": r.expires_at.isoformat() if r.expires_at else None,
                "created_at": r.created_at.isoformat() if r.created_at else "",
            }
            for r in rules
        ],
    }


@router.post("/{strategy_id}/feedback-rules/{rule_id}/toggle")
@limiter.limit("20/minute")
async def toggle_feedback_rule(
    request: Request,
    strategy_id: uuid.UUID,
    rule_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enable or disable a feedback rule."""
    from app.models.ai_insight import FeedbackRule

    _ = await _get_user_strategy(strategy_id, user_id, db)

    result = await db.execute(
        select(FeedbackRule).where(
            FeedbackRule.id == rule_id,
            FeedbackRule.strategy_id == strategy_id,
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")

    rule.is_active = not rule.is_active
    await db.commit()
    return {"id": str(rule.id), "is_active": rule.is_active}


@router.post("/{strategy_id}/synthesize-feedback")
@limiter.limit("5/minute")
async def synthesize_feedback(
    request: Request,
    strategy_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger on-demand feedback rule synthesis."""
    strategy = await _get_user_strategy(strategy_id, user_id, db)

    from app.advisor.feedback_synthesizer import FeedbackSynthesizer

    synthesizer = FeedbackSynthesizer()
    new_rules = await synthesizer.synthesize(
        str(strategy.id), str(strategy.user_id), db,
    )
    await db.commit()
    return {"new_rules_count": len(new_rules), "rules": new_rules}


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/minute")
async def delete_strategy(
    request: Request,
    strategy_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a strategy. Active strategies are deactivated first.

    All dependent records have their strategy_id set to NULL
    so they are preserved as historical records.
    """
    from sqlalchemy import update

    from app.models.ai_insight import AIInsight, FeedbackRule
    from app.models.position import Position
    from app.models.signal import Signal as SignalModel

    strategy = await _get_user_strategy(strategy_id, user_id, db)
    if strategy.is_active:
        strategy.is_active = False
        await db.flush()

    # Detach all dependent tables so FK constraints don't block deletion
    for model, col in [
        (SignalModel, SignalModel.strategy_id),
        (FeedbackRule, FeedbackRule.strategy_id),
        (AIInsight, AIInsight.strategy_id),
        (Position, Position.strategy_id),
    ]:
        await db.execute(
            update(model).where(col == strategy_id).values(strategy_id=None)
        )

    # Detach backtest results (no SQLAlchemy model, use raw SQL)
    from sqlalchemy import text
    await db.execute(
        text("UPDATE backtest_results SET strategy_id = NULL WHERE strategy_id = :sid"),
        {"sid": str(strategy_id)},
    )
    await db.flush()

    await db.delete(strategy)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
