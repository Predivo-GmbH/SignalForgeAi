"""
Layer 2: Zone Identifier.

Finds potential entry zones using Fibonacci retracement
and VWAP deviation bands.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.engine.indicators import calculate_fib_levels, compute_vwap
from app.engine.layers.trend import Trend, TrendResult


@dataclass
class EntryZone:
    zone_type: str
    upper: float
    lower: float
    strength: float
    levels: dict[float, float] | None = None

    def to_dict(self) -> dict:
        return {
            "zone_type": self.zone_type,
            "upper": self.upper,
            "lower": self.lower,
            "strength": self.strength,
        }


class ZoneIdentifier:
    """
    Layer 2: Finds potential entry zones using Fibonacci, VWAP bands,
    and support/resistance levels.
    """

    def find_zones(
        self, candles: pd.DataFrame, trend: TrendResult
    ) -> list[EntryZone]:
        zones: list[EntryZone] = []
        zones.extend(self._fibonacci_zones(candles, trend))
        zones.extend(self._vwap_deviation_zones(candles))
        return zones

    def _fibonacci_zones(
        self, candles: pd.DataFrame, trend: TrendResult
    ) -> list[EntryZone]:
        swing_high_idx = candles["high"].idxmax()
        swing_low_idx = candles["low"].idxmin()
        swing_high = float(candles["high"].loc[swing_high_idx])
        swing_low = float(candles["low"].loc[swing_low_idx])

        if swing_high == swing_low:
            return []

        if trend.direction == Trend.BULLISH:
            fib_levels = calculate_fib_levels(swing_low, swing_high)
        else:
            fib_levels = calculate_fib_levels(swing_high, swing_low)

        golden_upper = fib_levels[0.382]
        golden_lower = fib_levels[0.618]

        if golden_upper < golden_lower:
            golden_upper, golden_lower = golden_lower, golden_upper

        return [
            EntryZone(
                zone_type="fibonacci_golden",
                upper=float(golden_upper),
                lower=float(golden_lower),
                strength=0.7,
                levels=fib_levels,
            )
        ]

    def _vwap_deviation_zones(self, candles: pd.DataFrame) -> list[EntryZone]:
        vwap = compute_vwap(candles)
        std = candles["close"].rolling(20).std()

        if std.iloc[-1] is None or np.isnan(std.iloc[-1]):
            return []

        vwap_val = float(vwap.iloc[-1])
        std_val = float(std.iloc[-1])

        return [
            EntryZone(
                zone_type="vwap_1sigma",
                upper=vwap_val + std_val,
                lower=vwap_val - std_val,
                strength=0.5,
            ),
            EntryZone(
                zone_type="vwap_2sigma",
                upper=vwap_val + 2 * std_val,
                lower=vwap_val - 2 * std_val,
                strength=0.8,
            ),
        ]
