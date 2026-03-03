"""Correlation monitor — tracks pairwise correlation between open position symbols.

Thresholds:
  - Warning:  > 0.7 correlation
  - Critical: > 0.85 correlation

Output: exposure_penalty (1.0 = no penalty, scales down to penalty_at_critical)
Linear interpolation between warning and critical.

Cached in Redis: signalforge:correlations:{user_id} (TTL 10min)
"""

import json
import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

REDIS_KEY_PREFIX = "signalforge:correlations"
CACHE_TTL = 600  # 10 minutes


@dataclass
class CorrelationAlert:
    symbol_a: str
    symbol_b: str
    correlation: float
    risk_level: str  # "warning" or "critical"


@dataclass
class CorrelationResult:
    matrix: dict[str, dict[str, float]]
    alerts: list[CorrelationAlert] = field(default_factory=list)
    max_correlation: float = 0.0
    exposure_penalty: float = 1.0


class CorrelationMonitor:
    """Monitors correlation between symbols of open positions."""

    def __init__(
        self,
        threshold_warning: float = 0.7,
        threshold_critical: float = 0.85,
        lookback_bars: int = 100,
        penalty_at_critical: float = 0.5,
    ):
        self.threshold_warning = threshold_warning
        self.threshold_critical = threshold_critical
        self.lookback_bars = lookback_bars
        self.penalty_at_critical = penalty_at_critical

    async def compute(
        self,
        db: AsyncSession,
        symbols: list[str],
        timeframe: str = "1h",
    ) -> CorrelationResult:
        """Compute pairwise correlation matrix for the given symbols."""
        from app.models.candle import Candle

        if len(symbols) < 2:
            return CorrelationResult(matrix={}, max_correlation=0.0, exposure_penalty=1.0)

        # Load all close prices in one query (PERF-002: batch fetch)
        all_candles_result = await db.execute(
            select(Candle.symbol, Candle.close, Candle.time)
            .where(Candle.symbol.in_(symbols), Candle.timeframe == timeframe)
            .order_by(Candle.symbol, Candle.time.desc())
        )
        all_rows = all_candles_result.fetchall()

        # Group by symbol in Python and apply lookback limit
        price_data: dict[str, list[float]] = {}
        rows_by_symbol: dict[str, list[float]] = {}
        for row in all_rows:
            sym = row[0]
            rows_by_symbol.setdefault(sym, []).append(row[1])

        for sym, closes in rows_by_symbol.items():
            trimmed = closes[:self.lookback_bars]  # already desc ordered
            if len(trimmed) >= 30:
                price_data[sym] = list(reversed(trimmed))

        valid_symbols = list(price_data.keys())
        if len(valid_symbols) < 2:
            return CorrelationResult(matrix={}, max_correlation=0.0, exposure_penalty=1.0)

        # Align lengths (use shortest series)
        min_len = min(len(v) for v in price_data.values())
        aligned = {s: prices[-min_len:] for s, prices in price_data.items()}

        # Build DataFrame and compute correlation
        df = pd.DataFrame(aligned)
        # Use returns instead of raw prices for better correlation
        returns = df.pct_change().dropna()

        if len(returns) < 10:
            return CorrelationResult(matrix={}, max_correlation=0.0, exposure_penalty=1.0)

        corr_matrix = returns.corr()

        # Build result
        matrix_dict: dict[str, dict[str, float]] = {}
        alerts: list[CorrelationAlert] = []
        max_corr = 0.0

        for i, sym_a in enumerate(valid_symbols):
            matrix_dict[sym_a] = {}
            for j, sym_b in enumerate(valid_symbols):
                corr_val = float(corr_matrix.loc[sym_a, sym_b])
                if np.isnan(corr_val):
                    corr_val = 0.0
                matrix_dict[sym_a][sym_b] = round(corr_val, 4)

                # Track max off-diagonal correlation
                if i < j:
                    abs_corr = abs(corr_val)
                    if abs_corr > max_corr:
                        max_corr = abs_corr

                    if abs_corr >= self.threshold_critical:
                        alerts.append(CorrelationAlert(
                            symbol_a=sym_a,
                            symbol_b=sym_b,
                            correlation=round(corr_val, 4),
                            risk_level="critical",
                        ))
                    elif abs_corr >= self.threshold_warning:
                        alerts.append(CorrelationAlert(
                            symbol_a=sym_a,
                            symbol_b=sym_b,
                            correlation=round(corr_val, 4),
                            risk_level="warning",
                        ))

        penalty = self._calculate_penalty(max_corr)

        return CorrelationResult(
            matrix=matrix_dict,
            alerts=alerts,
            max_correlation=round(max_corr, 4),
            exposure_penalty=round(penalty, 4),
        )

    def _calculate_penalty(self, max_corr: float) -> float:
        """Linear interpolation of penalty between warning and critical thresholds."""
        if max_corr <= self.threshold_warning:
            return 1.0
        if max_corr >= self.threshold_critical:
            return self.penalty_at_critical
        # Linear interpolation
        t = (max_corr - self.threshold_warning) / (
            self.threshold_critical - self.threshold_warning
        )
        return 1.0 - t * (1.0 - self.penalty_at_critical)

    async def store_result(self, user_id: str, result: CorrelationResult) -> None:
        """Store correlation result in Redis for API access."""
        try:
            from app.core.redis_client import redis_client

            key = f"{REDIS_KEY_PREFIX}:{user_id}"
            data = json.dumps({
                "matrix": result.matrix,
                "alerts": [
                    {
                        "symbol_a": a.symbol_a,
                        "symbol_b": a.symbol_b,
                        "correlation": a.correlation,
                        "risk_level": a.risk_level,
                    }
                    for a in result.alerts
                ],
                "max_correlation": result.max_correlation,
                "exposure_penalty": result.exposure_penalty,
            })
            await redis_client.set(key, data, ex=CACHE_TTL)
        except Exception as e:
            logger.warning("Failed to store correlation result in Redis: %s", e)

    async def get_cached_result(self, user_id: str) -> CorrelationResult | None:
        """Get cached correlation result from Redis."""
        try:
            from app.core.redis_client import redis_client

            key = f"{REDIS_KEY_PREFIX}:{user_id}"
            data = await redis_client.get(key)
            if data:
                d = json.loads(data)
                alerts = [
                    CorrelationAlert(**a)
                    for a in d.get("alerts", [])
                ]
                return CorrelationResult(
                    matrix=d.get("matrix", {}),
                    alerts=alerts,
                    max_correlation=d.get("max_correlation", 0.0),
                    exposure_penalty=d.get("exposure_penalty", 1.0),
                )
        except Exception as e:
            logger.warning("Failed to load cached correlation result: %s", e)
        return None

    async def get_cached_penalty(self, user_id: str) -> float:
        """Get cached exposure penalty. Returns 1.0 if not cached."""
        result = await self.get_cached_result(user_id)
        if result:
            return result.exposure_penalty
        return 1.0
