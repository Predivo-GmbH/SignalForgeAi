"""Signal Quality Evaluator — Claude-powered second opinion on pipeline signals.

When Claude is unavailable, signals are REJECTED — the system does not
trade without AI quality analysis.
"""

import logging

from app.advisor.claude_client import ModelTier, claude_client
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a senior quantitative trader reviewing automated "
    "signals from a crypto trading system called SignalForge. "
    "Your role is to evaluate whether the combination of technical "
    "factors represents a genuine opportunity or a potential trap.\n\n"
    "You receive the signal details including all 14 confluence "
    "factors, their values, and the market context. Assess the "
    "QUALITY of the signal by looking for:\n"
    "1. Trap patterns (RSI oversold in strong downtrend = trap)\n"
    "2. Conflicting signals (bullish trigger + declining volume)\n"
    "3. Context binary scoring misses (extreme ATR = wide stops)\n"
    "4. Multi-factor interactions simple scoring cannot capture\n"
    "5. Multi-timeframe alignment (if provided)\n\n"
    "Return ONLY valid JSON with this structure:\n"
    '{\n'
    '  "quality_score": 0-100,\n'
    '  "recommendation": "strong_confirm|confirm|caution|reject",\n'
    '  "reasoning": "2-4 sentence analysis of signal quality",\n'
    '  "risk_adjustments": {\n'
    '    "position_size_factor": 0.0-1.5,\n'
    '    "reasoning": "Why position size should be adjusted"\n'
    '  }\n'
    '}\n\n'
    "Guidelines for recommendation:\n"
    "- strong_confirm (>= 80): All factors align, high conviction\n"
    "- confirm (60-79): Good setup with minor concerns\n"
    "- caution (40-59): Proceed with reduced size\n"
    "- reject (< 40): Signal is likely a trap or has flaws\n\n"
    "Respond ONLY with valid JSON."
)


def build_quality_user_message(
    signal_data: dict,
    confluence_details: dict,
    candle_summary: list[dict],
    mtf_data: dict | None = None,
) -> str:
    """Build the user message for signal quality evaluation."""
    lines = [
        f"Signal: {signal_data['action']} {signal_data['symbol']} ({signal_data['timeframe']})",
        f"Regime: {signal_data['regime']}",
        f"Trend: {signal_data['trend_direction']} (strength: {signal_data['trend_strength']:.4f})",
        f"Algorithmic confluence score: {signal_data['confluence_score']}/100",
        f"Triggers fired: {', '.join(signal_data['triggers'])}",
        f"Risk/Reward: {signal_data.get('risk_reward', 'N/A')}",
        "",
        "Confluence factor details (14 factors):",
    ]

    for factor, info in confluence_details.items():
        hit = info.get("hit", False)
        weight = info.get("weight", 0)
        earned = info.get("earned", 0)
        extra = {k: v for k, v in info.items() if k not in ("hit", "weight", "earned")}
        lines.append(
            f"  {factor}: {'HIT' if hit else 'MISS'} ({earned}/{weight}) {extra}"
        )

    lines.append("")
    lines.append("Last 5 candles (newest first):")
    for candle in candle_summary[:5]:
        lines.append(
            f"  O={candle['open']:.2f} H={candle['high']:.2f} "
            f"L={candle['low']:.2f} C={candle['close']:.2f} V={candle['volume']:.0f}"
        )

    if mtf_data:
        lines.append("")
        lines.append("Multi-timeframe analysis:")
        lines.append(f"  MTF confidence: {mtf_data.get('mtf_confidence', 'N/A')}/100")
        lines.append(f"  Alignment: {mtf_data.get('timeframe_alignment', 'N/A')}")
        if mtf_data.get("reasoning"):
            lines.append(f"  MTF reasoning: {mtf_data['reasoning']}")

    return "\n".join(lines)


