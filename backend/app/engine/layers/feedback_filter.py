"""Feedback Filter — applies learned rules to signal decisions.

Not a pipeline layer. Acts as a pre-filter and post-filter wrapping
the pipeline execution in run_pipeline.py.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_insight import FeedbackRule

logger = logging.getLogger(__name__)


class FeedbackFilter:
    """Applies learned feedback rules to signal decisions."""

    async def should_skip(
        self,
        symbol: str,
        regime: str | None,
        db: AsyncSession,
        strategy_id: str,
    ) -> tuple[bool, str | None]:
        """Check if any active rules say to skip this symbol/condition.

        Returns (should_skip, rule_description).
        """
        rules = await self._load_active_rules(db, strategy_id)

        for rule in rules:
            conditions = rule.conditions_json or {}

            # Check symbol match
            cond_symbol = conditions.get("symbol")
            if cond_symbol and cond_symbol != symbol:
                continue

            # Check regime match
            cond_regime = conditions.get("regime")
            if cond_regime and regime and cond_regime != regime:
                continue

            # Check action
            action = conditions.get("action")
            if action == "skip" and rule.rule_type == "avoid_pattern":
                logger.info(
                    "Feedback rule skip: %s (confidence=%.2f)",
                    rule.description, rule.confidence,
                )
                return True, rule.description

        return False, None

    async def get_confluence_override(
        self,
        symbol: str,
        regime: str | None,
        db: AsyncSession,
        strategy_id: str,
    ) -> int | None:
        """Check if any rules override the min_confluence for this context.

        Returns the override value, or None if no override.
        """
        rules = await self._load_active_rules(db, strategy_id)

        for rule in rules:
            if rule.rule_type != "adjust_param":
                continue

            conditions = rule.conditions_json or {}

            cond_symbol = conditions.get("symbol")
            if cond_symbol and cond_symbol != symbol:
                continue

            cond_regime = conditions.get("regime")
            if cond_regime and regime and cond_regime != regime:
                continue

            override = conditions.get("min_confluence")
            if override is not None:
                return int(override)

        return None

    @staticmethod
    async def _load_active_rules(db: AsyncSession, strategy_id: str) -> list:
        """Load active, non-expired feedback rules for a strategy."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(FeedbackRule).where(
                FeedbackRule.strategy_id == strategy_id,
                FeedbackRule.is_active == True,  # noqa: E712
                (FeedbackRule.expires_at.is_(None)) | (FeedbackRule.expires_at > now),
            )
        )
        return list(result.scalars().all())
