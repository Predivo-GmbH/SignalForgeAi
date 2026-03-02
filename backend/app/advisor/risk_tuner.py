"""Adaptive Risk Tuner — Claude-powered strategy parameter optimization."""

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
parameter adjustments to optimize the strategy.

Recommend CONSERVATIVE adjustments — never change any parameter by more
than 20% from its current value in a single adjustment.

RISK MANAGEMENT parameters:
- min_confluence: 10-100 (higher = fewer but better trades)
- max_risk_per_trade: 0.005-0.10 (fraction of equity per trade)
- max_daily_loss: 0.01-0.20 (daily loss circuit breaker)
- atr_sl_multiplier: 0.5-5.0 (wider = fewer stop-outs)
- min_risk_reward: 0.5-5.0 (must be <= 1.6 — pipeline R:R is ~1.618)

PIPELINE SENSITIVITY parameters (directly control trade frequency):
- min_trigger_count: 1-5 (how many of 5 trigger types must confirm entry; lower = more trades)
- trigger_lookback_candles: 1-10 (window to check for crossovers; 1 = exact candle only, higher = more forgiving)
- ema_slope_threshold: 0.0001-0.01 (minimum EMA-200 slope for trend; lower = accepts weaker trends)

CRITICAL: If the strategy has generated ZERO signals over 24+ hours, the
pipeline sensitivity is too strict. In that case, you MUST loosen at least
one of: lower min_trigger_count, raise trigger_lookback_candles, or lower
ema_slope_threshold.

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

# Bounds for each tunable parameter
PARAM_BOUNDS = {
    "min_confluence": (10, 100),
    "max_risk_per_trade": (0.005, 0.10),
    "max_daily_loss": (0.01, 0.20),
    "atr_sl_multiplier": (0.5, 5.0),
    "min_risk_reward": (0.5, 5.0),
    # Pipeline sensitivity
    "min_trigger_count": (1, 5),
    "trigger_lookback_candles": (1, 10),
    "ema_slope_threshold": (0.0001, 0.01),
}

MAX_CHANGE_PCT = 0.20  # 20% max change per adjustment


