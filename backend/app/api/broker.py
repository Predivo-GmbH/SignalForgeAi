"""Broker connection management API — CRUD for API credentials."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.core.encryption import decrypt_value, encrypt_value
from app.models.strategy import BrokerConnection

router = APIRouter(prefix="/broker", tags=["broker"])


class BrokerConnectRequest(BaseModel):
    broker: str  # "alpaca" or "binance"
    api_key: str
    api_secret: str
    is_paper: bool = True


class BrokerConnectionResponse(BaseModel):
    id: str
    broker: str
    api_key_masked: str  # ****last4
    is_paper: bool

    model_config = {"from_attributes": True}


def _mask_key(key: str) -> str:
    if len(key) <= 4:
        return "****"
    return f"****{key[-4:]}"


@router.post("", response_model=BrokerConnectionResponse, status_code=201)
async def create_broker_connection(
    body: BrokerConnectRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Store encrypted broker credentials."""
    conn = BrokerConnection(
        id=uuid.uuid4(),
        user_id=uuid.UUID(user_id),
        broker=body.broker,
        api_key_enc=encrypt_value(body.api_key),
        api_secret_enc=encrypt_value(body.api_secret),
        is_paper=body.is_paper,
    )
    db.add(conn)
    await db.commit()
    await db.refresh(conn)
    return BrokerConnectionResponse(
        id=str(conn.id),
        broker=conn.broker,
        api_key_masked=_mask_key(body.api_key),
        is_paper=conn.is_paper,
    )


@router.get("", response_model=list[BrokerConnectionResponse])
async def list_broker_connections(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List broker connections (keys masked)."""
    result = await db.execute(
        select(BrokerConnection).where(BrokerConnection.user_id == uuid.UUID(user_id))
    )
    connections = result.scalars().all()
    out = []
    for c in connections:
        try:
            raw_key = decrypt_value(c.api_key_enc)
            masked = _mask_key(raw_key)
        except Exception:
            masked = "****error"
        out.append(
            BrokerConnectionResponse(
                id=str(c.id),
                broker=c.broker,
                api_key_masked=masked,
                is_paper=c.is_paper,
            )
        )
    return out


@router.delete("/{connection_id}", status_code=204)
async def delete_broker_connection(
    connection_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a broker connection."""
    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.id == uuid.UUID(connection_id),
            BrokerConnection.user_id == uuid.UUID(user_id),
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Broker connection not found")
    await db.delete(conn)
    await db.commit()
