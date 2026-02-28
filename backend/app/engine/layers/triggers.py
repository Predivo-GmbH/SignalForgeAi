"""
Layer 4: Trigger Detector.

Checks for actionable entry triggers using multiple confirmation signals.
Requires at least 2 out of 5 trigger types to fire for a confirmed entry.

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

    Evaluates 5 independent trigger conditions on the latest candle data
    and requires at least 2 confirmations for a valid entry signal.
    """

    def check(
        self,
        candles: pd.DataFrame,
        zone: EntryZone,
        trend: TrendResult,
    ) -> TriggerResult:
        """Evaluate all trigger conditions against current candle data."""
        confirmations: list[str] = []
        price = float(candles["close"].iloc[-1])

        if self._check_macd_crossover(candles, trend):
            confirmations.append("macd_crossover")

        if self._check_rsi_midline(candles, trend):
            confirmations.append("rsi_midline_cross")

        if self._check_stochastic_exit(candles, trend):
            confirmations.append("stochastic_exit_extreme")

        if self._check_engulfing(candles, trend):
            confirmations.append("engulfing_candle")

        if self._check_zone_reclaim(candles, zone, trend):
            confirmations.append("zone_reclaim")

        confirmed = len(confirmations) >= 2

        return TriggerResult(
            confirmed=confirmed,
            price=price,
            confirmations=confirmations,
        )

    # ------------------------------------------------------------------
    # Trigger A: MACD crossover in trend direction
    # ------------------------------------------------------------------
    @staticmethod
    def _check_macd_crossover(candles: pd.DataFrame, trend: TrendResult) -> bool:
        """MACD line crosses signal line in the direction of the trend."""
        if len(candles) < 35:
            return False

        macd_line, signal_line, _ = compute_macd(candles["close"])
        cur_macd = macd_line.iloc[-1]
        prev_macd = macd_line.iloc[-2]
        cur_signal = signal_line.iloc[-1]
        prev_signal = signal_line.iloc[-2]

        if pd.isna(cur_macd) or pd.isna(prev_macd) or pd.isna(cur_signal) or pd.isna(prev_signal):
            return False

        if trend.direction == Trend.BULLISH:
            return prev_macd <= prev_signal and cur_macd > cur_signal
        elif trend.direction == Trend.BEARISH:
            return prev_macd >= prev_signal and cur_macd < cur_signal

        return False

    # ------------------------------------------------------------------
    # Trigger B: RSI crossing midline (50)
    # ------------------------------------------------------------------
    @staticmethod
    def _check_rsi_midline(candles: pd.DataFrame, trend: TrendResult) -> bool:
        """RSI crosses the 50 midline in the direction of the trend."""
        if len(candles) < 20:
            return False

        rsi = compute_rsi(candles["close"], period=14)
        cur_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2]

        if pd.isna(cur_rsi) or pd.isna(prev_rsi):
            return False

        if trend.direction == Trend.BULLISH:
            return prev_rsi <= 50 and cur_rsi > 50
        elif trend.direction == Trend.BEARISH:
            return prev_rsi >= 50 and cur_rsi < 50

        return False

    # ------------------------------------------------------------------
    # Trigger C: Stochastic leaving overbought/oversold
    # ------------------------------------------------------------------
    @staticmethod
    def _check_stochastic_exit(candles: pd.DataFrame, trend: TrendResult) -> bool:
        """Stochastic %K exits overbought (>80) or oversold (<20) territory."""
        if len(candles) < 20:
            return False

        slowk, _ = compute_stochastic(candles)
        cur_k = slowk.iloc[-1]
        prev_k = slowk.iloc[-2]

        if pd.isna(cur_k) or pd.isna(prev_k):
            return False

        if trend.direction == Trend.BULLISH:
            # Leaving oversold: was below 20, now above 20
            return prev_k <= 20 and cur_k > 20
        elif trend.direction == Trend.BEARISH:
            # Leaving overbought: was above 80, now below 80
            return prev_k >= 80 and cur_k < 80

        return False

    # ------------------------------------------------------------------
    # Trigger D: Engulfing candlestick pattern
    # ------------------------------------------------------------------
    @staticmethod
    def _check_engulfing(candles: pd.DataFrame, trend: TrendResult) -> bool:
        """Bullish or bearish engulfing pattern on the latest two candles."""
        if len(candles) < 2:
            return False

        prev_open = candles["open"].iloc[-2]
        prev_close = candles["close"].iloc[-2]
        cur_open = candles["open"].iloc[-1]
        cur_close = candles["close"].iloc[-1]

        if trend.direction == Trend.BULLISH:
            # Bullish engulfing: previous candle bearish, current candle bullish
            # and current body fully engulfs previous body
            prev_bearish = prev_close < prev_open
            cur_bullish = cur_close > cur_open
            engulfs = cur_open <= prev_close and cur_close >= prev_open
            return prev_bearish and cur_bullish and engulfs
        elif trend.direction == Trend.BEARISH:
            # Bearish engulfing: previous candle bullish, current candle bearish
            # and current body fully engulfs previous body
            prev_bullish = prev_close > prev_open
            cur_bearish = cur_close < cur_open
            engulfs = cur_open >= prev_close and cur_close <= prev_open
            return prev_bullish and cur_bearish and engulfs

        return False

    # ------------------------------------------------------------------
    # Trigger E: Price reclaiming zone
    # ------------------------------------------------------------------
    @staticmethod
    def _check_zone_reclaim(
        candles: pd.DataFrame, zone: EntryZone, trend: TrendResult
    ) -> bool:
        """Price moves back into the entry zone from outside it."""
        if len(candles) < 2:
            return False

        prev_close = candles["close"].iloc[-2]
        cur_close = candles["close"].iloc[-1]

        if trend.direction == Trend.BULLISH:
            # Was below zone, now inside or above lower boundary
            return prev_close < zone.lower and cur_close >= zone.lower
        elif trend.direction == Trend.BEARISH:
            # Was above zone, now inside or below upper boundary
            return prev_close > zone.upper and cur_close <= zone.upper

        return False
