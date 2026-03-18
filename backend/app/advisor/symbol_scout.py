"""SymbolScout — AI-driven evaluation of new symbol candidates.

Called by the universe expansion task every 6 hours (and on-demand) to decide
which high-volume USDT pairs are worth adding to the candidate pool.

This is strategic selection, not signal evaluation:
  - Signal evaluation (SignalQualityEvaluator) happens per-signal during live trading.
  - Symbol selection (SymbolScout) decides which symbols the pipeline should watch at all.

No AI → no candidates added (No AI, No Trading principle).
"""

import logging

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a systematic cryptocurrency trading analyst evaluating
new symbol candidates for a watchlist.

Given a list of new USDT trading pairs (with 24h volume) and the
active strategy parameters, select which symbols are worth monitoring.

Criteria for inclusion:
- Sufficient market structure for technical analysis
  (not pure speculation with no trend history)
- Volume consistent enough to produce reliable candle data
- Avoid symbols that heavily duplicate existing watchlist coverage
  (same sector, near-perfect correlation with already-watched tokens)
- Prefer symbols with observable trend/range regimes over purely
  random price action

Do NOT try to predict price direction. You are deciding which symbols
deserve pipeline attention, not which to buy.

Respond with JSON only:
{
  "approved": ["SYM1/USDT", "SYM2/USDT"],
  "rejected_count": 12,
  "reasoning": "One or two sentences explaining the selection logic."
}

If you have no candidates to evaluate, return:
{"approved": [], "rejected_count": 0, "reasoning": "No candidates."}
"""


class SymbolScout:
    """Evaluates new symbol candidates using Claude and returns approved symbols."""

    async def evaluate_candidates(
        self,
        candidates: list[dict],
        strategy_config: dict,
        current_watchlist: set[str],
    ) -> list[str]:
        """Ask Claude which candidates are worth adding to the watchlist.

        Args:
            candidates: list of dicts with keys ``symbol`` and ``quoteVolume``
                        (already volume-filtered, sorted by volume desc)
            strategy_config: the active strategy's config dict (for context)
            current_watchlist: symbols already watched (Claude avoids redundancy)

        Returns:
            List of approved symbol strings. Empty list if Claude unavailable.
        """
        from app.advisor.claude_client import ModelTier, claude_client

        if not candidates:
            return []

        # Cap at 100 candidates per call — sending 1000 symbols wastes tokens
        candidates = candidates[:100]

        user_message = _build_user_message(candidates, strategy_config, current_watchlist)

        result = await claude_client.ask_json(
            ModelTier.DEEP,
            _SYSTEM_PROMPT,
            user_message,
            max_tokens=1024,
            cache_ttl=0,
            insight_type="symbol_scout",
        )

        if result is None:
            logger.warning("SymbolScout: Claude unavailable — no candidates approved")
            return []

        approved = result.get("approved", [])
        reasoning = result.get("reasoning", "")
        rejected = result.get("rejected_count", len(candidates) - len(approved))

        logger.info(
            "SymbolScout: %d/%d candidates approved. Reasoning: %s",
            len(approved), len(approved) + rejected, reasoning,
        )

        # Validate: only return symbols that were actually in our candidate list
        candidate_symbols = {c["symbol"] for c in candidates}
        approved = [s for s in approved if s in candidate_symbols]

        return approved


def _build_user_message(
    candidates: list[dict],
    strategy_config: dict,
    current_watchlist: set[str],
) -> str:
    timeframes = strategy_config.get("timeframes", ["4h"])
    min_confluence = strategy_config.get("min_confluence", 70)

    watchlist_sample = sorted(current_watchlist)[:20]
    watchlist_str = ", ".join(watchlist_sample)
    if len(current_watchlist) > 20:
        watchlist_str += f" … and {len(current_watchlist) - 20} more"

    candidate_lines = "\n".join(
        f"  {c['symbol']}  vol=${c.get('quoteVolume', 0):,.0f}"
        for c in candidates
    )

    return f"""Strategy context:
- Timeframes: {', '.join(timeframes)}
- Min confluence required: {min_confluence}
- Current watchlist ({len(current_watchlist)} symbols): {watchlist_str}

New candidates to evaluate ({len(candidates)} symbols, sorted by 24h volume):
{candidate_lines}

Which of these candidates are worth adding to the watchlist for pipeline evaluation?"""
