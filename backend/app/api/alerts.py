"""Alert configuration API — manage email notification preferences."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.dependencies import get_current_user

router = APIRouter(tags=["alerts"])


# ---------------------------------------------------------------------------
# In-memory config store (single-user for now)
# ---------------------------------------------------------------------------

_alert_configs: dict[str, dict] = {}

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
    alert_email: str = ""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/alerts/config", response_model=AlertConfig)
async def get_alert_config(user_id: str = Depends(get_current_user)):
    """Get current alert configuration for the authenticated user."""
    cfg = _alert_configs.get(user_id, _DEFAULT_CONFIG.copy())
    return AlertConfig(**cfg)


@router.put("/alerts/config", response_model=AlertConfig)
async def update_alert_config(
    body: AlertConfig,
    user_id: str = Depends(get_current_user),
):
    """Update alert settings for the authenticated user."""
    cfg = body.model_dump()
    _alert_configs[user_id] = cfg
    return AlertConfig(**cfg)
