"""AI investment planner — autonomous strategy generation.

The AI advisor analyzes market conditions and determines ALL optimal
strategy parameters. No presets. No human risk selection.

When Claude is unavailable, plan generation fails — the system does not
trade without AI analysis.
"""

import logging

import numpy as np

from app.advisor.claude_client import ModelTier, claude_client

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = """\
You are the autonomous AI trading advisor for SignalForge.
You analyze market conditions and determine the OPTIMAL strategy parameters.
There are no presets — you decide everything based on your analysis.

The trading pipeline has 6 sequential layers. A trade is only placed when
ALL layers pass. You control the sensitivity of each gate:

PIPELINE SENSITIVITY (directly controls trade frequency):
- min_confluence (10-100): Minimum technical confluence score to accept a signal.
  14 weighted factors (Fibonacci, S/R overlap, VWAP, RSI, MACD, Bollinger, etc.)
  scored 0-100. Lower threshold = more trades but lower quality. Typical: 35-60.
- min_trigger_count (1-5): How many of 5 trigger types must confirm entry.
  Triggers: MACD crossover, RSI midline cross, stochastic exit, engulfing candle,
  zone reclaim. Each is a crossover event. Lower = more trades. Typical: 1-2.
- trigger_lookback_candles (1-10): How many candles back to check for trigger
  crossovers. 1 = must happen on the exact latest candle (very strict).
  3-5 = crossover within recent candles (much more achievable). Typical: 3-5.
- ema_slope_threshold (0.0001-0.01): Minimum EMA-200 slope for trend
  confirmation. Lower = accepts weaker/developing trends. Typical: 0.0003-0.002.

RISK MANAGEMENT:
- max_risk_per_trade (0.001-0.10): Max position risk as fraction of equity.
- max_daily_loss (0.01-0.20): Daily loss circuit breaker fraction.
- atr_sl_multiplier (0.5-5.0): Stop-loss distance in ATR multiples.
- min_risk_reward (0.5-5.0): Minimum reward:risk ratio. The pipeline uses
  Fibonacci extensions (TP1=1.618x risk), so R:R is always ~1.618. Set this
  at or below 1.618 to avoid blocking all trades.

TIMEFRAMES:
- timeframes: ["1h"] or ["4h"] or ["1h", "4h"]. 1h = more frequent signals.

RISK FEATURES (enable/disable based on conditions):
- trailing_stop_enabled (bool) + atr_trail_multiplier (0.5-5.0)
- drawdown_breaker_enabled (bool) + max_drawdown_pct (0.05-0.50)
- break_even_enabled (bool) + break_even_r_multiple (0.5-3.0)
- cppi_enabled (bool) + cppi_multiplier (1.0-10.0)
- max_hold_hours (1-168): Close position after this many hours.
- correlation_monitor_enabled (bool) + correlation_threshold (0.3-0.95)

USDT RESERVE POLICY:
You must also recommend the optimal USDT reserve percentage for the portfolio.
This controls how much of the portfolio value stays as USDT (dry powder) and is
NOT deployed into trades. The reserve ensures the system can act on buy signals.

Guidelines for usdt_reserve_pct (0.0 - 0.50):
- Strong bull market, high trending%: 0.05 - 0.10 (maximize exposure)
- Normal/mixed market: 0.10 - 0.20 (balanced)
- Weak/choppy market, low trending%: 0.15 - 0.25 (preserve capital)
- Bear market, high chaotic%: 0.25 - 0.40 (defensive, keep dry powder)
- Extreme fear/crash conditions: 0.35 - 0.50 (cash-heavy, wait for opportunities)

Include "usdt_reserve_pct" in strategy_config and "reserve_reasoning" (1 sentence
explaining your choice) in the top-level response.

CRITICAL RULES:
- Choose parameters that match current market conditions. If the market is
  not suitable for trading, strict parameters that produce zero trades is
  the correct outcome — do NOT artificially loosen settings to force trades.
- In low-trending markets (trending% < 30), adjust ema_slope_threshold and
  trigger_lookback_candles to match actual market behavior — not to force signals.
- min_risk_reward MUST be <= 1.6 (pipeline R:R is ~1.618 from Fibonacci).
- Select 3-15 cryptos with the best technical setups.

Respond ONLY with valid JSON."""


