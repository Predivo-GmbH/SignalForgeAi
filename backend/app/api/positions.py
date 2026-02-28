"""Positions API — list open positions and account state."""

from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import get_current_user
from app.execution.position_manager import PositionManager

router = APIRouter(prefix="/positions", tags=["positions"])

# Global position manager instance (single-user for now)
_pm = PositionManager(initial_equity=10000)


@router.get("")
async def list_positions(user_id: str = Depends(get_current_user)):
    """Return all currently open positions."""
    positions = _pm.list_open()
    return [_pos_to_dict(p) for p in positions]


@router.get("/account")
async def account_state(user_id: str = Depends(get_current_user)):
    """Return current account state (equity, PnL, open position count)."""
    state = _pm.account_state()
    return {
        "equity": state.equity,
        "daily_pnl": state.daily_pnl,
        "open_positions": state.open_positions,
        "max_positions": state.max_positions,
    }


@router.post("/{position_id}/close")
async def close_position(
    position_id: str,
    exit_price: float,
    reason: str = "manual",
    user_id: str = Depends(get_current_user),
):
    """Close an open position at the given exit price."""
    try:
        pos = _pm.close_position(position_id, exit_price, reason)
        return _pos_to_dict(pos)
    except KeyError:
        raise HTTPException(status_code=404, detail="Position not found")


def _pos_to_dict(p):
    """Convert a Position dataclass to a JSON-serializable dict."""
    return {
        "id": p.id,
        "symbol": p.symbol,
        "direction": p.direction,
        "entry_price": p.entry_price,
        "quantity": p.quantity,
        "stop_loss": p.stop_loss,
        "take_profit": p.take_profit,
        "is_open": p.is_open,
        "pnl": p.pnl,
        "exit_price": p.exit_price,
        "exit_reason": p.exit_reason,
        "order_id": p.order_id,
    }
