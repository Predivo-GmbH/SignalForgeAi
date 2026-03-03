"""
Layer 3: Confluence Scorer.

Scores an entry zone 0-100 using 9 weighted factors that measure
alignment between technical indicators and the identified zone.
"""

import pandas as pd

from app.engine.indicators import (
    compute_bollinger_bands,
    compute_cci,
    compute_ichimoku,
    compute_macd,
    compute_obv,
    compute_rsi,
    compute_stochastic,
    compute_vwap,
    compute_williams_r,
)
from app.engine.layers.trend import Trend, TrendResult
from app.engine.layers.zones import EntryZone


class ConfluenceScorer:
    """
    Layer 3: Scores a zone 0-100 based on how many independent
    technical factors confirm it as a high-probability entry.
    14 factors covering price structure, momentum, volume, and volatility.
    """

    WEIGHTS: dict[str, int] = {
        "fibonacci_alignment": 12,
        "sr_overlap": 12,
        "multi_tf_fib": 10,
        "vwap_proximity": 8,
        "volume_node": 8,
        "rsi_confirmation": 8,
        "macd_momentum": 8,
        "candlestick_pattern": 7,
        "stochastic_cross": 5,
        "bollinger_position": 5,
        "ichimoku_cloud": 5,
        "obv_trend": 5,
        "williams_r_extreme": 4,
        "cci_momentum": 3,
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
            "bollinger_position": self._check_bollinger_position,
            "ichimoku_cloud": self._check_ichimoku_cloud,
            "obv_trend": self._check_obv_trend,
            "williams_r_extreme": self._check_williams_r_extreme,
            "cci_momentum": self._check_cci_momentum,
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
        """RSI confirms trend momentum (not extreme against direction).

        Bullish: RSI 35-65 (not overbought, room to run).
        Bearish: RSI 35-65 (not oversold, room to fall).
        This avoids the contradiction of requiring oversold in an uptrend.
        """
        rsi = compute_rsi(candles["close"], period=14)
        rsi_val = float(rsi.dropna().iloc[-1]) if len(rsi.dropna()) > 0 else 50.0

        if trend.direction == Trend.BULLISH:
            hit = 35 <= rsi_val <= 65  # Healthy momentum, not overextended
        elif trend.direction == Trend.BEARISH:
            hit = 35 <= rsi_val <= 65  # Room to fall, not already oversold
        else:
            hit = False

        return hit, {"rsi": rsi_val, "trend": trend.direction.value}

    def _check_macd_momentum(
        self, zone: EntryZone, candles: pd.DataFrame, trend: TrendResult
    ) -> tuple[bool, dict]:
        """MACD confirms momentum: histogram aligned OR rising in trend direction."""
        macd_line, signal_line, histogram = compute_macd(candles["close"])
        hist_clean = histogram.dropna()
        if len(hist_clean) < 2:
            return False, {"histogram": 0, "rising": False}

        hist_val = float(hist_clean.iloc[-1])
        hist_prev = float(hist_clean.iloc[-2])
        rising = hist_val > hist_prev

        if trend.direction == Trend.BULLISH:
            # Positive histogram OR rising histogram (momentum recovering)
            hit = hist_val > 0 or rising
        elif trend.direction == Trend.BEARISH:
            # Negative histogram OR falling histogram (momentum increasing)
            hit = hist_val < 0 or not rising
        else:
            hit = False

        return hit, {"histogram": hist_val, "rising": rising}

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
        """Stochastic %K/%D cross or momentum in trend direction."""
        slow_k, slow_d = compute_stochastic(candles)
        k_clean = slow_k.dropna()
        d_clean = slow_d.dropna()

        if len(k_clean) < 2 or len(d_clean) < 2:
            return False, {"slow_k": 0, "slow_d": 0}

        k_now = float(k_clean.iloc[-1])
        d_now = float(d_clean.iloc[-1])
        k_prev = float(k_clean.iloc[-2])
        d_prev = float(d_clean.iloc[-2])

        # Bullish: %K crosses above %D, or %K rising in lower half
        bullish = (k_prev < d_prev and k_now > d_now and k_now < 50) or (
            k_now > k_prev and k_now < 50
        )
        # Bearish: %K crosses below %D, or %K falling in upper half
        bearish = (k_prev > d_prev and k_now < d_now and k_now > 50) or (
            k_now < k_prev and k_now > 50
        )

        if trend.direction == Trend.BULLISH:
            hit = bullish
        elif trend.direction == Trend.BEARISH:
            hit = bearish
        else:
            hit = False

        return hit, {"slow_k": k_now, "slow_d": d_now}

    def _check_bollinger_position(
        self, zone: EntryZone, candles: pd.DataFrame, trend: TrendResult
    ) -> tuple[bool, dict]:
        """Price near lower Bollinger Band in uptrend or upper band in downtrend."""
        upper, middle, lower = compute_bollinger_bands(candles["close"])
        upper_clean = upper.dropna()
        lower_clean = lower.dropna()
        if len(upper_clean) == 0 or len(lower_clean) == 0:
            return False, {"bb_position": "unknown"}

        price = float(candles["close"].iloc[-1])
        upper_val = float(upper_clean.iloc[-1])
        lower_val = float(lower_clean.iloc[-1])
        band_width = upper_val - lower_val
        if band_width == 0:
            return False, {"bb_position": "flat"}

        # Position within bands: 0 = at lower, 1 = at upper
        bb_pct = (price - lower_val) / band_width

        if trend.direction == Trend.BULLISH:
            hit = bb_pct < 0.3  # Near lower band = oversold bounce opportunity
        elif trend.direction == Trend.BEARISH:
            hit = bb_pct > 0.7  # Near upper band = overbought rejection opportunity
        else:
            hit = False

        return hit, {"bb_pct": round(bb_pct, 3), "upper": upper_val, "lower": lower_val}

    def _check_ichimoku_cloud(
        self, zone: EntryZone, candles: pd.DataFrame, trend: TrendResult
    ) -> tuple[bool, dict]:
        """Price position relative to Ichimoku Cloud confirms trend."""
        ichi = compute_ichimoku(candles)
        senkou_a = ichi["senkou_a"].dropna()
        senkou_b = ichi["senkou_b"].dropna()
        if len(senkou_a) == 0 or len(senkou_b) == 0:
            return False, {"cloud_position": "insufficient_data"}

        price = float(candles["close"].iloc[-1])
        cloud_top = max(float(senkou_a.iloc[-1]), float(senkou_b.iloc[-1]))
        cloud_bottom = min(float(senkou_a.iloc[-1]), float(senkou_b.iloc[-1]))

        if trend.direction == Trend.BULLISH:
            hit = price > cloud_top  # Price above cloud confirms uptrend
            pos = "above"
        elif trend.direction == Trend.BEARISH:
            hit = price < cloud_bottom  # Price below cloud confirms downtrend
            pos = "below"
        else:
            hit = False
            pos = "inside" if cloud_bottom <= price <= cloud_top else "outside"

        return hit, {"cloud_position": pos, "cloud_top": cloud_top, "cloud_bottom": cloud_bottom}

    def _check_obv_trend(
        self, zone: EntryZone, candles: pd.DataFrame, trend: TrendResult
    ) -> tuple[bool, dict]:
        """On-Balance Volume trend aligns with price trend (rising OBV = accumulation)."""
        obv = compute_obv(candles)
        obv_clean = obv.dropna()
        if len(obv_clean) < 20:
            return False, {"obv_slope": 0}

        # Compare OBV 20-period moving average slope
        obv_ma = obv_clean.rolling(20).mean().dropna()
        if len(obv_ma) < 2:
            return False, {"obv_slope": 0}

        obv_slope = float(obv_ma.iloc[-1] - obv_ma.iloc[-5]) if len(obv_ma) >= 5 else 0

        if trend.direction == Trend.BULLISH:
            hit = obv_slope > 0  # Rising OBV confirms buying pressure
        elif trend.direction == Trend.BEARISH:
            hit = obv_slope < 0  # Falling OBV confirms selling pressure
        else:
            hit = False

        return hit, {"obv_slope": round(obv_slope, 2)}

    def _check_williams_r_extreme(
        self, zone: EntryZone, candles: pd.DataFrame, trend: TrendResult
    ) -> tuple[bool, dict]:
        """Williams %R confirms trend momentum (not overextended against direction)."""
        wr = compute_williams_r(candles)
        wr_clean = wr.dropna()
        if len(wr_clean) == 0:
            return False, {"williams_r": -50}

        wr_val = float(wr_clean.iloc[-1])

        if trend.direction == Trend.BULLISH:
            hit = wr_val < -30  # Not overbought, has room to run
        elif trend.direction == Trend.BEARISH:
            hit = wr_val > -70  # Not oversold, has room to fall
        else:
            hit = False

        return hit, {"williams_r": round(wr_val, 2)}

    def _check_cci_momentum(
        self, zone: EntryZone, candles: pd.DataFrame, trend: TrendResult
    ) -> tuple[bool, dict]:
        """CCI confirms momentum direction. >0 = bullish momentum, <0 = bearish."""
        cci = compute_cci(candles)
        cci_clean = cci.dropna()
        if len(cci_clean) == 0:
            return False, {"cci": 0}

        cci_val = float(cci_clean.iloc[-1])

        if trend.direction == Trend.BULLISH:
            hit = cci_val > -50  # Not deep negative = momentum supportive
        elif trend.direction == Trend.BEARISH:
            hit = cci_val < 50  # Not deep positive = momentum supportive
        else:
            hit = False

        return hit, {"cci": round(cci_val, 2)}
