"""Alert configuration API — manage email notification preferences (DB-backed)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.core.rate_limit import limiter

router = APIRouter(tags=["alerts"])

_DEFAULT_CONFIG = {
    "email_on_signal": False,
    "email_daily_summary": False,
    "min_confluence_alert": 60,
    "alert_email": "",
}


class AlertConfig(BaseModel):
    email_on_signal: bool = False
    email_daily_summary: bool = False
    min_confluence_alert: int = 60
    alert_email: str = Field(default="", max_length=254)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/alerts/config", response_model=AlertConfig)
@limiter.limit("60/minute")
async def get_alert_config(
    request: Request,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get alert configuration from user's DB record."""
    from app.models.user import User

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.alert_config or _DEFAULT_CONFIG


@router.put("/alerts/config", response_model=AlertConfig)
@limiter.limit("20/minute")
async def update_alert_config(
    request: Request,
    body: AlertConfig,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update alert configuration in user's DB record."""
    from app.models.user import User

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.alert_config = body.model_dump()
    await db.commit()
    return user.alert_config
