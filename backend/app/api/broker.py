"""Broker connection management API — CRUD for API credentials."""

import logging
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.core.encryption import decrypt_value, encrypt_value
from app.core.rate_limit import limiter
from app.execution.adapters.ccxt_adapter import CCXTAdapter
from app.models.strategy import BrokerConnection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/broker", tags=["broker"])


class BrokerConnectRequest(BaseModel):
    broker: Literal["binance", "kucoin", "mexc", "bitstamp", "cryptocom", "kraken"] = "binance"
    api_key: str = ""
    api_secret: str = ""
    api_passphrase: str = ""
    is_paper: bool = True
    purpose: Literal["read", "trade"] = "read"


class BrokerConnectionResponse(BaseModel):
    id: str
    broker: str
    api_key_masked: str  # ****last4
    is_paper: bool
    purpose: str
    created_at: str

    model_config = {"from_attributes": True}


def _mask_key(key: str) -> str:
    if len(key) <= 4:
        return "****"
    return f"****{key[-4:]}"


@router.post("", response_model=BrokerConnectionResponse, status_code=201)
@limiter.limit("20/minute")
async def create_broker_connection(
    request: Request,
    body: BrokerConnectRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Store encrypted broker credentials."""
    if not body.is_paper and (not body.api_key or not body.api_secret):
        raise HTTPException(
            status_code=422,
            detail="API key and secret are required for live trading",
        )
    if body.purpose == "trade" and body.is_paper:
        raise HTTPException(
            status_code=422,
            detail="Trading purpose requires a live (non-paper) connection",
        )
    # Paper mode doesn't need credentials — skip encryption
    if body.is_paper:
        api_key_enc = b""
        api_secret_enc = b""
        api_passphrase_enc = None
    else:
        api_key_enc = encrypt_value(body.api_key)
        api_secret_enc = encrypt_value(body.api_secret)
        api_passphrase_enc = encrypt_value(body.api_passphrase) if body.api_passphrase else None

    conn = BrokerConnection(
        id=uuid.uuid4(),
        user_id=uuid.UUID(user_id),
        broker=body.broker,
        api_key_enc=api_key_enc,
        api_secret_enc=api_secret_enc,
        api_passphrase_enc=api_passphrase_enc,
        is_paper=body.is_paper,
        purpose=body.purpose,
    )
    db.add(conn)
    await db.commit()
    await db.refresh(conn)
    return BrokerConnectionResponse(
        id=str(conn.id),
        broker=conn.broker,
        api_key_masked="Paper" if body.is_paper else _mask_key(body.api_key),
        is_paper=conn.is_paper,
        purpose=conn.purpose,
        created_at=conn.created_at.isoformat(),
    )


@router.get("", response_model=list[BrokerConnectionResponse])
@limiter.limit("60/minute")
async def list_broker_connections(
    request: Request,
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
        if c.is_paper:
            masked = "Paper"
        else:
            try:
                raw_key = decrypt_value(c.api_key_enc)
                masked = _mask_key(raw_key)
            except Exception:
                logger.warning("Failed to decrypt API key for connection %s", c.id, exc_info=True)
                masked = "****error"
        out.append(
            BrokerConnectionResponse(
                id=str(c.id),
                broker=c.broker,
                api_key_masked=masked,
                is_paper=c.is_paper,
                purpose=c.purpose,
                created_at=c.created_at.isoformat(),
            )
        )
    return out


@router.delete("/{connection_id}", status_code=204)
@limiter.limit("20/minute")
async def delete_broker_connection(
    request: Request,
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


class BrokerHealthResponse(BaseModel):
    id: str
    broker: str
    ok: bool
    error: str | None = None


@router.get("/{connection_id}/health", response_model=BrokerHealthResponse)
@limiter.limit("5/minute")
async def check_broker_health(
    request: Request,
    connection_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Test a broker connection by fetching the account balance."""
    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.id == uuid.UUID(connection_id),
            BrokerConnection.user_id == uuid.UUID(user_id),
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Broker connection not found")

    if conn.is_paper:
        return BrokerHealthResponse(id=str(conn.id), broker=conn.broker, ok=True)

    try:
        api_key = decrypt_value(conn.api_key_enc)
        api_secret = decrypt_value(conn.api_secret_enc)
        passphrase = decrypt_value(conn.api_passphrase_enc) if conn.api_passphrase_enc else ""
        adapter = CCXTAdapter(
            exchange_id=conn.broker,
            api_key=api_key,
            api_secret=api_secret,
            password=passphrase,
            testnet=False,
        )
        try:
            await adapter.get_full_balance()
            return BrokerHealthResponse(id=str(conn.id), broker=conn.broker, ok=True)
        finally:
            await adapter.close()
    except Exception as exc:
        logger.error("Broker health check failed for connection %s: %s", connection_id, exc)
        return BrokerHealthResponse(
            id=str(conn.id), broker=conn.broker, ok=False,
            error="Connection check failed. Verify API credentials and try again.",
        )