class SignalQualityEvaluator:
    """Evaluates signal quality using Claude as a second opinion."""

    async def evaluate(
        self,
        signal_data: dict,
        confluence_details: dict,
        candle_summary: list[dict],
        mtf_data: dict | None = None,
    ) -> dict:
        """Evaluate signal quality.

        Returns dict with quality_score, recommendation, reasoning,
        and optional risk_adjustments.

        When Claude is unavailable, signals are REJECTED — the system
        does not trade without AI quality analysis.
        """
        if not settings.ai_signal_quality_enabled:
            return self._feature_disabled_result(signal_data)

        user_message = build_quality_user_message(
            signal_data, confluence_details, candle_summary, mtf_data,
        )

        result = await claude_client.ask_json(
            ModelTier.FAST,
            SYSTEM_PROMPT,
            user_message,
            cache_ttl=settings.ai_signal_quality_cache_ttl,
            insight_type="signal_quality",
        )

        if result is not None:
            return self._validate_result(result, signal_data)

        logger.warning(
            "Claude unavailable — rejecting signal %s %s (no AI quality analysis)",
            signal_data.get("symbol"), signal_data.get("action"),
        )
        return self._ai_unavailable_reject(signal_data)

    def evaluate_sync(
        self,
        signal_data: dict,
        confluence_details: dict,
        candle_summary: list[dict],
        mtf_data: dict | None = None,
    ) -> dict:
        """Evaluate signal quality synchronously (for backtest engine).

        Returns dict with quality_score, recommendation, reasoning,
        and optional risk_adjustments.

        When Claude is unavailable, signals are REJECTED.
        """
        user_message = build_quality_user_message(
            signal_data, confluence_details, candle_summary, mtf_data,
        )

        result = claude_client.ask_json_sync(
            ModelTier.FAST,
            SYSTEM_PROMPT,
            user_message,
            cache_ttl=settings.ai_signal_quality_cache_ttl,
            insight_type="signal_quality_backtest",
        )

        if result is not None:
            return self._validate_result(result, signal_data)

        logger.warning(
            "Claude unavailable — rejecting signal %s %s in backtest (no AI quality analysis)",
            signal_data.get("symbol"), signal_data.get("action"),
        )
        return self._ai_unavailable_reject(signal_data)

    def _validate_result(self, result: dict, signal_data: dict) -> dict:
        """Ensure all required fields exist with valid values."""
        quality_score = result.get("quality_score", signal_data["confluence_score"])
        quality_score = max(0, min(100, int(quality_score)))

        recommendation = result.get("recommendation", "confirm")
        if recommendation not in ("strong_confirm", "confirm", "caution", "reject"):
            recommendation = "confirm"

        risk_adj = result.get("risk_adjustments", {})
        size_factor = risk_adj.get("position_size_factor", 1.0)
        size_factor = max(0.0, min(1.5, float(size_factor)))

        return {
            "quality_score": quality_score,
            "recommendation": recommendation,
            "reasoning": result.get("reasoning", ""),
            "risk_adjustments": {
                "position_size_factor": size_factor,
                "reasoning": risk_adj.get("reasoning", ""),
            },
        }

    @staticmethod
    def _feature_disabled_result(signal_data: dict) -> dict:
        """Return passthrough when the feature is deliberately disabled by config."""
        return {
            "quality_score": signal_data["confluence_score"],
            "recommendation": "confirm",
            "reasoning": "AI signal quality evaluation disabled by configuration.",
            "risk_adjustments": {
                "position_size_factor": 1.0,
                "reasoning": "No adjustment — feature disabled",
            },
        }

    @staticmethod
    def _ai_unavailable_reject(signal_data: dict) -> dict:
        """Reject signal when Claude is unavailable — no trading without AI analysis."""
        return {
            "quality_score": 0,
            "recommendation": "reject",
            "reasoning": (
                "Claude unavailable — signal rejected. "
                "The system does not trade without AI quality analysis."
            ),
            "risk_adjustments": {
                "position_size_factor": 0.0,
                "reasoning": "Trade blocked — AI unavailable",
            },
        }
