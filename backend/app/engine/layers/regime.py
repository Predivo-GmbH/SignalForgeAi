"""
Layer 0: Regime Detector.

Determines current market regime using ADX (trend strength)
and ATR percentile (volatility context).
Output: TRENDING, RANGING, TRANSITIONING, or CHAOTIC.
"""

from enum import Enum

import pandas as pd

from app.engine.indicators import compute_adx, compute_atr


class Regime(Enum):
    TRENDING = "trending"
    TRENDING_BULL = "trending_bull"
    TRENDING_BEAR = "trending_bear"
    RANGING = "ranging"
    TRANSITIONING = "transitioning"
    CHAOTIC = "chaotic"


class RegimeDetector:
    """
    Layer 0: Determines current market regime using ADX + ATR percentile.
    Output: TRENDING, RANGING, TRANSITIONING, or CHAOTIC.
    """

    def detect(self, candles: pd.DataFrame) -> Regime:
        adx = compute_adx(candles, period=14)
        adx_val = adx.dropna().iloc[-1] if len(adx.dropna()) > 0 else 0
        adx_regime = self._adx_regime(float(adx_val))

        atr_pct = self._atr_percentile(candles, lookback=100)

        # Chaotic: extreme volatility — requires both high ATR percentile
        # AND high ATR relative to price (normalized ATR > 3%).
        # This avoids false CHAOTIC in tight ranges where percentile is high
        # but absolute volatility is low.
        atr = compute_atr(candles, period=14)
        atr_clean = atr.dropna()
        price = float(candles["close"].iloc[-1])
        if len(atr_clean) > 0 and price > 0:
            normalized_atr = float(atr_clean.iloc[-1]) / price
        else:
            normalized_atr = 0.0

        if atr_pct > 90 and normalized_atr > 0.03:
            return Regime.CHAOTIC

        # Consensus between ADX and ATR
        if adx_regime == Regime.TRENDING:
            if atr_pct < 20:
                return Regime.TRANSITIONING  # Low vol but ADX high = weakening trend
            return Regime.TRENDING
        elif adx_regime == Regime.RANGING:
            return Regime.RANGING
        else:
            return Regime.TRANSITIONING

    def _adx_regime(self, adx_value: float) -> Regime:
        if adx_value > 25:
            return Regime.TRENDING
        elif adx_value < 20:
            return Regime.RANGING
        else:
            return Regime.TRANSITIONING

    def _atr_percentile(self, candles: pd.DataFrame, lookback: int = 100) -> float:
        atr = compute_atr(candles, period=14)
        atr_clean = atr.dropna()
        if len(atr_clean) < 2:
            return 50.0
        tail = atr_clean.tail(lookback)
        current = tail.iloc[-1]
        percentile = float((tail < current).mean() * 100)
        return percentile
