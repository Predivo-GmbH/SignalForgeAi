"""Adaptive Risk Tuner — Claude-powered strategy parameter optimization.

When Claude is unavailable, no adjustments are made — the system does not
modify strategy parameters without AI analysis.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.advisor.claude_client import ModelTier, claude_client
from app.models.signal import Signal
from app.models.trade import Trade

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a risk management specialist for SignalForge, an automated crypto
trading platform. You analyze recent trading performance and recommend
risk parameter adjustments to optimize the strategy.

Recommend CONSERVATIVE adjustments — never change any parameter by more
than 20% from its current value in a single adjustment.

You may ONLY adjust these RISK MANAGEMENT parameters:
- min_confluence: 10-100 (higher = fewer but better trades)
- max_risk_per_trade: 0.005-0.10 (fraction of equity per trade)
- max_daily_loss: 0.01-0.20 (daily loss circuit breaker)
- atr_sl_multiplier: 0.5-5.0 (wider = fewer stop-outs)
- min_risk_reward: 0.5-5.0 (must be <= 1.6 — pipeline R:R is ~1.618)

Do NOT adjust pipeline sensitivity parameters (min_trigger_count,
trigger_lookback_candles, ema_slope_threshold). Those are part of the
strategy identity set by the AI Advisor and must not be changed.

Return ONLY valid JSON:
{
  "adjustments": {
    "param_name": new_value
  },
  "reasoning": "2-3 sentence explanation",
  "metrics_snapshot": {
    "win_rate": 0.0-1.0,
    "avg_pnl": number,
    "avg_risk_reward": number,
    "total_trades": number,
    "max_drawdown_pct": number
  }
}

Only include parameters that need changing in "adjustments".
If no changes are needed, return an empty adjustments object.
Respond ONLY with valid JSON."""

# Bounds for each tunable parameter (risk management only)
PARAM_BOUNDS = {
    "min_confluence": (10, 100),
    "max_risk_per_trade": (0.005, 0.10),
    "max_daily_loss": (0.01, 0.20),
    "atr_sl_multiplier": (0.5, 5.0),
    "min_risk_reward": (0.5, 5.0),
}

MAX_CHANGE_PCT = 0.20  # 20% max change per adjustment


