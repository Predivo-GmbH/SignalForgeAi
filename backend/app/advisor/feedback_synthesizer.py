"""Feedback Synthesizer — converts trade patterns into actionable rules.

When Claude is unavailable, no rules are generated — the system does not
create feedback rules without AI analysis.
"""

import logging
import uuid as uuid_mod
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.advisor.claude_client import ModelTier, claude_client
from app.models.ai_insight import FeedbackRule
from app.models.signal import Signal
from app.models.trade import Trade

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a trading systems engineer for an automated crypto trading "
    "platform called SignalForgeAI. You analyze batches of completed trades "
    "to identify recurring patterns that should be encoded as rules for "
    "the system.\n\n"
    "Rules must be specific and actionable. Each rule should have:\n"
    "1. A clear condition (what market state or signal characteristic "
    "triggers this rule)\n"
    "2. A clear action (skip signal, adjust parameter, require extra "
    "confirmation)\n"
    "3. A confidence level (0.0-1.0) based on how consistent the "
    "pattern is\n\n"
    "Only propose rules backed by 3+ trades showing the same pattern.\n\n"
    'Return ONLY valid JSON with this structure:\n'
    '{\n'
    '  "rules": [\n'
    '    {\n'
    '      "rule_type": '
    '"avoid_pattern|prefer_pattern|adjust_param|filter_condition",\n'
    '      "description": "Human-readable description of the rule",\n'
    '      "conditions": {\n'
    '        "symbol": "BTC/USDT or null for any",\n'
    '        "regime": "trending|ranging|chaotic or null for any",\n'
    '        "min_confluence": null or number,\n'
    '        "action": "skip|reduce_size|require_confirmation"\n'
    '      },\n'
    '      "confidence": 0.0-1.0,\n'
    '      "evidence": "What trades support this rule"\n'
    '    }\n'
    '  ],\n'
    '  "summary": "1-2 sentence summary of findings"\n'
    '}\n\n'
    "Respond ONLY with valid JSON."
)



class FeedbackSynthesizer:
    """Converts trade analysis patterns into actionable feedback rules."""

    async def synthesize(self, strategy_id: str, user_id: str, db: AsyncSession) -> list[dict]:
        """Analyze recent trades and produce feedback rules.

        Returns list of newly created FeedbackRule dicts.
        """
        result = await db.execute(
            select(Trade)
            .join(Signal, Trade.signal_id == Signal.id)
            .where(
                Signal.strategy_id == uuid_mod.UUID(strategy_id),
                Trade.pnl.is_not(None),
            )
            .order_by(Trade.exit_time.desc())
            .limit(50)
        )
        trades = list(result.scalars().all())

        if len(trades) < 10:
            return []

        user_message = self._build_user_message(trades)
        ai_result = await claude_client.ask_json(
            ModelTier.DEEP,
            SYSTEM_PROMPT,
            user_message,
            cache_ttl=0,
            insight_type="feedback_synthesis",
        )

        if ai_result is None:
            logger.warning("Claude unavailable — skipping feedback synthesis (no rules without AI)")
            return []

        new_rules = []
        for rule_data in ai_result.get("rules", []):
            if not self._validate_rule(rule_data):
                continue

            rule = FeedbackRule(
                strategy_id=uuid_mod.UUID(strategy_id),
                user_id=uuid_mod.UUID(user_id),
                rule_type=rule_data.get("rule_type", "filter_condition"),
                description=rule_data.get("description", ""),
                conditions_json=rule_data.get("conditions", {}),
                confidence=min(1.0, max(0.0, float(rule_data.get("confidence", 0.5)))),
                is_active=True,
                expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            )
            db.add(rule)
            new_rules.append({
                "rule_type": rule.rule_type,
                "description": rule.description,
                "conditions": rule.conditions_json,
                "confidence": rule.confidence,
            })

        return new_rules

    @staticmethod
    def _build_user_message(trades: list) -> str:
        lines = [f"Analyzing {len(trades)} recent trades for pattern-based rules:", ""]

        for i, t in enumerate(trades, 1):
            lines.append(
                f"{i}. {t.symbol} {t.direction} | "
                f"PnL: {t.pnl:+.2f} | Confluence: {t.confluence_score or 'N/A'} | "
                f"Exit: {t.exit_reason or 'N/A'} | R:R: {t.risk_reward or 'N/A'}"
            )

        return "\n".join(lines)

    @staticmethod
    def _validate_rule(rule_data: dict) -> bool:
        """Check that a rule has required fields."""
        if not isinstance(rule_data, dict):
            return False
        if "description" not in rule_data:
            return False
        rule_type = rule_data.get("rule_type", "")
        return rule_type in ("avoid_pattern", "prefer_pattern", "adjust_param", "filter_condition")

