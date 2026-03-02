"""Technical analyzer — scores cryptos using all pipeline indicators."""

import logging

import numpy as np
import pandas as pd

from app.engine.indicators import (
    compute_adx,
    compute_atr,
    compute_bollinger_bands,
    compute_cci,
    compute_ichimoku,
    compute_macd,
    compute_obv,
    compute_rsi,
    compute_williams_r,
)
from app.engine.layers.regime import Regime, RegimeDetector
from app.engine.layers.trend import Trend, TrendFilter

logger = logging.getLogger(__name__)


class TechnicalAnalyzer:
    """Scores cryptos using all available technical indicators.

    Score breakdown (0-100):
      - Regime: TRENDING=15, RANGING=5, TRANSITIONING=3, CHAOTIC=0
      - Trend: BULLISH/BEARISH=15, UNDETERMINED=0
      - RSI: oversold/overbought with trend=10, neutral zone=6
      - MACD: histogram aligned with trend=10
      - ADX strength: >40=10, >30=7, >20=3
      - Volume rank: top 10=8, top 20=4
      - Bollinger Bands: price near band in trend direction=8
      - Ichimoku Cloud: price above/below cloud=8
      - OBV: volume trend confirms price trend=6
      - Williams %R: extreme levels confirming trend=5
      - CCI: momentum confirmation=5
    """

    def __init__(self):
        self.regime_detector = RegimeDetector()
        self.trend_filter = TrendFilter()

    def score_crypto(self, symbol: str, candles: pd.DataFrame, volume_rank: int = 0) -> dict:
        """Run all indicators on a single crypto and return a comprehensive score."""
        try:
            price = float(candles["close"].iloc[-1])

            # Regime detection (with HMM if available)
            regime = self.regime_detector.detect(candles)
            regime_score = {
                Regime.TRENDING: 15, Regime.TRENDING_BULL: 15, Regime.TRENDING_BEAR: 15,
                Regime.RANGING: 5, Regime.TRANSITIONING: 3, Regime.CHAOTIC: 0,
            }.get(regime, 3)

            # Trend filter
            trend = self.trend_filter.evaluate(candles)
            trend_score = 15 if trend.direction in (Trend.BULLISH, Trend.BEARISH) else 0

            # RSI
            rsi = compute_rsi(candles["close"])
            rsi_val = float(rsi.dropna().iloc[-1]) if len(rsi.dropna()) > 0 else 50
            if trend.direction == Trend.BULLISH and rsi_val < 40:
                rsi_score = 10
            elif trend.direction == Trend.BEARISH and rsi_val > 60:
                rsi_score = 10
            elif 30 <= rsi_val <= 70:
                rsi_score = 6
            else:
                rsi_score = 2

            # MACD momentum
            _, _, macd_hist = compute_macd(candles["close"])
            hist_val = float(macd_hist.dropna().iloc[-1]) if len(macd_hist.dropna()) > 0 else 0
            if (trend.direction == Trend.BULLISH and hist_val > 0) or \
               (trend.direction == Trend.BEARISH and hist_val < 0):
                macd_score = 10
            elif hist_val != 0:
                macd_score = 3
            else:
                macd_score = 0

            # ADX strength
            adx = compute_adx(candles)
            adx_val = float(adx.dropna().iloc[-1]) if len(adx.dropna()) > 0 else 0
            if adx_val > 40:
                adx_score = 10
            elif adx_val > 30:
                adx_score = 7
            elif adx_val > 20:
                adx_score = 3
            else:
                adx_score = 0

            # Volume rank bonus
            if volume_rank <= 10:
                vol_score = 8
            elif volume_rank <= 20:
                vol_score = 4
            else:
                vol_score = 0

            # Bollinger Bands
            bb_score = 0
            bb_pct = 0.5
            try:
                upper, middle, lower = compute_bollinger_bands(candles["close"])
                upper_clean = upper.dropna()
                lower_clean = lower.dropna()
                if len(upper_clean) > 0 and len(lower_clean) > 0:
                    bb_upper = float(upper_clean.iloc[-1])
                    bb_lower = float(lower_clean.iloc[-1])
                    bw = bb_upper - bb_lower
                    if bw > 0:
                        bb_pct = (price - bb_lower) / bw
                        if trend.direction == Trend.BULLISH and bb_pct < 0.3:
                            bb_score = 8  # Near lower band in uptrend
                        elif trend.direction == Trend.BEARISH and bb_pct > 0.7:
                            bb_score = 8  # Near upper band in downtrend
                        elif 0.2 < bb_pct < 0.8:
                            bb_score = 3  # Within bands
            except Exception:
                pass

            # Ichimoku Cloud
            ichi_score = 0
            cloud_pos = "unknown"
            try:
                ichi = compute_ichimoku(candles)
                sa = ichi["senkou_a"].dropna()
                sb = ichi["senkou_b"].dropna()
                if len(sa) > 0 and len(sb) > 0:
                    cloud_top = max(float(sa.iloc[-1]), float(sb.iloc[-1]))
                    cloud_bottom = min(float(sa.iloc[-1]), float(sb.iloc[-1]))
                    if trend.direction == Trend.BULLISH and price > cloud_top:
                        ichi_score = 8
                        cloud_pos = "above"
                    elif trend.direction == Trend.BEARISH and price < cloud_bottom:
                        ichi_score = 8
                        cloud_pos = "below"
                    elif cloud_bottom <= price <= cloud_top:
                        cloud_pos = "inside"
                    else:
                        cloud_pos = "outside"
                        ichi_score = 2
            except Exception:
                pass

            # OBV trend
            obv_score = 0
            obv_slope = 0.0
            try:
                obv = compute_obv(candles)
                obv_clean = obv.dropna()
                if len(obv_clean) >= 20:
                    obv_ma = obv_clean.rolling(20).mean().dropna()
                    if len(obv_ma) >= 5:
                        obv_slope = float(obv_ma.iloc[-1] - obv_ma.iloc[-5])
                        if (trend.direction == Trend.BULLISH and obv_slope > 0) or \
                           (trend.direction == Trend.BEARISH and obv_slope < 0):
                            obv_score = 6
            except Exception:
                pass

            # Williams %R
            wr_score = 0
            wr_val = -50.0
            try:
                wr = compute_williams_r(candles)
                wr_clean = wr.dropna()
                if len(wr_clean) > 0:
                    wr_val = float(wr_clean.iloc[-1])
                    if trend.direction == Trend.BULLISH and wr_val < -80:
                        wr_score = 5  # Oversold
                    elif trend.direction == Trend.BEARISH and wr_val > -20:
                        wr_score = 5  # Overbought
            except Exception:
                pass

            # CCI
            cci_score = 0
            cci_val = 0.0
            try:
                cci = compute_cci(candles)
                cci_clean = cci.dropna()
                if len(cci_clean) > 0:
                    cci_val = float(cci_clean.iloc[-1])
                    if (trend.direction == Trend.BULLISH and cci_val > 100) or \
                       (trend.direction == Trend.BEARISH and cci_val < -100):
                        cci_score = 5
            except Exception:
                pass

            # ATR (informational)
            atr = compute_atr(candles)
            atr_val = float(atr.dropna().iloc[-1]) if len(atr.dropna()) > 0 else 0
            atr_pct = (atr_val / price * 100) if price > 0 else 0

            total_score = min(100, (
                regime_score + trend_score + rsi_score + macd_score +
                adx_score + vol_score + bb_score + ichi_score +
                obv_score + wr_score + cci_score
            ))

            # Recommendation
            if total_score >= 70:
                recommendation = "strong_buy"
            elif total_score >= 50:
                recommendation = "buy"
            elif total_score >= 30:
                recommendation = "neutral"
            else:
                recommendation = "avoid"

            return {
                "symbol": symbol,
                "score": total_score,
                "regime": regime.value,
                "trend_direction": trend.direction.value,
                "trend_strength": round(trend.strength, 4),
                "rsi": round(rsi_val, 2),
                "adx": round(adx_val, 2),
                "atr_pct": round(atr_pct, 2),
                "macd_histogram": round(hist_val, 6),
                "bollinger_pct": round(bb_pct, 3),
                "ichimoku_cloud": cloud_pos,
                "obv_slope": round(obv_slope, 2),
                "williams_r": round(wr_val, 2),
                "cci": round(cci_val, 2),
                "volume_rank": volume_rank,
                "price": round(price, 8),
                "recommendation": recommendation,
            }

        except Exception as e:
            logger.error("Failed to score %s: %s", symbol, e)
            return {
                "symbol": symbol,
                "score": 0,
                "regime": "unknown",
                "trend_direction": "undetermined",
                "trend_strength": 0,
                "rsi": 50,
                "adx": 0,
                "atr_pct": 0,
                "macd_histogram": 0,
                "bollinger_pct": 0.5,
                "ichimoku_cloud": "unknown",
                "obv_slope": 0,
                "williams_r": -50,
                "cci": 0,
                "volume_rank": volume_rank,
                "price": 0,
                "recommendation": "avoid",
            }

    def analyze_market(self, candles_by_symbol: dict[str, pd.DataFrame],
                       volume_ranks: dict[str, int] | None = None) -> list[dict]:
        """Score all cryptos, sort by score descending."""
        ranks = volume_ranks or {}
        results = []
        for symbol, df in candles_by_symbol.items():
            if len(df) < 50:
                logger.warning("Skipping %s: only %d candles", symbol, len(df))
                continue
            score = self.score_crypto(symbol, df, volume_rank=ranks.get(symbol, 99))
            results.append(score)

        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    def compute_market_profile(self, scored: list[dict]) -> dict:
        """Aggregate scored results into a market profile for the AI advisor.

        Returns raw metrics — the AI advisor uses these to determine
        optimal strategy parameters autonomously.
        """
        if not scored:
            return {
                "trending_pct": 0, "bullish_pct": 0, "chaotic_pct": 0,
                "avg_score": 0, "avg_adx": 0, "avg_volatility": 0,
                "avg_rsi": 50, "total_scanned": 0,
            }

        total = len(scored)
        trending_count = sum(
            1 for s in scored
            if s.get("regime", "").startswith("trending")
        )
        bullish_count = sum(1 for s in scored if s.get("trend_direction") == "bullish")
        chaotic_count = sum(1 for s in scored if s.get("regime") == "chaotic")

        return {
            "trending_pct": round(trending_count / total * 100, 1),
            "bullish_pct": round(bullish_count / total * 100, 1),
            "chaotic_pct": round(chaotic_count / total * 100, 1),
            "avg_score": round(float(np.mean([s.get("score", 0) for s in scored])), 1),
            "avg_adx": round(float(np.mean([s.get("adx", 0) for s in scored])), 1),
            "avg_volatility": round(float(np.mean([s.get("atr_pct", 0) for s in scored])), 2),
            "avg_rsi": round(float(np.mean([s.get("rsi", 50) for s in scored])), 1),
            "total_scanned": total,
        }