class RiskTuner:
    """Analyzes performance and adjusts strategy risk parameters."""

    async def tune(self, strategy, db: AsyncSession) -> dict:
        """Analyze recent trades and return parameter adjustments.

        Returns dict with adjustments, reasoning, and metrics_snapshot.
        """
        cfg = strategy.config or {}
        current_params = {
            "min_confluence": cfg.get("min_confluence", 50),
            "max_risk_per_trade": cfg.get("max_risk_per_trade", 0.02),
            "max_daily_loss": cfg.get("max_daily_loss", 0.06),
            "atr_sl_multiplier": cfg.get("atr_sl_multiplier", 2.0),
            "min_risk_reward": cfg.get("min_risk_reward", 1.5),
            # Pipeline sensitivity
            "min_trigger_count": cfg.get("min_trigger_count", 2),
            "trigger_lookback_candles": cfg.get("trigger_lookback_candles", 1),
            "ema_slope_threshold": cfg.get("ema_slope_threshold", 0.001),
        }

        # Check for zero-signal condition — strategy active but no signals at all
        from datetime import datetime, timedelta, timezone

        from sqlalchemy import func

        signal_count_result = await db.execute(
            select(func.count(Signal.id)).where(
                Signal.strategy_id == strategy.id,
            )
        )
        total_signals = signal_count_result.scalar() or 0

        strategy_age_hours = 0.0
        if strategy.created_at:
            strategy_age_hours = (
                datetime.now(timezone.utc) - strategy.created_at.replace(tzinfo=timezone.utc)
            ).total_seconds() / 3600

        zero_signals = total_signals == 0 and strategy_age_hours >= 24

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

        # Build metrics — either from trades or a zero-signal summary
        if len(trades) >= 5:
            metrics = self._compute_metrics(trades)
        elif zero_signals:
            metrics = {
                "total_trades": 0,
                "total_signals": 0,
                "strategy_age_hours": round(strategy_age_hours, 1),
                "win_rate": 0,
                "avg_pnl": 0,
                "avg_risk_reward": 0,
                "max_drawdown_pct": 0,
                "stop_loss_hit_rate": 0,
            }
        else:
            return {
                "adjustments": {},
                "reasoning": "Insufficient trade history (need at least 5 closed trades).",
                "metrics_snapshot": {"total_trades": len(trades)},
            }

        pattern_context = await self._load_pattern_context(strategy.id)
        user_message = self._build_user_message(
            current_params, metrics, pattern_context, zero_signals,
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

        # Algorithmic fallback only when Claude is unavailable
        if zero_signals:
            return self._no_signals_fallback(current_params, strategy_age_hours)
        return self._algorithmic_fallback(metrics, current_params)

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
        lines = ["Current strategy parameters:"]
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

    @staticmethod
    def _no_signals_fallback(current_params: dict, age_hours: float) -> dict:
        """Loosen pipeline sensitivity when zero signals have been generated."""
        adjustments = {}

        # Lower min_trigger_count toward 1
        if current_params["min_trigger_count"] > 1:
            adjustments["min_trigger_count"] = max(1, current_params["min_trigger_count"] - 1)

        # Raise trigger_lookback_candles toward 5
        if current_params["trigger_lookback_candles"] < 5:
            adjustments["trigger_lookback_candles"] = min(
                5, current_params["trigger_lookback_candles"] + 2,
            )

        # Lower ema_slope_threshold toward 0.0002
        if current_params["ema_slope_threshold"] > 0.0003:
            adjustments["ema_slope_threshold"] = round(
                max(0.0002, current_params["ema_slope_threshold"] * 0.6), 4,
            )

        # Also lower min_confluence if still high
        if current_params["min_confluence"] > 40:
            adjustments["min_confluence"] = max(35, current_params["min_confluence"] - 10)

        return {
            "adjustments": adjustments,
            "reasoning": (
                f"Strategy has generated zero signals after {age_hours:.0f} hours. "
                f"Pipeline sensitivity is too strict for current market conditions. "
                f"Loosening trigger requirements and trend threshold to enable signal generation."
            ),
            "metrics_snapshot": {"total_trades": 0, "total_signals": 0},
        }

    @staticmethod
    def _algorithmic_fallback(metrics: dict, current_params: dict) -> dict:
        """Simple rule-based adjustments when Claude unavailable."""
        adjustments = {}

        # If win rate < 40%, raise min_confluence
        if metrics["win_rate"] < 0.40:
            new_conf = min(100, current_params["min_confluence"] + 5)
            if new_conf != current_params["min_confluence"]:
                adjustments["min_confluence"] = new_conf

        # If SL hit rate > 60%, widen stops
        if metrics["stop_loss_hit_rate"] > 0.60:
            new_atr = min(5.0, current_params["atr_sl_multiplier"] * 1.1)
            adjustments["atr_sl_multiplier"] = round(new_atr, 2)

        # If max drawdown > 10%, reduce risk per trade
        if metrics["max_drawdown_pct"] > 0.10:
            new_risk = max(0.005, current_params["max_risk_per_trade"] * 0.9)
            adjustments["max_risk_per_trade"] = round(new_risk, 4)

        # If few trades and min_trigger_count is high, lower it
        if metrics["total_trades"] < 5 and current_params.get("min_trigger_count", 2) > 1:
            adjustments["min_trigger_count"] = max(
                1, current_params["min_trigger_count"] - 1,
            )

        reasoning = "Algorithmic fallback: "
        if adjustments:
            reasoning += ", ".join(
                f"{k} adjusted to {v}" for k, v in adjustments.items()
            )
        else:
            reasoning += "no adjustments needed based on current metrics."

        return {
            "adjustments": adjustments,
            "reasoning": reasoning,
            "metrics_snapshot": metrics,
        }