def _build_advisor_user_message(
    scored_cryptos: list[dict],
    investment_amount: float,
    market_profile: dict,
) -> str:
    """Build the user message for autonomous plan generation."""
    crypto_table = "\n".join([
        f"  {c['symbol']}: score={c['score']}, regime={c['regime']}, "
        f"trend={c['trend_direction']}, RSI={c['rsi']}, ADX={c['adx']}, "
        f"volatility={c['atr_pct']}%, recommendation={c['recommendation']}"
        for c in scored_cryptos[:30]
    ])

    profile_lines = "\n".join(
        f"  {k}: {v}" for k, v in market_profile.items()
    )

    return f"""Market scan results — top-scored cryptocurrencies:
{crypto_table}

Market profile:
{profile_lines}

Investment amount: ${investment_amount:,.0f}

Analyze these market conditions and generate the OPTIMAL strategy.
Return ONLY valid JSON:
{{
  "summary": "2-3 sentence market analysis and strategy rationale",
  "selected_cryptos": [
    {{"symbol": "BTC/USDT", "reason": "Why selected (1 sentence)"}},
    ...
  ],
  "strategy_config": {{
    "min_confluence": 45,
    "min_trigger_count": 2,
    "trigger_lookback_candles": 3,
    "ema_slope_threshold": 0.0005,
    "max_risk_per_trade": 0.02,
    "max_daily_loss": 0.06,
    "atr_sl_multiplier": 2.0,
    "min_risk_reward": 1.5,
    "timeframes": ["1h"],
    "trailing_stop_enabled": false,
    "atr_trail_multiplier": 2.0,
    "drawdown_breaker_enabled": true,
    "max_drawdown_pct": 0.15,
    "break_even_enabled": true,
    "break_even_r_multiple": 1.0,
    "cppi_enabled": false,
    "max_hold_hours": 24,
    "correlation_monitor_enabled": true,
    "correlation_threshold": 0.7,
    "usdt_reserve_pct": 0.15
  }},
  "reasoning": "Detailed explanation of why these parameters are optimal",
  "reserve_reasoning": "Why this USDT reserve % is optimal for current conditions",
  "expected_behavior": "What to expect over 1 week (2-3 sentences)",
  "warnings": ["risk warning 1", "risk warning 2"]
}}"""


class InvestmentPlanner:
    """Creates optimal investment plans using Claude AI."""

    def generate_plan(
        self,
        scored_cryptos: list[dict],
        investment_amount: float,
        market_profile: dict | None = None,
    ) -> dict | None:
        """Generate an autonomous investment plan.

        The AI determines ALL strategy parameters — no presets, no human
        risk selection. Uses Claude Sonnet for deep reasoning about
        parameter interactions.

        Returns None if Claude is unavailable — the system does not
        generate strategies without AI analysis.
        """
        if market_profile is None:
            market_profile = _compute_basic_profile(scored_cryptos)

        plan = claude_client.ask_json_sync(
            ModelTier.DEEP,
            PLANNER_SYSTEM_PROMPT,
            _build_advisor_user_message(scored_cryptos, investment_amount, market_profile),
            max_tokens=2500,
            cache_ttl=0,
            insight_type="investment_plan",
        )

        if plan is not None:
            plan.setdefault("summary", "AI-generated optimal strategy")
            plan.setdefault("selected_cryptos", [])
            plan.setdefault("strategy_config", {})
            plan.setdefault("reasoning", "")
            plan.setdefault("expected_behavior", "")
            plan.setdefault("warnings", [])
            plan["strategy_config"]["account_equity"] = investment_amount
            return plan

        logger.warning("Claude unavailable — cannot generate investment plan without AI analysis")
        return None


def _compute_basic_profile(scored_cryptos: list[dict]) -> dict:
    """Compute a basic market profile from scored crypto data."""
    if not scored_cryptos:
        return {
            "trending_pct": 0, "bullish_pct": 0, "avg_score": 0,
            "avg_adx": 0, "avg_volatility": 0, "chaotic_pct": 0,
        }

    total = len(scored_cryptos)
    trending = sum(
        1 for c in scored_cryptos
        if c.get("regime", "").startswith("trending")
    )
    bullish = sum(1 for c in scored_cryptos if c.get("trend_direction") == "bullish")
    chaotic = sum(1 for c in scored_cryptos if c.get("regime") == "chaotic")

    return {
        "trending_pct": round(trending / total * 100, 1),
        "bullish_pct": round(bullish / total * 100, 1),
        "avg_score": round(float(np.mean([c.get("score", 0) for c in scored_cryptos])), 1),
        "avg_adx": round(float(np.mean([c.get("adx", 0) for c in scored_cryptos])), 1),
        "avg_volatility": round(float(np.mean([c.get("atr_pct", 0) for c in scored_cryptos])), 2),
        "chaotic_pct": round(chaotic / total * 100, 1),
    }
