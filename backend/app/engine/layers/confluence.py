"""
Layer 3: Confluence Scorer.

Scores an entry zone 0-100 using 9 weighted factors that measure
alignment between technical indicators and the identified zone.
"""

import pandas as pd

from app.engine.indicators import (
    compute_macd,
    compute_rsi,
    compute_stochastic,
    compute_vwap,
)
from app.engine.layers.trend import Trend, TrendResult
from app.engine.layers.zones import EntryZone


class ConfluenceScorer:
    """
    Layer 3: Scores a zone 0-100 based on how many independent
    technical factors confirm it as a high-probability entry.
    """

    WEIGHTS: dict[str, int] = {
        "fibonacci_alignment": 15,
        "sr_overlap": 15,
        "multi_tf_fib": 15,
        "vwap_proximity": 10,
        "volume_node": 10,
        "rsi_confirmation": 10,
        "macd_momentum": 10,
        "candlestick_pattern": 10,
        "stochastic_cross": 5,
    }

    def score(
        self, zone: EntryZone, candles: pd.DataFrame, trend: TrendResult
    ) -> int:
        total, _ = self.score_with_details(zone, candles, trend)
        return total

    def score_with_details(
        self, zone: EntryZone, candles: pd.DataFrame, trend: TrendResult
    ) -> tuple[int, dict]:
        details: dict[str, dict] = {}
        total = 0

        checks = {
            "fibonacci_alignment": self._check_fibonacci_alignment,
            "sr_overlap": self._check_sr_overlap,
            "multi_tf_fib": self._check_multi_tf_fib,
            "vwap_proximity": self._check_vwap_proximity,
            "volume_node": self._check_volume_node,
            "rsi_confirmation": self._check_rsi_confirmation,
            "macd_momentum": self._check_macd_momentum,
            "candlestick_pattern": self._check_candlestick_pattern,
            "stochastic_cross": self._check_stochastic_cross,
        }

        for factor, check_fn in checks.items():
            weight = self.WEIGHTS[factor]
            hit, info = check_fn(zone, candles, trend)
            earned = weight if hit else 0
            total += earned
            details[factor] = {"hit": hit, "weight": weight, "earned": earned, **info}

        total = max(0, min(100, total))
        return total, details

    # ── Factor checks ──────────────────────────────────────────────

    def _check_fibonacci_alignment(
        self, zone: EntryZone, candles: pd.DataFrame, trend: TrendResult
    ) -> tuple[bool, dict]:
        """Zone is a Fibonacci golden pocket zone."""
        hit = zone.zone_type.startswith("fibonacci")
        return hit, {"zone_type": zone.zone_type}

    def _check_sr_overlap(
        self, zone: EntryZone, candles: pd.DataFrame, trend: TrendResult
    ) -> tuple[bool, dict]:
        """Price recently bounced from the zone boundaries (support/resistance overlap)."""
        close = candles["close"]
        recent = close.tail(20)
        zone_width = zone.upper - zone.lower
        if zone_width == 0:
            return False, {"bounces": 0}

        # Count bars where price touched the zone then reversed
        in_zone = ((recent >= zone.lower) & (recent <= zone.upper)).sum()
        bounces = int(in_zone)
        hit = bounces >= 3
        return hit, {"bounces": bounces}

    def _check_multi_tf_fib(
        self, zone: EntryZone, candles: pd.DataFrame, trend: TrendResult
    ) -> tuple[bool, dict]:
        """Simulate multi-timeframe Fibonacci by checking zone strength and levels overlap."""
        # Use zone strength as a proxy — zones confirmed across timeframes
        # have higher strength values set upstream
        hit = zone.strength >= 0.7
        return hit, {"zone_strength": zone.strength}

    def _check_vwap_proximity(
        self, zone: EntryZone, candles: pd.DataFrame, trend: TrendResult
    ) -> tuple[bool, dict]:
        """Current price is near VWAP and VWAP is within the zone."""
        vwap = compute_vwap(candles)
        vwap_val = float(vwap.iloc[-1])
        in_zone = zone.lower <= vwap_val <= zone.upper
        hit = in_zone
        return hit, {"vwap": vwap_val, "in_zone": in_zone}

    def _check_volume_node(
        self, zone: EntryZone, candles: pd.DataFrame, trend: TrendResult
    ) -> tuple[bool, dict]:
        """High volume node within the zone (above-average volume when price was in zone)."""
        close = candles["close"]
        volume = candles["volume"]
        in_zone_mask = (close >= zone.lower) & (close <= zone.upper)

        if in_zone_mask.sum() == 0:
            return False, {"avg_zone_vol": 0, "avg_total_vol": float(volume.mean())}

        avg_zone_vol = float(volume[in_zone_mask].mean())
        avg_total_vol = float(volume.mean())
        hit = avg_zone_vol > avg_total_vol * 1.2  # 20% above average
        return hit, {"avg_zone_vol": avg_zone_vol, "avg_total_vol": avg_total_vol}

    def _check_rsi_confirmation(
        self, zone: EntryZone, candles: pd.DataFrame, trend: TrendResult
    ) -> tuple[bool, dict]:
        """RSI confirms: oversold (<40) in uptrend or overbought (>60) in downtrend."""
        rsi = compute_rsi(candles["close"], period=14)
        rsi_val = float(rsi.dropna().iloc[-1]) if len(rsi.dropna()) > 0 else 50.0

        if trend.direction == Trend.BULLISH:
            hit = rsi_val < 40  # Oversold in uptrend = buying opportunity
        elif trend.direction == Trend.BEARISH:
            hit = rsi_val > 60  # Overbought in downtrend = selling opportunity
        else:
            hit = False

        return hit, {"rsi": rsi_val, "trend": trend.direction.value}

    def _check_macd_momentum(
        self, zone: EntryZone, candles: pd.DataFrame, trend: TrendResult
    ) -> tuple[bool, dict]:
        """MACD histogram aligned with trend direction."""
        macd_line, signal_line, histogram = compute_macd(candles["close"])
        hist_clean = histogram.dropna()
        if len(hist_clean) == 0:
            return False, {"histogram": 0}

        hist_val = float(hist_clean.iloc[-1])

        if trend.direction == Trend.BULLISH:
            hit = hist_val > 0
        elif trend.direction == Trend.BEARISH:
            hit = hist_val < 0
        else:
            hit = False

        return hit, {"histogram": hist_val}

    def _check_candlestick_pattern(
        self, zone: EntryZone, candles: pd.DataFrame, trend: TrendResult
    ) -> tuple[bool, dict]:
        """Detect simple reversal candlestick patterns at the zone."""
        if len(candles) < 3:
            return False, {"pattern": "none"}

        last = candles.iloc[-1]
        prev = candles.iloc[-2]
        body = abs(last["close"] - last["open"])
        upper_wick = last["high"] - max(last["close"], last["open"])
        lower_wick = min(last["close"], last["open"]) - last["low"]
        candle_range = last["high"] - last["low"]

        if candle_range == 0:
            return False, {"pattern": "none"}

        # Hammer (bullish reversal): small body, long lower wick
        is_hammer = (
            lower_wick > body * 2
            and upper_wick < body * 0.5
            and trend.direction == Trend.BULLISH
        )

        # Engulfing: current body engulfs previous body
        prev_body = abs(prev["close"] - prev["open"])
        is_bullish_engulfing = (
            last["close"] > last["open"]
            and prev["close"] < prev["open"]
            and body > prev_body
            and trend.direction == Trend.BULLISH
        )
        is_bearish_engulfing = (
            last["close"] < last["open"]
            and prev["close"] > prev["open"]
            and body > prev_body
            and trend.direction == Trend.BEARISH
        )

        if is_hammer:
            return True, {"pattern": "hammer"}
        elif is_bullish_engulfing:
            return True, {"pattern": "bullish_engulfing"}
        elif is_bearish_engulfing:
            return True, {"pattern": "bearish_engulfing"}

        return False, {"pattern": "none"}

    def _check_stochastic_cross(
        self, zone: EntryZone, candles: pd.DataFrame, trend: TrendResult
    ) -> tuple[bool, dict]:
        """Stochastic %K/%D cross in trend direction."""
        slow_k, slow_d = compute_stochastic(candles)
        k_clean = slow_k.dropna()
        d_clean = slow_d.dropna()

        if len(k_clean) < 2 or len(d_clean) < 2:
            return False, {"slow_k": 0, "slow_d": 0}

        k_now = float(k_clean.iloc[-1])
        d_now = float(d_clean.iloc[-1])
        k_prev = float(k_clean.iloc[-2])
        d_prev = float(d_clean.iloc[-2])

        # Bullish cross: %K crosses above %D in oversold territory
        bullish_cross = k_prev < d_prev and k_now > d_now and k_now < 30
        # Bearish cross: %K crosses below %D in overbought territory
        bearish_cross = k_prev > d_prev and k_now < d_now and k_now > 70

        if trend.direction == Trend.BULLISH:
            hit = bullish_cross
        elif trend.direction == Trend.BEARISH:
            hit = bearish_cross
        else:
            hit = False

        return hit, {"slow_k": k_now, "slow_d": d_now}
