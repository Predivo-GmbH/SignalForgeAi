"""
Layer 4: Trigger Detector.

Checks for actionable entry triggers using multiple confirmation signals.
Requires a configurable number of trigger types to fire within a lookback
window for a confirmed entry.

Trigger types:
  A. MACD crossover in trend direction
  B. RSI crossing midline (50)
  C. Stochastic leaving overbought/oversold
  D. Engulfing candlestick pattern
  E. Price reclaiming zone
"""

from dataclasses import dataclass, field

import pandas as pd

from app.engine.indicators import compute_macd, compute_rsi, compute_stochastic
from app.engine.layers.trend import Trend, TrendResult
from app.engine.layers.zones import EntryZone


@dataclass
class TriggerResult:
    confirmed: bool
    price: float
    confirmations: list[str] = field(default_factory=list)


class TriggerDetector:
    """
    Layer 4: Checks for actionable entry triggers.

    Evaluates 5 independent trigger conditions over a configurable lookback
    window and requires a configurable number of confirmations.
    """

    def __init__(
        self,
        min_confirmations: int = 2,
        lookback: int = 1,
    ):
        self.min_confirmations = min_confirmations
        self.lookback = lookback

    def check(
        self,
        candles: pd.DataFrame,
        zone: EntryZone,
        trend: TrendResult,
    ) -> TriggerResult:
        """Evaluate all trigger conditions against candle data."""
        confirmations: list[str] = []
        price = float(candles["close"].iloc[-1])

        if self._check_macd_crossover(candles, trend, self.lookback):
            confirmations.append("macd_crossover")

        if self._check_rsi_midline(candles, trend, self.lookback):
            confirmations.append("rsi_midline_cross")

        if self._check_stochastic_exit(candles, trend, self.lookback):
            confirmations.append("stochastic_exit_extreme")

        if self._check_engulfing(candles, trend, self.lookback):
            confirmations.append("engulfing_candle")

        if self._check_zone_reclaim(candles, zone, trend, self.lookback):
            confirmations.append("zone_reclaim")

        confirmed = len(confirmations) >= self.min_confirmations

        return TriggerResult(
            confirmed=confirmed,
            price=price,
            confirmations=confirmations,
        )

    # ------------------------------------------------------------------
    # Trigger A: MACD crossover in trend direction
    # ------------------------------------------------------------------
    @staticmethod
    def _check_macd_crossover(
        candles: pd.DataFrame, trend: TrendResult, lookback: int = 1,
    ) -> bool:
        """MACD line crosses signal line in the direction of the trend."""
        if len(candles) < 35:
            return False

        macd_line, signal_line, _ = compute_macd(candles["close"])

        for offset in range(lookback):
            idx = -1 - offset
            prev_idx = idx - 1
            if abs(prev_idx) > len(macd_line):
                break

            cur_macd = macd_line.iloc[idx]
            prev_macd = macd_line.iloc[prev_idx]
            cur_signal = signal_line.iloc[idx]
            prev_signal = signal_line.iloc[prev_idx]

            nans = (
                pd.isna(cur_macd) or pd.isna(prev_macd)
                or pd.isna(cur_signal) or pd.isna(prev_signal)
            )
            if nans:
                continue

            if trend.direction == Trend.BULLISH:
                if prev_macd <= prev_signal and cur_macd > cur_signal:
                    return True
            elif trend.direction == Trend.BEARISH:
                if prev_macd >= prev_signal and cur_macd < cur_signal:
                    return True

        return False

    # ------------------------------------------------------------------
    # Trigger B: RSI crossing midline (50)
    # ------------------------------------------------------------------
    @staticmethod
    def _check_rsi_midline(
        candles: pd.DataFrame, trend: TrendResult, lookback: int = 1,
    ) -> bool:
        """RSI crosses the 50 midline in the direction of the trend."""
        if len(candles) < 20:
            return False

        rsi = compute_rsi(candles["close"], period=14)

        for offset in range(lookback):
            idx = -1 - offset
            prev_idx = idx - 1
            if abs(prev_idx) > len(rsi):
                break

            cur_rsi = rsi.iloc[idx]
            prev_rsi = rsi.iloc[prev_idx]

            if pd.isna(cur_rsi) or pd.isna(prev_rsi):
                continue

            if trend.direction == Trend.BULLISH:
                if prev_rsi <= 50 and cur_rsi > 50:
                    return True
            elif trend.direction == Trend.BEARISH:
                if prev_rsi >= 50 and cur_rsi < 50:
                    return True

        return False

    # ------------------------------------------------------------------
    # Trigger C: Stochastic leaving overbought/oversold
    # ------------------------------------------------------------------
    @staticmethod
    def _check_stochastic_exit(
        candles: pd.DataFrame, trend: TrendResult, lookback: int = 1,
    ) -> bool:
        """Stochastic %K exits overbought (>80) or oversold (<20) territory."""
        if len(candles) < 20:
            return False

        slowk, _ = compute_stochastic(candles)

        for offset in range(lookback):
            idx = -1 - offset
            prev_idx = idx - 1
            if abs(prev_idx) > len(slowk):
                break

            cur_k = slowk.iloc[idx]
            prev_k = slowk.iloc[prev_idx]

            if pd.isna(cur_k) or pd.isna(prev_k):
                continue

            if trend.direction == Trend.BULLISH:
                if prev_k <= 20 and cur_k > 20:
                    return True
            elif trend.direction == Trend.BEARISH:
                if prev_k >= 80 and cur_k < 80:
                    return True

        return False

    # ------------------------------------------------------------------
    # Trigger D: Engulfing candlestick pattern
    # ------------------------------------------------------------------
    @staticmethod
    def _check_engulfing(
        candles: pd.DataFrame, trend: TrendResult, lookback: int = 1,
    ) -> bool:
        """Bullish or bearish engulfing pattern within lookback window."""
        if len(candles) < 2:
            return False

        for offset in range(lookback):
            idx = -1 - offset
            prev_idx = idx - 1
            if abs(prev_idx) >= len(candles):
                break

            prev_open = candles["open"].iloc[prev_idx]
            prev_close = candles["close"].iloc[prev_idx]
            cur_open = candles["open"].iloc[idx]
            cur_close = candles["close"].iloc[idx]

            if trend.direction == Trend.BULLISH:
                prev_bearish = prev_close < prev_open
                cur_bullish = cur_close > cur_open
                engulfs = cur_open <= prev_close and cur_close >= prev_open
                if prev_bearish and cur_bullish and engulfs:
                    return True
            elif trend.direction == Trend.BEARISH:
                prev_bullish = prev_close > prev_open
                cur_bearish = cur_close < cur_open
                engulfs = cur_open >= prev_close and cur_close <= prev_open
                if prev_bullish and cur_bearish and engulfs:
                    return True

        return False

    # ------------------------------------------------------------------
    # Trigger E: Price reclaiming zone
    # ------------------------------------------------------------------
    @staticmethod
    def _check_zone_reclaim(
        candles: pd.DataFrame, zone: EntryZone, trend: TrendResult,
        lookback: int = 1,
    ) -> bool:
        """Price moves back into the entry zone from outside it."""
        if len(candles) < 2:
            return False

        for offset in range(lookback):
            idx = -1 - offset
            prev_idx = idx - 1
            if abs(prev_idx) >= len(candles):
                break

            prev_close = candles["close"].iloc[prev_idx]
            cur_close = candles["close"].iloc[idx]

            if trend.direction == Trend.BULLISH:
                if prev_close < zone.lower and cur_close >= zone.lower:
                    return True
            elif trend.direction == Trend.BEARISH:
                if prev_close > zone.upper and cur_close <= zone.upper:
                    return True

        return False
