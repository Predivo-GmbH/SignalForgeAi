"""Technical analyzer — scores cryptos using pipeline layers."""

import logging

import pandas as pd

from app.engine.indicators import compute_adx, compute_atr, compute_ema, compute_macd, compute_rsi
from app.engine.layers.regime import Regime, RegimeDetector
from app.engine.layers.trend import Trend, TrendFilter

logger = logging.getLogger(__name__)


class TechnicalAnalyzer:
    """Scores cryptos using the existing signal pipeline layers."""

    def __init__(self):
        self.regime_detector = RegimeDetector()
        self.trend_filter = TrendFilter()

    def score_crypto(self, symbol: str, candles: pd.DataFrame, volume_rank: int = 0) -> dict:
        """Run pipeline layers on a single crypto and return a technical score.

        Score breakdown (0-100):
          - Regime: TRENDING=25, RANGING=10, TRANSITIONING=5, CHAOTIC=0
          - Trend: BULLISH/BEARISH=25, UNDETERMINED=0
          - RSI: 30-70 range=10, oversold/overbought with trend=15
          - MACD: positive histogram in trend direction=15
          - Volume rank bonus: top 10=10, top 20=5
          - ADX strength: >30=10, >40=15
        """
        try:
            # Regime detection
            regime = self.regime_detector.detect(candles)
            regime_score = {
                Regime.TRENDING: 25,
                Regime.TRENDING_BULL: 25,
                Regime.TRENDING_BEAR: 25,
                Regime.RANGING: 10,
                Regime.TRANSITIONING: 5,
                Regime.CHAOTIC: 0,
            }.get(regime, 5)

            # Trend filter
            trend = self.trend_filter.evaluate(candles)
            trend_score = 25 if trend.direction in (Trend.BULLISH, Trend.BEARISH) else 0

            # RSI
            rsi = compute_rsi(candles["close"])
            rsi_val = float(rsi.dropna().iloc[-1]) if len(rsi.dropna()) > 0 else 50
            if trend.direction == Trend.BULLISH and rsi_val < 40:
                rsi_score = 15  # Oversold in uptrend = opportunity
            elif trend.direction == Trend.BEARISH and rsi_val > 60:
                rsi_score = 15  # Overbought in downtrend = opportunity
            elif 30 <= rsi_val <= 70:
                rsi_score = 10  # Neutral zone
            else:
                rsi_score = 5

            # MACD momentum
            macd_line, macd_signal, macd_hist = compute_macd(candles["close"])
            hist_val = float(macd_hist.dropna().iloc[-1]) if len(macd_hist.dropna()) > 0 else 0
            if (trend.direction == Trend.BULLISH and hist_val > 0) or \
               (trend.direction == Trend.BEARISH and hist_val < 0):
                macd_score = 15
            elif hist_val != 0:
                macd_score = 5
            else:
                macd_score = 0

            # ADX strength
            adx = compute_adx(candles)
            adx_val = float(adx.dropna().iloc[-1]) if len(adx.dropna()) > 0 else 0
            if adx_val > 40:
                adx_score = 15
            elif adx_val > 30:
                adx_score = 10
            elif adx_val > 20:
                adx_score = 5
            else:
                adx_score = 0

            # Volume rank bonus
            if volume_rank <= 10:
                vol_score = 10
            elif volume_rank <= 20:
                vol_score = 5
            else:
                vol_score = 0

            # ATR (for info, not scoring)
            atr = compute_atr(candles)
            atr_val = float(atr.dropna().iloc[-1]) if len(atr.dropna()) > 0 else 0
            price = float(candles["close"].iloc[-1])
            atr_pct = (atr_val / price * 100) if price > 0 else 0

            total_score = min(100, regime_score + trend_score + rsi_score + macd_score + adx_score + vol_score)

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
