"""
Layer 1: Trend Filter.

Determines dominant trend direction using EMA alignment (50/100/200)
and slope of the 200 EMA.
"""

from dataclasses import dataclass
from enum import Enum

import pandas as pd

from app.engine.indicators import compute_ema, compute_vwap


class Trend(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    UNDETERMINED = "undetermined"


@dataclass
class TrendResult:
    direction: Trend
    strength: float
    vwap_aligned: bool | None = None


class TrendFilter:
    """
    Layer 1: Determines dominant trend direction.
    Uses 200 EMA as primary, 50/100 EMA alignment, and slope for strength.
    """

    def __init__(self, slope_threshold: float = 0.001):
        self.slope_threshold = slope_threshold

    def evaluate(self, candles: pd.DataFrame) -> TrendResult:
        close = candles["close"]

        if len(close) < 200:
            return TrendResult(direction=Trend.UNDETERMINED, strength=0)

        ema_200 = compute_ema(close, 200)
        ema_100 = compute_ema(close, 100)
        ema_50 = compute_ema(close, 50)

        ema_aligned_bull = ema_50.iloc[-1] > ema_100.iloc[-1] > ema_200.iloc[-1]
        ema_aligned_bear = ema_50.iloc[-1] < ema_100.iloc[-1] < ema_200.iloc[-1]

        # Trend strength via slope of 200 EMA (last 20 bars)
        if ema_200.iloc[-20] != 0:
            ema_slope = (ema_200.iloc[-1] - ema_200.iloc[-20]) / abs(
                ema_200.iloc[-20]
            )
        else:
            ema_slope = 0

        # VWAP alignment
        vwap = compute_vwap(candles)
        above_vwap = bool(close.iloc[-1] > vwap.iloc[-1])

        if ema_aligned_bull and ema_slope > self.slope_threshold:
            return TrendResult(
                direction=Trend.BULLISH,
                strength=float(abs(ema_slope)),
                vwap_aligned=above_vwap,
            )
        elif ema_aligned_bear and ema_slope < -self.slope_threshold:
            return TrendResult(
                direction=Trend.BEARISH,
                strength=float(abs(ema_slope)),
                vwap_aligned=not above_vwap,
            )
        else:
            return TrendResult(
                direction=Trend.UNDETERMINED,
                strength=0,
                vwap_aligned=None,
            )
