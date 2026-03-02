"""Deep Pattern Analyzer — Claude-powered trade history analysis.

When Claude is unavailable, no patterns are generated — the system does not
fabricate analysis without AI.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.advisor.claude_client import ModelTier, claude_client
from app.models.trade import Trade

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a trading performance analyst for an automated crypto "
    "trading platform called SignalForge. You receive a batch of "
    "completed trades with their details and must identify deep "
    "patterns, behavioral tendencies, and actionable insights.\n\n"
    "Go beyond surface-level statistics. Look for:\n"
    "1. Symbol-specific behavior (some pairs consistently trap)\n"
    "2. Regime correlation (which regimes produce best/worst)\n"
    "3. Confluence score correlation with actual outcomes\n"
    "4. Exit reason patterns (stop-loss vs target-hit distribution)\n"
    "5. Risk/Reward patterns (cutting winners short?)\n"
    "6. Position sizing tendencies (over/under-sizing)\n"
    "7. Streak patterns (loss clusters, recovery patterns)\n\n"
    "Return ONLY valid JSON with this structure:\n"
    '{\n'
    '  "summary": "2-3 sentence overview of trading performance",\n'
    '  "performance_metrics": {\n'
    '    "win_rate": 0.0-1.0,\n'
    '    "profit_factor": number,\n'
    '    "avg_win": number,\n'
    '    "avg_loss": number,\n'
    '    "best_symbol": "symbol",\n'
    '    "worst_symbol": "symbol"\n'
    '  },\n'
    '  "patterns": [\n'
    '    {\n'
    '      "pattern": "description of the pattern",\n'
    '      "evidence": "specific data supporting this pattern",\n'
    '      "severity": "high|medium|low",\n'
    '      "actionable": true/false\n'
    '    }\n'
    '  ],\n'
    '  "strengths": ["strength 1", "strength 2"],\n'
    '  "weaknesses": ["weakness 1", "weakness 2"],\n'
    '  "recommendations": [\n'
    '    {\n'
    '      "action": "specific recommendation",\n'
    '      "expected_impact": "what improvement this should bring",\n'
    '      "priority": "high|medium|low"\n'
    '    }\n'
    '  ]\n'
    '}\n\n'
    "Respond ONLY with valid JSON."
)


class PatternAnalyzer:
    """Deep analysis of trade history using Claude."""

    async def analyze_deep(self, user_id: str, db: AsyncSession, limit: int = 100) -> dict:
        """Run deep analysis on recent trade history."""
        result = await db.execute(
            select(Trade)
            .where(Trade.user_id == user_id, Trade.pnl.is_not(None))
            .order_by(Trade.exit_time.desc())
            .limit(limit)
        )
        trades = list(result.scalars().all())

        if not trades:
            return self._empty_result()

        user_message = self._build_user_message(trades)
        ai_result = await claude_client.ask_json(
            ModelTier.DEEP,
            SYSTEM_PROMPT,
            user_message,
            cache_ttl=3600,  # Cache for 1 hour
            insight_type="pattern_analysis",
        )

        if ai_result is not None:
            return self._validate_result(ai_result)

        logger.warning("Claude unavailable — skipping pattern analysis (no analysis without AI)")
        return self._empty_result()

    @staticmethod
    def _build_user_message(trades: list) -> str:
        lines = [f"Analyzing {len(trades)} recent closed trades:", ""]

        # Per-trade detail
        for i, t in enumerate(trades[:50], 1):  # Cap at 50 for token efficiency
            lines.append(
                f"{i}. {t.symbol} {t.direction} | "
                f"PnL: {t.pnl:+.2f} | R:R: {t.risk_reward or 'N/A'} | "
                f"Confluence: {t.confluence_score or 'N/A'} | "
                f"Exit: {t.exit_reason or 'N/A'} | "
                f"Regime: {getattr(t, 'regime', 'N/A')}"
            )

        # Summary stats
        total = len(trades)
        wins = [t for t in trades if t.pnl and t.pnl > 0]
        losses = [t for t in trades if t.pnl and t.pnl <= 0]

        lines.append("")
        lines.append(f"Quick stats: {total} trades, {len(wins)} wins, {len(losses)} losses")
        lines.append(f"Win rate: {len(wins)/total*100:.1f}%")

        if wins:
            lines.append(f"Avg win: {sum(t.pnl for t in wins)/len(wins):+.2f}")
        if losses:
            lines.append(f"Avg loss: {sum(t.pnl for t in losses)/len(losses):+.2f}")

        # Symbol breakdown
        from collections import Counter
        symbol_pnl: dict[str, float] = {}
        symbol_count: dict[str, int] = Counter()
        for t in trades:
            symbol_pnl[t.symbol] = symbol_pnl.get(t.symbol, 0) + (t.pnl or 0)
            symbol_count[t.symbol] += 1

        lines.append("")
        lines.append("Per-symbol P&L:")
        for sym in sorted(symbol_pnl, key=lambda s: symbol_pnl[s], reverse=True):
            lines.append(f"  {sym}: {symbol_pnl[sym]:+.2f} ({symbol_count[sym]} trades)")

        return "\n".join(lines)

    @staticmethod
    def _validate_result(result: dict) -> dict:
        """Ensure all required fields exist."""
        result.setdefault("summary", "")
        result.setdefault("performance_metrics", {})
        result.setdefault("patterns", [])
        result.setdefault("strengths", [])
        result.setdefault("weaknesses", [])
        result.setdefault("recommendations", [])

        # Validate pattern structure
        valid_patterns = []
        for p in result["patterns"]:
            if isinstance(p, dict) and "pattern" in p:
                p.setdefault("evidence", "")
                p.setdefault("severity", "medium")
                p.setdefault("actionable", True)
                if p["severity"] not in ("high", "medium", "low"):
                    p["severity"] = "medium"
                valid_patterns.append(p)
        result["patterns"] = valid_patterns

        # Validate recommendation structure
        valid_recs = []
        for r in result["recommendations"]:
            if isinstance(r, dict) and "action" in r:
                r.setdefault("expected_impact", "")
                r.setdefault("priority", "medium")
                if r["priority"] not in ("high", "medium", "low"):
                    r["priority"] = "medium"
                valid_recs.append(r)
        result["recommendations"] = valid_recs

        return result

    @staticmethod
    def _empty_result() -> dict:
        return {
            "summary": "No closed trades to analyse.",
            "performance_metrics": {},
            "patterns": [],
            "strengths": [],
            "weaknesses": [],
            "recommendations": [],
        }
