"""Regime-based allocation manager.

Reads the current HMM regime from Redis (populated by the weekly
``train_hmm_regime`` task) and maps it to a target allocation percentage
using a configurable table.  Smoothing prevents whiplash on regime
transitions by moving gradually toward the target over *N* bars.

State stored in Redis: ``signalforge:regime_alloc:{user_id}``

Follows the same pattern as ``cppi.py`` (dataclass state, async methods,
Redis-backed persistence).
"""

import json
import logging
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

REDIS_KEY_PREFIX = "signalforge:regime_alloc"

# ---------------------------------------------------------------------------
# Preset allocation tables
# Maps HMM regime label → target allocation (0.0–1.0)
# HMMRegimeModel uses 3 states: low_vol, trending, high_vol
# ---------------------------------------------------------------------------
ALLOCATION_TABLES: dict[str, dict[str, float]] = {
    "conservative": {"low_vol": 1.0, "trending": 0.80, "high_vol": 0.30},
    "moderate":     {"low_vol": 1.0, "trending": 0.90, "high_vol": 0.50},
    "aggressive":   {"low_vol": 1.0, "trending": 1.00, "high_vol": 0.70},
}

# Fallback when regime is unknown
DEFAULT_ALLOCATION = 1.0


@dataclass
class RegimeAllocationState:
    regime: str
    target_pct: float
    current_pct: float
    allocation_table_name: str
    smoothing_bars: int
    last_updated: float  # unix timestamp


class RegimeAllocator:
    """Manages regime-based allocation per user.

    Parameters
    ----------
    allocation_table : str or dict
        Name of a preset table ("conservative", "moderate", "aggressive")
        or a custom ``{regime: pct}`` dict.
    smoothing_bars : int
        Number of bars over which to linearly smooth toward the target.
        1 = instant transition, 3 = gradual (recommended), 5 = very smooth.
    """

    def __init__(
        self,
        allocation_table: str | dict = "moderate",
        smoothing_bars: int = 3,
    ):
        if isinstance(allocation_table, str):
            self.table = ALLOCATION_TABLES.get(allocation_table, ALLOCATION_TABLES["moderate"])
            self.table_name = allocation_table
        else:
            self.table = allocation_table
            self.table_name = "custom"
        self.smoothing_bars = max(1, smoothing_bars)

    async def get_target_allocation(
        self, user_id: str, symbol: str = "BTC/USDT",
    ) -> float:
        """Compute the current allocation percentage (0.0–1.0).

        Reads the HMM regime from Redis, looks up the target allocation
        from the table, and smooths toward it over ``smoothing_bars`` steps.
        """
        # 1. Read current HMM regime from Redis
        regime = await self._read_hmm_regime(symbol)

        # 2. Look up target from table
        target = self.table.get(regime, DEFAULT_ALLOCATION)

        # 3. Load existing state and apply smoothing
        state = await self._load_state(user_id)

        if state is None:
            current = target  # First call — no smoothing
        else:
            # Move 1/smoothing_bars of the gap per call
            gap = target - state.current_pct
            step = gap / self.smoothing_bars
            current = state.current_pct + step

        # Clamp
        current = max(0.0, min(1.0, current))

        new_state = RegimeAllocationState(
            regime=regime,
            target_pct=round(target, 4),
            current_pct=round(current, 4),
            allocation_table_name=self.table_name,
            smoothing_bars=self.smoothing_bars,
            last_updated=time.time(),
        )
        await self._save_state(user_id, new_state)

        if current < 1.0:
            logger.info(
                "RegimeAllocator: user %s symbol %s regime=%s "
                "target=%.0f%% current=%.0f%% (table=%s, smooth=%d)",
                user_id, symbol, regime,
                target * 100, current * 100,
                self.table_name, self.smoothing_bars,
            )

        return current

    async def get_state(self, user_id: str) -> RegimeAllocationState | None:
        """Return current allocation state for API/monitoring."""
        return await self._load_state(user_id)

    async def reset(self, user_id: str) -> None:
        """Reset allocation state (called when user changes config)."""
        try:
            from app.core.redis_client import redis_client

            key = f"{REDIS_KEY_PREFIX}:{user_id}"
            await redis_client.delete(key)
        except Exception:
            logger.warning("Failed to reset regime allocation state for user %s", user_id, exc_info=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _read_hmm_regime(self, symbol: str) -> str:
        """Read the current HMM regime label from Redis."""
        try:
            from app.core.redis_client import redis_client

            data = await redis_client.get(f"signalforge:hmm_regime:{symbol}")
            if data:
                from app.engine.layers.hmm_regime import HMMRegimeModel

                model = HMMRegimeModel.deserialize(data)
                # The model stores the last predicted state in its state_map.
                # We need candle data to predict, but the serialized model
                # doesn't include that.  The hmm_train task stores the raw
                # serialized model.  For the allocator we need a simpler
                # approach: store the regime label directly in Redis alongside
                # the model.  Check if a separate label key exists first.
                label = await redis_client.get(f"signalforge:hmm_regime_label:{symbol}")
                if label:
                    return label.decode() if isinstance(label, bytes) else label
                # Fallback: if no label cached, default to "trending"
                return "trending"
        except Exception as e:
            logger.warning("Failed to read HMM regime from Redis: %s", e)
        return "trending"

    async def _load_state(self, user_id: str) -> RegimeAllocationState | None:
        """Load state from Redis."""
        try:
            from app.core.redis_client import redis_client

            key = f"{REDIS_KEY_PREFIX}:{user_id}"
            data = await redis_client.get(key)
            if data:
                d = json.loads(data)
                return RegimeAllocationState(**d)
        except Exception:
            logger.warning("Failed to load regime allocation state for user %s", user_id, exc_info=True)
        return None

    async def _save_state(self, user_id: str, state: RegimeAllocationState) -> None:
        """Save state to Redis."""
        try:
            from app.core.redis_client import redis_client

            key = f"{REDIS_KEY_PREFIX}:{user_id}"
            data = json.dumps({
                "regime": state.regime,
                "target_pct": state.target_pct,
                "current_pct": state.current_pct,
                "allocation_table_name": state.allocation_table_name,
                "smoothing_bars": state.smoothing_bars,
                "last_updated": state.last_updated,
            })
            await redis_client.set(key, data, ex=7 * 86400)  # 7 day TTL
        except Exception as e:
            logger.warning("Failed to save regime allocation state to Redis: %s", e)