class RiskTuner:
    """Analyzes performance and adjusts strategy risk parameters."""

    async def tune(self, strategy, db: AsyncSession) -> dict:
        """Analyze recent trades and return risk parameter adjustments.

        Only adjusts risk management parameters based on actual trade
        performance. Pipeline sensitivity parameters are part of the
        strategy identity and are never modified here.

        Returns dict with adjustments, reasoning, and metrics_snapshot.
        """
        cfg = strategy.config or {}
        current_params = {
            "min_confluence": cfg.get("min_confluence", 50),
            "max_risk_per_trade": cfg.get("max_risk_per_trade", 0.02),
            "max_daily_loss": cfg.get("max_daily_loss", 0.06),
            "atr_sl_multiplier": cfg.get("atr_sl_multiplier", 2.0),
            "min_risk_reward": cfg.get("min_risk_reward", 1.5),
        }

        # Load recent trades for this strategy (via Signal join)
        result = await db.execute(
            select(Trade)
            .join(Signal, Trade.signal_id == Signal.id)
            .where(
                Signal.strategy_id == strategy.id,
                Trade.pnl.is_not(None),
            )
            .order_by(Trade.exit_time.desc())
            .limit(50)
        )
        trades = list(result.scalars().all())

        if len(trades) < 5:
            return {
                "adjustments": {},
                "reasoning": "Insufficient trade history (need at least 5 closed trades).",
                "metrics_snapshot": {"total_trades": len(trades)},
            }

        metrics = self._compute_metrics(trades)

        pattern_context = await self._load_pattern_context(strategy.id)
        user_message = self._build_user_message(
            current_params, metrics, pattern_context,
        )

        ai_result = await claude_client.ask_json(
            ModelTier.DEEP,
            SYSTEM_PROMPT,
            user_message,
            cache_ttl=0,
            insight_type="risk_tuning",
        )

        if ai_result is not None:
            validated = self._validate_adjustments(
                ai_result.get("adjustments", {}), current_params,
            )
            return {
                "adjustments": validated,
                "reasoning": ai_result.get("reasoning", ""),
                "metrics_snapshot": ai_result.get("metrics_snapshot", metrics),
            }

        # Claude unavailable — no adjustments. The system does not modify
        # strategy parameters without AI analysis.
        logger.warning("Claude unavailable — skipping risk tuning (no adjustments without AI)")
        return {
            "adjustments": {},
            "reasoning": (
                "Claude unavailable — no adjustments made. "
                "The system does not modify strategy parameters "
                "without AI analysis."
            ),
            "metrics_snapshot": metrics,
        }

    @staticmethod
    def _compute_metrics(trades: list) -> dict:
        """Compute performance metrics from trade history."""
        total = len(trades)
        wins = [t for t in trades if t.pnl and t.pnl > 0]
        losses = [t for t in trades if t.pnl and t.pnl <= 0]

        win_rate = len(wins) / total if total else 0
        avg_pnl = sum(t.pnl for t in trades if t.pnl) / total if total else 0
        avg_rr = (
            sum(t.risk_reward for t in trades if t.risk_reward)
            / sum(1 for t in trades if t.risk_reward)
            if any(t.risk_reward for t in trades)
            else 0
        )

        # Compute max drawdown from cumulative PnL
        cumulative = 0.0
        peak = 0.0
        max_dd = 0.0
        for t in sorted(trades, key=lambda x: x.exit_time or x.created_at):
            cumulative += t.pnl or 0
            peak = max(peak, cumulative)
            dd = (peak - cumulative) / max(peak, 1)
            max_dd = max(max_dd, dd)

        sl_count = sum(1 for t in losses if t.exit_reason == "stop_loss")
        sl_rate = sl_count / len(losses) if losses else 0

        return {
            "win_rate": round(win_rate, 3),
            "avg_pnl": round(avg_pnl, 2),
            "avg_risk_reward": round(avg_rr, 2),
            "total_trades": total,
            "max_drawdown_pct": round(max_dd, 3),
            "stop_loss_hit_rate": round(sl_rate, 3),
            "avg_confluence_wins": round(
                sum(t.confluence_score for t in wins if t.confluence_score)
                / max(len(wins), 1), 1,
            ),
            "avg_confluence_losses": round(
                sum(t.confluence_score for t in losses if t.confluence_score)
                / max(len(losses), 1), 1,
            ),
        }

    @staticmethod
    async def _load_pattern_context(strategy_id) -> dict | None:
        """Load cached pattern analysis from Redis (produced by periodic task)."""
        try:
            import json as _json

            from app.core.redis_client import redis_client

            raw = await redis_client.get(f"pattern_analysis:{strategy_id}")
            if raw:
                return _json.loads(raw)
        except Exception:
            pass
        return None

    @staticmethod
    def _build_user_message(
        current_params: dict,
        metrics: dict,
        pattern_context: dict | None = None,
    ) -> str:
        lines = ["Current risk parameters:"]
        for k, v in current_params.items():
            lines.append(f"  {k}: {v}")

        lines.append("")
        lines.append("Recent performance metrics (last 50 trades):")
        for k, v in metrics.items():
            lines.append(f"  {k}: {v}")

        if pattern_context:
            patterns = pattern_context.get("patterns", [])
            recs = pattern_context.get("recommendations", [])
            if patterns or recs:
                lines.append("")
                lines.append("Deep pattern analysis insights:")
                for p in patterns[:5]:
                    lines.append(
                        f"  [{p.get('severity', 'medium')}] {p.get('pattern', '')}"
                    )
                for r in recs[:3]:
                    lines.append(
                        f"  Recommendation: {r.get('action', '')}"
                    )

        return "\n".join(lines)

    @staticmethod
    def _validate_adjustments(adjustments: dict, current_params: dict) -> dict:
        """Validate adjustments are within bounds and max 20% change."""
        validated = {}
        for param, new_val in adjustments.items():
            if param not in PARAM_BOUNDS:
                continue

            lo, hi = PARAM_BOUNDS[param]
            current = current_params.get(param)
            if current is None:
                continue

            new_val = float(new_val)
            # Clamp to valid range
            new_val = max(lo, min(hi, new_val))
            # Enforce max 20% change
            max_change = abs(current) * MAX_CHANGE_PCT
            if abs(new_val - current) > max_change:
                if new_val > current:
                    new_val = current + max_change
                else:
                    new_val = current - max_change
                new_val = max(lo, min(hi, new_val))

            # Only include if actually changed
            if abs(new_val - current) > 1e-6:
                validated[param] = round(new_val, 4)

        return validated

