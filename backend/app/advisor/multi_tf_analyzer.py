"""Multi-Timeframe Analyzer — synthesizes signals across timeframes."""

import logging

import pandas as pd

from app.advisor.claude_client import ModelTier, claude_client
from app.config import settings
from app.engine.layers.regime import RegimeDetector
from app.engine.layers.trend import TrendFilter

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a multi-timeframe analysis expert for crypto trading. "
    "You receive technical analysis data from multiple timeframes "
    "for the same symbol and must synthesize them into a unified "
    "confidence assessment.\n\n"
    "Key principles:\n"
    "- Higher timeframes carry more weight (daily > 4h > 1h)\n"
    "- A 1h buy signal AGAINST the daily trend is high-risk\n"
    "- Confluence across all timeframes = highest confidence\n"
    "- Divergence between timeframes = caution / reduced size\n"
    "- If only 1h data is available, base assessment on that\n\n"
    "Return ONLY valid JSON with this structure:\n"
    '{\n'
    '  "mtf_confidence": 0-100,\n'
    '  "timeframe_alignment": "aligned|mixed|conflicting",\n'
    '  "reasoning": "2-3 sentence synthesis across timeframes",\n'
    '  "recommendation": "confirm|caution|reject"\n'
    '}\n\n'
    "Guidelines:\n"
    "- aligned: All available timeframes agree on direction\n"
    "- mixed: Some agree, some neutral/undetermined\n"
    "- conflicting: Timeframes disagree on direction\n\n"
    "Respond ONLY with valid JSON."
)

# Higher timeframes to check (in addition to the primary signal timeframe)
HIGHER_TIMEFRAMES = ["4h", "1d"]


def _summarize_timeframe(
    timeframe: str, candles: pd.DataFrame,
) -> dict:
    """Run algorithmic analysis on a single timeframe and return summary."""
    regime_detector = RegimeDetector()
    trend_filter = TrendFilter()

    regime = regime_detector.detect(candles)
    trend = trend_filter.evaluate(candles)

    close = candles["close"]
    last_price = float(close.iloc[-1])

    return {
        "timeframe": timeframe,
        "regime": regime.value,
        "trend_direction": trend.direction.value,
        "trend_strength": round(trend.strength, 4),
        "last_price": last_price,
        "candle_count": len(candles),
    }


class MultiTimeframeAnalyzer:
    """Synthesizes signals across multiple timeframes using Claude."""

    async def analyze(
        self,
        symbol: str,
        primary_signal_data: dict,
        db_session,
    ) -> dict:
        """Synthesize multi-timeframe data for a signal.

        Fetches higher timeframe candles from DB, runs algorithmic analysis,
        and sends to Claude for synthesis.
        """
        if not settings.ai_multi_timeframe_enabled:
            return self._passthrough_fallback(primary_signal_data)

        # Gather timeframe data
        tf_summaries = [
            {
                "timeframe": primary_signal_data["timeframe"],
                "regime": primary_signal_data["regime"],
                "trend_direction": primary_signal_data["trend_direction"],
                "trend_strength": primary_signal_data["trend_strength"],
                "source": "primary_signal",
            }
        ]

        from app.data.storage import CandleStorage

        for tf in HIGHER_TIMEFRAMES:
            if tf == primary_signal_data["timeframe"]:
                continue
            try:
                candles_data = await CandleStorage.load_candles_db(
                    db_session, symbol, tf, limit=200,
                )
                if len(candles_data) < 50:
                    continue
                df = pd.DataFrame(candles_data)
                summary = _summarize_timeframe(tf, df)
                tf_summaries.append(summary)
            except Exception:
                logger.debug("No %s candles for %s in MTF analysis", tf, symbol)

        # If we only have the primary timeframe, use algorithmic fallback
        if len(tf_summaries) <= 1:
            return self._algorithmic_fallback(tf_summaries)

        # Build prompt and call Claude
        user_message = self._build_user_message(symbol, tf_summaries)
        result = await claude_client.ask_json(
            ModelTier.FAST,
            SYSTEM_PROMPT,
            user_message,
            cache_ttl=settings.ai_signal_quality_cache_ttl,
            insight_type="multi_tf_analysis",
        )

        if result is not None:
            return self._validate_result(result)

        return self._algorithmic_fallback(tf_summaries)

    @staticmethod
    def _build_user_message(symbol: str, tf_summaries: list[dict]) -> str:
        lines = [f"Symbol: {symbol}", "", "Timeframe analysis:"]
        for s in tf_summaries:
            lines.append(
                f"  {s['timeframe']}: regime={s.get('regime', 'N/A')}, "
                f"trend={s.get('trend_direction', 'N/A')}, "
                f"strength={s.get('trend_strength', 'N/A')}"
            )
        return "\n".join(lines)

    @staticmethod
    def _validate_result(result: dict) -> dict:
        confidence = max(0, min(100, int(result.get("mtf_confidence", 50))))
        alignment = result.get("timeframe_alignment", "mixed")
        if alignment not in ("aligned", "mixed", "conflicting"):
            alignment = "mixed"
        recommendation = result.get("recommendation", "confirm")
        if recommendation not in ("confirm", "caution", "reject"):
            recommendation = "confirm"
        return {
            "mtf_confidence": confidence,
            "timeframe_alignment": alignment,
            "reasoning": result.get("reasoning", ""),
            "recommendation": recommendation,
        }

    @staticmethod
    def _algorithmic_fallback(tf_summaries: list[dict]) -> dict:
        """Simple alignment check without Claude."""
        directions = [
            s["trend_direction"] for s in tf_summaries
            if s.get("trend_direction") not in (None, "undetermined")
        ]

        if not directions:
            return {
                "mtf_confidence": 50,
                "timeframe_alignment": "mixed",
                "reasoning": "Insufficient timeframe data for alignment check.",
                "recommendation": "confirm",
            }

        # Check if all non-undetermined directions agree
        unique = set(directions)
        if len(unique) == 1:
            return {
                "mtf_confidence": 85,
                "timeframe_alignment": "aligned",
                "reasoning": f"All {len(directions)} timeframes show {directions[0]} trend.",
                "recommendation": "confirm",
            }
        elif "bullish" in unique and "bearish" in unique:
            return {
                "mtf_confidence": 30,
                "timeframe_alignment": "conflicting",
                "reasoning": "Timeframes show conflicting trend directions.",
                "recommendation": "caution",
            }
        else:
            return {
                "mtf_confidence": 60,
                "timeframe_alignment": "mixed",
                "reasoning": "Timeframes show mixed alignment.",
                "recommendation": "confirm",
            }

    @staticmethod
    def _passthrough_fallback(signal_data: dict) -> dict:
        """Return neutral MTF data when feature is disabled."""
        return {
            "mtf_confidence": 50,
            "timeframe_alignment": "mixed",
            "reasoning": "Multi-timeframe analysis disabled.",
            "recommendation": "confirm",
        }
