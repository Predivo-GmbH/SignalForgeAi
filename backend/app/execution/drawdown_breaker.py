"""Portfolio-level drawdown circuit breaker with graduated responses.

Levels (percentage of max_drawdown_pct limit):
  - Level 0: Normal       (drawdown < 50% of limit) — full sizing
  - Level 1: Warning      (50-75% of limit)         — reduce new position sizes by 50%
  - Level 2: Halt         (75-100% of limit)         — block all new trades
  - Level 3: Emergency    (100%+ of limit)           — close all positions

State stored in Redis: signalforge:drawdown:{user_id}
"""

import json
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

REDIS_KEY_PREFIX = "signalforge:drawdown"


@dataclass
class DrawdownState:
    peak_equity: float
    current_equity: float
    drawdown_pct: float
    level: int


class DrawdownBreaker:
    """Portfolio-level drawdown circuit breaker."""

    def __init__(self, max_drawdown_pct: float = 0.15):
        self.max_drawdown_pct = max_drawdown_pct
        self._peak: float = 0.0
        self._current: float = 0.0

    async def update_and_check(
        self, user_id: str, current_equity: float
    ) -> int:
        """Update equity and return the current drawdown level (0-3).

        Persists state in Redis for fast access from other tasks.
        """
        state = await self._load_state(user_id)

        # Initialize or update peak
        if state is None:
            self._peak = current_equity
        else:
            self._peak = max(state.peak_equity, current_equity)

        self._current = current_equity

        # Calculate drawdown
        if self._peak > 0:
            drawdown_pct = (self._peak - current_equity) / self._peak
        else:
            drawdown_pct = 0.0

        # Determine level based on % of max_drawdown_pct consumed
        if self.max_drawdown_pct > 0:
            consumed = drawdown_pct / self.max_drawdown_pct
        else:
            consumed = 0.0

        if consumed >= 1.0:
            level = 3
        elif consumed >= 0.75:
            level = 2
        elif consumed >= 0.50:
            level = 1
        else:
            level = 0

        new_state = DrawdownState(
            peak_equity=self._peak,
            current_equity=current_equity,
            drawdown_pct=round(drawdown_pct, 6),
            level=level,
        )
        await self._save_state(user_id, new_state)

        if level > 0:
            logger.warning(
                "Drawdown breaker Level %d for user %s: equity=%.2f peak=%.2f "
                "drawdown=%.2f%% (limit=%.2f%%)",
                level, user_id, current_equity, self._peak,
                drawdown_pct * 100, self.max_drawdown_pct * 100,
            )

        return level

    async def get_sizing_multiplier(self, user_id: str) -> float:
        """Return sizing multiplier based on current drawdown level.

        Level 0: 1.0 (full sizing)
        Level 1: 0.5 (half sizing)
        Level 2+: 0.0 (no new trades)
        """
        state = await self._load_state(user_id)
        if state is None:
            return 1.0
        if state.level >= 2:
            return 0.0
        if state.level == 1:
            return 0.5
        return 1.0

    async def get_state(self, user_id: str) -> DrawdownState | None:
        """Return current drawdown state for API/monitoring."""
        return await self._load_state(user_id)

    async def _load_state(self, user_id: str) -> DrawdownState | None:
        """Load state from Redis."""
        try:
            from app.core.redis_client import redis_client

            key = f"{REDIS_KEY_PREFIX}:{user_id}"
            data = await redis_client.get(key)
            if data:
                d = json.loads(data)
                return DrawdownState(**d)
        except Exception as e:
            logger.warning("Failed to load drawdown state from Redis: %s", e)
        return None

    async def _save_state(self, user_id: str, state: DrawdownState) -> None:
        """Save state to Redis."""
        try:
            from app.core.redis_client import redis_client

            key = f"{REDIS_KEY_PREFIX}:{user_id}"
            data = json.dumps({
                "peak_equity": state.peak_equity,
                "current_equity": state.current_equity,
                "drawdown_pct": state.drawdown_pct,
                "level": state.level,
            })
            await redis_client.set(key, data, ex=7 * 86400)  # 7 day TTL
        except Exception as e:
            logger.warning("Failed to save drawdown state to Redis: %s", e)
