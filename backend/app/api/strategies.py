"""Strategies CRUD API — create, list, get, update, activate, delete."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.models.strategy import Strategy

router = APIRouter(prefix="/strategies", tags=["strategies"])


# ---------- Schemas ----------


class CreateStrategyRequest(BaseModel):
    name: str
    config: dict = {}


class UpdateStrategyRequest(BaseModel):
    name: str | None = None
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
async def create_strategy(
    body: CreateStrategyRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new strategy."""
    strategy = Strategy(
        user_id=uuid.UUID(user_id),
        name=body.name,
        config=body.config,
        is_active=False,
    )
    db.add(strategy)
    await db.commit()
    await db.refresh(strategy)
    return _strategy_to_response(strategy)


@router.get("", response_model=StrategyListResponse)
async def list_strategies(
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


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single strategy by ID."""
    strategy = await _get_user_strategy(strategy_id, user_id, db)
    return _strategy_to_response(strategy)


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
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
        strategy.config = body.config

    await db.commit()
    await db.refresh(strategy)
    return _strategy_to_response(strategy)


@router.post("/{strategy_id}/activate", response_model=StrategyResponse)
async def activate_strategy(
    strategy_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle the is_active flag on a strategy."""
    strategy = await _get_user_strategy(strategy_id, user_id, db)
    strategy.is_active = not strategy.is_active
    await db.commit()
    await db.refresh(strategy)
    return _strategy_to_response(strategy)


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    strategy_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a strategy."""
    strategy = await _get_user_strategy(strategy_id, user_id, db)
    await db.delete(strategy)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
