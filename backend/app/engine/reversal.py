"""
Layer 6: Reversal Monitor.

Monitors open positions for trend-reversal signals and recommends
exit actions (hold, partial close, tighten stop, or full close)
based on aggregated severity of reversal indicators.

Indicators checked:
  - EMA 10/20 crossover against position direction
  - Volume divergence (declining volume against trend)
  - MACD histogram divergence (weakening momentum)

Severity aggregation:
  - max severity >= 0.8  -> CLOSE_POSITION
  - max severity >= 0.6  -> TIGHTEN_STOP
  - max severity >= 0.4 AND 2+ alerts -> PARTIAL_CLOSE
  - else -> HOLD
"""

from enum import Enum

import pandas as pd

from app.engine.indicators import compute_ema, compute_macd


class ReversalAction(Enum):
    HOLD = "hold"
    PARTIAL_CLOSE = "partial_close"
    TIGHTEN_STOP = "tighten_stop"
    CLOSE_POSITION = "close_position"


class ReversalMonitor:
    """
    Layer 6: Monitors open positions for reversal signals.

    Given current candle data and position direction, evaluates multiple
    reversal indicators and returns a recommended exit action.
    """

    def check_position(self, candles: pd.DataFrame, direction: str) -> ReversalAction:
        """
        Check whether an open position should be adjusted or closed.

        Args:
            candles: OHLCV DataFrame with at least 30 rows.
            direction: "LONG" or "SHORT".

        Returns:
            ReversalAction indicating recommended action.
        """
        alerts: list[tuple[str, float]] = []

        ema_severity = self._check_ema_cross(candles, direction)
        if ema_severity > 0:
            alerts.append(("ema_cross", ema_severity))

        vol_severity = self._check_volume_divergence(candles, direction)
        if vol_severity > 0:
            alerts.append(("volume_divergence", vol_severity))

        macd_severity = self._check_macd_divergence(candles, direction)
        if macd_severity > 0:
            alerts.append(("macd_divergence", macd_severity))

        return self._aggregate(alerts)

    def _check_ema_cross(self, candles: pd.DataFrame, direction: str) -> float:
        """
        Check EMA 10/20 cross against position direction.

        Returns severity 0.5 if the fast EMA has crossed the slow EMA
        in the direction opposing the position.
        """
        close = candles["close"]
        if len(close) < 20:
            return 0.0

        ema_10 = compute_ema(close, 10)
        ema_20 = compute_ema(close, 20)

        fast = float(ema_10.iloc[-1])
        slow = float(ema_20.iloc[-1])

        if direction == "LONG" and fast < slow:
            # Fast EMA crossed below slow — bearish signal against long
            return 0.5
        elif direction == "SHORT" and fast > slow:
            # Fast EMA crossed above slow — bullish signal against short
            return 0.5

        return 0.0

    def _check_volume_divergence(self, candles: pd.DataFrame, direction: str) -> float:
        """
        Check for declining volume against the trend direction.

        Compares recent average volume (last 10 bars) against prior
        average volume (bars 10-30). If volume is declining while
        price continues in position direction, returns severity 0.4.
        """
        if len(candles) < 30:
            return 0.0

        volume = candles["volume"]
        close = candles["close"]

        recent_vol = float(volume.tail(10).mean())
        prior_vol = float(volume.iloc[-30:-10].mean())

        if prior_vol == 0:
            return 0.0

        vol_ratio = recent_vol / prior_vol

        # Check if price is still moving in position direction
        recent_price_change = float(close.iloc[-1]) - float(close.iloc[-10])

        if direction == "LONG" and recent_price_change > 0 and vol_ratio < 0.6:
            # Price rising but volume declining — divergence
            return 0.4
        elif direction == "SHORT" and recent_price_change < 0 and vol_ratio < 0.6:
            # Price falling but volume declining — divergence
            return 0.4

        return 0.0

    def _check_macd_divergence(self, candles: pd.DataFrame, direction: str) -> float:
        """
        Check MACD histogram for weakening momentum.

        If the histogram is moving against the position direction
        (negative for longs, positive for shorts), returns severity 0.7.
        Also checks for histogram declining over last 5 bars.
        """
        close = candles["close"]
        if len(close) < 35:
            return 0.0

        _, _, histogram = compute_macd(close)
        hist_clean = histogram.dropna()

        if len(hist_clean) < 5:
            return 0.0

        current_hist = float(hist_clean.iloc[-1])

        # Normalize histogram against price to avoid false signals from noise.
        # A histogram of -0.01 on a $150 asset is noise, not a reversal.
        price = float(close.iloc[-1])
        if price > 0:
            normalized_hist = abs(current_hist) / price
        else:
            normalized_hist = 0.0

        # Require histogram to be at least 0.05% of price to be meaningful
        significance_threshold = 0.0005

        # Check histogram direction against position
        if direction == "LONG" and current_hist < 0 and normalized_hist > significance_threshold:
            return 0.7
        elif direction == "SHORT" and current_hist > 0 and normalized_hist > significance_threshold:
            return 0.7

        # Check for declining histogram momentum (weakening trend)
        recent_hist = hist_clean.tail(5)
        hist_slope = float(recent_hist.iloc[-1]) - float(recent_hist.iloc[0])

        if direction == "LONG" and hist_slope < 0 and current_hist > 0:
            # Still positive but declining — early warning
            declining_ratio = abs(hist_slope) / max(abs(current_hist), 1e-10)
            if declining_ratio > 1.0:
                return 0.4
        elif direction == "SHORT" and hist_slope > 0 and current_hist < 0:
            # Still negative but rising — early warning
            declining_ratio = abs(hist_slope) / max(abs(current_hist), 1e-10)
            if declining_ratio > 1.0:
                return 0.4

        return 0.0

    @staticmethod
    def _aggregate(alerts: list[tuple[str, float]]) -> ReversalAction:
        """
        Aggregate alert severities into a single action recommendation.

        Rules:
          - max severity >= 0.8  -> CLOSE_POSITION
          - max severity >= 0.6  -> TIGHTEN_STOP
          - max severity >= 0.4 AND 2+ alerts -> PARTIAL_CLOSE
          - else -> HOLD
        """
        if not alerts:
            return ReversalAction.HOLD

        max_severity = max(s for _, s in alerts)
        alert_count = len(alerts)

        if max_severity >= 0.8:
            return ReversalAction.CLOSE_POSITION
        elif max_severity >= 0.6:
            return ReversalAction.TIGHTEN_STOP
        elif max_severity >= 0.4 and alert_count >= 2:
            return ReversalAction.PARTIAL_CLOSE
        else:
            return ReversalAction.HOLD
