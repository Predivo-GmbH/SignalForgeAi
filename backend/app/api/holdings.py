"""Holdings API — aggregated portfolio view, exchange balances, manual CRUD."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.core.encryption import decrypt_value
from app.execution.adapters.ccxt_adapter import CCXTAdapter
from app.models.holding import ManualHolding
from app.models.position import Position
from app.models.strategy import BrokerConnection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/holdings", tags=["holdings"])


# ---------- Schemas ----------


class HoldingItem(BaseModel):
    id: str | None = None
    symbol: str
    quantity: float
    avg_price: float | None = None
    source: str
    notes: str | None = None


class HoldingsResponse(BaseModel):
    holdings: list[HoldingItem]
    total_value_usd: float | None = None


class ManualHoldingRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    quantity: float = Field(gt=0)
    purchase_price: float | None = None
    notes: str | None = Field(default=None, max_length=255)


class ManualHoldingResponse(BaseModel):
    id: str
    symbol: str
    quantity: float
    purchase_price: float | None = None
    notes: str | None = None
    created_at: str

    model_config = {"from_attributes": True}


# ---------- Helpers ----------


async def _fetch_exchange_holdings(
    db: AsyncSession, user_id: str,
) -> list[HoldingItem]:
    """Fetch balances from read-only live broker connections."""
    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.user_id == uuid.UUID(user_id),
            BrokerConnection.is_paper.is_(False),
            BrokerConnection.purpose == "read",
        )
    )
    connections = result.scalars().all()
    holdings: list[HoldingItem] = []

    for conn in connections:
        try:
            api_key = decrypt_value(conn.api_key_enc)
            api_secret = decrypt_value(conn.api_secret_enc)
            adapter = CCXTAdapter(
                exchange_id=conn.broker,
                api_key=api_key,
                api_secret=api_secret,
                testnet=False,
            )
            try:
                balances = await adapter.get_full_balance()
                for symbol, qty in balances.items():
                    holdings.append(HoldingItem(
                        symbol=symbol,
                        quantity=qty,
                        source=conn.broker,
                    ))
            finally:
                await adapter.close()
        except Exception:
            logger.exception("Failed to fetch balance from %s connection %s", conn.broker, conn.id)

    return holdings


async def _fetch_trading_holdings(
    db: AsyncSession, user_id: str,
) -> list[HoldingItem]:
    """Get open trading positions grouped by base symbol."""
    result = await db.execute(
        select(Position).where(
            Position.user_id == uuid.UUID(user_id),
            Position.is_open.is_(True),
        )
    )
    positions = result.scalars().all()
    grouped: dict[str, float] = {}
    for p in positions:
        # Extract base symbol (e.g. "BTC" from "BTC/USDT")
        base = p.symbol.split("/")[0] if "/" in p.symbol else p.symbol
        sign = 1.0 if p.direction.upper() in ("LONG", "BUY") else -1.0
        grouped[base] = grouped.get(base, 0) + (p.quantity * sign)

    return [
        HoldingItem(symbol=sym, quantity=qty, source="trading")
        for sym, qty in grouped.items()
        if abs(qty) > 1e-12
    ]


async def _fetch_manual_holdings(
    db: AsyncSession, user_id: str,
) -> list[HoldingItem]:
    """Get all manual holdings for the user."""
    result = await db.execute(
        select(ManualHolding).where(ManualHolding.user_id == uuid.UUID(user_id))
        .order_by(ManualHolding.symbol)
    )
    rows = result.scalars().all()
    return [
        HoldingItem(
            id=str(h.id),
            symbol=h.symbol,
            quantity=h.quantity,
            avg_price=h.purchase_price,
            source="manual",
            notes=h.notes,
        )
        for h in rows
    ]


# ---------- Routes ----------


@router.get("", response_model=HoldingsResponse)
async def get_aggregated_holdings(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregated view: exchange balances + manual holdings + trading positions."""
    exchange = await _fetch_exchange_holdings(db, user_id)
    manual = await _fetch_manual_holdings(db, user_id)
    trading = await _fetch_trading_holdings(db, user_id)
    all_holdings = exchange + manual + trading
    return HoldingsResponse(holdings=all_holdings)


@router.get("/exchange", response_model=list[HoldingItem])
async def get_exchange_holdings(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch live balances from connected exchanges."""
    return await _fetch_exchange_holdings(db, user_id)


@router.get("/manual", response_model=list[ManualHoldingResponse])
async def list_manual_holdings(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all manual holdings."""
    result = await db.execute(
        select(ManualHolding).where(ManualHolding.user_id == uuid.UUID(user_id))
        .order_by(ManualHolding.symbol)
    )
    rows = result.scalars().all()
    return [
        ManualHoldingResponse(
            id=str(h.id),
            symbol=h.symbol,
            quantity=h.quantity,
            purchase_price=h.purchase_price,
            notes=h.notes,
            created_at=h.created_at.isoformat() if h.created_at else "",
        )
        for h in rows
    ]


@router.post("/manual", response_model=ManualHoldingResponse, status_code=201)
async def add_manual_holding(
    body: ManualHoldingRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a manual crypto holding."""
    holding = ManualHolding(
        id=uuid.uuid4(),
        user_id=uuid.UUID(user_id),
        symbol=body.symbol.upper(),
        quantity=body.quantity,
        purchase_price=body.purchase_price,
        notes=body.notes,
    )
    db.add(holding)
    await db.commit()
    await db.refresh(holding)
    return ManualHoldingResponse(
        id=str(holding.id),
        symbol=holding.symbol,
        quantity=holding.quantity,
        purchase_price=holding.purchase_price,
        notes=holding.notes,
        created_at=holding.created_at.isoformat() if holding.created_at else "",
    )


@router.put("/manual/{holding_id}", response_model=ManualHoldingResponse)
async def update_manual_holding(
    holding_id: str,
    body: ManualHoldingRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a manual holding."""
    result = await db.execute(
        select(ManualHolding).where(
            ManualHolding.id == uuid.UUID(holding_id),
            ManualHolding.user_id == uuid.UUID(user_id),
        )
    )
    holding = result.scalar_one_or_none()
    if not holding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holding not found")

    holding.symbol = body.symbol.upper()
    holding.quantity = body.quantity
    holding.purchase_price = body.purchase_price
    holding.notes = body.notes
    await db.commit()
    await db.refresh(holding)
    return ManualHoldingResponse(
        id=str(holding.id),
        symbol=holding.symbol,
        quantity=holding.quantity,
        purchase_price=holding.purchase_price,
        notes=holding.notes,
        created_at=holding.created_at.isoformat() if holding.created_at else "",
    )


@router.delete("/manual/{holding_id}", status_code=204)
async def delete_manual_holding(
    holding_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a manual holding."""
    result = await db.execute(
        select(ManualHolding).where(
            ManualHolding.id == uuid.UUID(holding_id),
            ManualHolding.user_id == uuid.UUID(user_id),
        )
    )
    holding = result.scalar_one_or_none()
    if not holding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holding not found")
    await db.delete(holding)
    await db.commit()
