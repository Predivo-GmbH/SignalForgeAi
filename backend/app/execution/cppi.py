"""CPPI (Constant Proportion Portfolio Insurance) manager.

Implements drawdown-based CPPI where the floor ratchets up at new equity
highs, locking in gains. Output is an exposure percentage (0.0-1.0) that
scales all position sizes.

CPPI Formula:
  cushion = portfolio_value - floor
  risky_exposure = multiplier × cushion
  exposure_pct = clamp(risky_exposure / portfolio_value, 0.0, 1.0)

Floor update (drawdown-based variant):
  floor = max(floor, peak_equity × (1 - max_drawdown_pct))
  peak_equity = max(peak_equity, portfolio_value)

State stored in Redis: signalforge:cppi:{user_id}
"""

import json
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

REDIS_KEY_PREFIX = "signalforge:cppi"


@dataclass
class CPPIState:
    floor: float
    peak_equity: float
    current_exposure_pct: float
    cushion: float
    multiplier: float
    max_drawdown_pct: float


class CPPIManager:
    """Manages CPPI state and exposure calculations per user."""

    def __init__(
        self,
        multiplier: float = 3.0,
        max_drawdown_pct: float = 0.15,
        min_exposure_pct: float = 0.0,
        max_exposure_pct: float = 1.0,
    ):
        self.multiplier = multiplier
        self.max_drawdown_pct = max_drawdown_pct
        self.min_exposure_pct = min_exposure_pct
        self.max_exposure_pct = max_exposure_pct

    async def calculate_exposure(
        self, user_id: str, current_equity: float
    ) -> float:
        """Recalculate CPPI exposure and update Redis state.

        Returns exposure_pct between 0.0 and 1.0.
        """
        state = await self._load_state(user_id)

        if state is None:
            # Initialize: floor at equity × (1 - max_dd), peak = equity
            peak = current_equity
            floor = current_equity * (1 - self.max_drawdown_pct)
        else:
            # Update peak if new high
            peak = max(state.peak_equity, current_equity)
            # Ratchet floor up at new highs (locks in gains)
            floor = max(state.floor, peak * (1 - self.max_drawdown_pct))

        # Calculate cushion
        cushion = max(0.0, current_equity - floor)

        # Calculate risky exposure
        if current_equity > 0:
            risky_exposure = self.multiplier * cushion
            exposure_pct = risky_exposure / current_equity
        else:
            exposure_pct = 0.0

        # Clamp
        exposure_pct = max(self.min_exposure_pct, min(self.max_exposure_pct, exposure_pct))

        new_state = CPPIState(
            floor=round(floor, 2),
            peak_equity=round(peak, 2),
            current_exposure_pct=round(exposure_pct, 4),
            cushion=round(cushion, 2),
            multiplier=self.multiplier,
            max_drawdown_pct=self.max_drawdown_pct,
        )
        await self._save_state(user_id, new_state)

        if exposure_pct < 1.0:
            logger.info(
                "CPPI: user %s exposure=%.1f%% (equity=%.2f floor=%.2f "
                "cushion=%.2f mult=%.1f)",
                user_id, exposure_pct * 100, current_equity,
                floor, cushion, self.multiplier,
            )

        return exposure_pct

    async def get_exposure(self, user_id: str) -> float:
        """Get current exposure percentage from Redis cache.

        Returns 1.0 if no CPPI state exists (feature disabled / first run).
        """
        state = await self._load_state(user_id)
        if state is None:
            return 1.0
        return state.current_exposure_pct

    async def get_state(self, user_id: str) -> CPPIState | None:
        """Return current CPPI state for API/monitoring."""
        return await self._load_state(user_id)

    async def reset(self, user_id: str) -> None:
        """Reset CPPI state (called when user wants to restart)."""
        try:
            from app.core.redis_client import redis_client

            key = f"{REDIS_KEY_PREFIX}:{user_id}"
            await redis_client.delete(key)
        except Exception:
            logger.warning("Failed to reset CPPI state for user %s", user_id, exc_info=True)

    async def _load_state(self, user_id: str) -> CPPIState | None:
        """Load state from Redis."""
        try:
            from app.core.redis_client import redis_client

            key = f"{REDIS_KEY_PREFIX}:{user_id}"
            data = await redis_client.get(key)
            if data:
                d = json.loads(data)
                return CPPIState(**d)
        except Exception:
            logger.warning("Failed to load CPPI state for user %s", user_id, exc_info=True)
        return None

    async def _save_state(self, user_id: str, state: CPPIState) -> None:
        """Save state to Redis."""
        try:
            from app.core.redis_client import redis_client

            key = f"{REDIS_KEY_PREFIX}:{user_id}"
            data = json.dumps({
                "floor": state.floor,
                "peak_equity": state.peak_equity,
                "current_exposure_pct": state.current_exposure_pct,
                "cushion": state.cushion,
                "multiplier": state.multiplier,
                "max_drawdown_pct": state.max_drawdown_pct,
            })
            await redis_client.set(key, data, ex=7 * 86400)  # 7 day TTL
        except Exception as e:
            logger.warning("Failed to save CPPI state to Redis: %s", e)
