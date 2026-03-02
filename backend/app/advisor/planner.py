"""AI investment planner — uses Claude to create allocation plans."""

import json
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Import presets from strategies API
STRATEGY_PRESETS_INFO = {
    "conservative_swing": {
        "name": "Conservative Swing",
        "risk_per_trade": "1%", "min_confluence": 70, "timeframe": "4h",
        "description": "Fewer trades, wider stops, higher confluence filter",
    },
    "balanced_momentum": {
        "name": "Balanced Momentum",
        "risk_per_trade": "2%", "min_confluence": 50, "timeframe": "1h",
        "description": "Default balanced approach, good starting point",
    },
    "aggressive_scalper": {
        "name": "Aggressive Scalper",
        "risk_per_trade": "3%", "min_confluence": 35, "timeframe": "1h+4h",
        "description": "More trades, higher risk, multiple timeframes",
    },
}


def _build_advisor_prompt(scored_cryptos: list[dict], investment_amount: float,
                          risk_tolerance: str) -> str:
    """Build the Claude prompt for investment plan generation."""
    crypto_table = "\n".join([
        f"  {c['symbol']}: score={c['score']}, regime={c['regime']}, "
        f"trend={c['trend_direction']}, RSI={c['rsi']}, ADX={c['adx']}, "
        f"volatility={c['atr_pct']}%, recommendation={c['recommendation']}"
        for c in scored_cryptos[:20]
    ])

    return f"""You are a professional crypto trading advisor for an automated trading system called SignalForge.

The system uses a 6-layer signal pipeline:
1. Regime Detection (ADX+ATR) - blocks trading in chaotic markets
2. Trend Filter (EMA alignment) - requires clear bullish/bearish trend
3. Zone Identification (Fibonacci retracement + VWAP) - finds entry zones
4. Confluence Scoring (9 factors, 0-100) - requires minimum score to trade
5. Trigger Detection (MACD crossover, RSI, engulfing candles, etc.) - needs 2+ confirmations
6. Risk Management (ATR stops, Fibonacci targets, position sizing)

Available strategy presets:
- Conservative Swing: 1% risk/trade, confluence ≥70, 4h timeframe
- Balanced Momentum: 2% risk/trade, confluence ≥50, 1h timeframe
- Aggressive Scalper: 3% risk/trade, confluence ≥35, 1h+4h timeframes

Here are the top-scored cryptocurrencies from a live market scan:
{crypto_table}

The user wants to invest ${investment_amount:,.0f} with a "{risk_tolerance}" risk tolerance.

Create an investment plan. Return ONLY valid JSON with this structure:
{{
  "summary": "2-3 sentence overview of the plan and market conditions",
  "strategy_preset": "conservative_swing|balanced_momentum|aggressive_scalper",
  "selected_cryptos": [
    {{"symbol": "BTC/USDT", "reason": "Why this crypto was selected (1 sentence)"}},
    ...
  ],
  "risk_config": {{
    "account_equity": {investment_amount},
    "min_confluence": 50,
    "max_risk_per_trade": 0.02,
    "max_daily_loss": 0.06,
    "atr_sl_multiplier": 2.0,
    "min_risk_reward": 1.5
  }},
  "expected_behavior": "What the user should expect over 1 week (2-3 sentences)",
  "warnings": ["risk warning 1", "risk warning 2"]
}}

Rules:
- Select 5-10 cryptos that have the best technical setup (score ≥40, avoid "avoid" recommendations)
- Match strategy_preset to risk_tolerance: conservative→conservative_swing, balanced→balanced_momentum, aggressive→aggressive_scalper
- The risk_config values should match the chosen preset but with account_equity set to the user's amount
- Be realistic about expectations — this is paper trading for evaluation
- Include at least 2 risk warnings

Respond ONLY with valid JSON."""


class InvestmentPlanner:
    """Creates investment plans using Claude AI or algorithmic fallback."""

    def generate_plan(self, scored_cryptos: list[dict], investment_amount: float,
                      risk_tolerance: str = "balanced") -> dict:
        """Generate an investment allocation plan.

        Uses Claude if API key is configured, otherwise falls back to
        algorithmic selection.
        """
        if settings.anthropic_api_key:
            try:
                return self._generate_with_ai(scored_cryptos, investment_amount, risk_tolerance)
            except Exception:
                logger.exception("AI plan generation failed, using algorithmic fallback")

        return self._generate_algorithmic(scored_cryptos, investment_amount, risk_tolerance)

    def _generate_with_ai(self, scored_cryptos: list[dict], investment_amount: float,
                          risk_tolerance: str) -> dict:
        """Generate plan using Claude."""
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        prompt = _build_advisor_prompt(scored_cryptos, investment_amount, risk_tolerance)

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text
        plan = json.loads(raw)

        # Ensure required fields exist
        plan.setdefault("summary", "AI-generated investment plan")
        plan.setdefault("strategy_preset", "balanced_momentum")
        plan.setdefault("selected_cryptos", [])
        plan.setdefault("risk_config", {})
        plan.setdefault("expected_behavior", "")
        plan.setdefault("warnings", [])

        # Ensure account_equity is set
        plan["risk_config"]["account_equity"] = investment_amount

        return plan

    def _generate_algorithmic(self, scored_cryptos: list[dict], investment_amount: float,
                              risk_tolerance: str) -> dict:
        """Algorithmic fallback when Claude is not available."""
        preset_map = {
            "conservative": "conservative_swing",
            "balanced": "balanced_momentum",
            "aggressive": "aggressive_scalper",
        }
        preset_key = preset_map.get(risk_tolerance, "balanced_momentum")

        # Select top cryptos with score >= 30, max 8
        selected = [
            {"symbol": c["symbol"], "reason": f"Score {c['score']}/100 — {c['regime']} regime, {c['trend_direction']} trend, ADX {c['adx']}"}
            for c in scored_cryptos
            if c["score"] >= 30 and c["recommendation"] != "avoid"
        ][:8]

        if not selected:
            selected = [{"symbol": c["symbol"], "reason": f"Top by volume (score {c['score']}/100)"} for c in scored_cryptos[:5]]

        # Risk config from preset
        risk_configs = {
            "conservative_swing": {
                "account_equity": investment_amount,
                "min_confluence": 70,
                "max_risk_per_trade": 0.01,
                "max_daily_loss": 0.04,
                "atr_sl_multiplier": 2.5,
                "min_risk_reward": 2.0,
            },
            "balanced_momentum": {
                "account_equity": investment_amount,
                "min_confluence": 50,
                "max_risk_per_trade": 0.02,
                "max_daily_loss": 0.06,
                "atr_sl_multiplier": 2.0,
                "min_risk_reward": 1.5,
            },
            "aggressive_scalper": {
                "account_equity": investment_amount,
                "min_confluence": 35,
                "max_risk_per_trade": 0.03,
                "max_daily_loss": 0.08,
                "atr_sl_multiplier": 1.5,
                "min_risk_reward": 1.2,
            },
        }

        return {
            "summary": f"Algorithmic plan: {len(selected)} cryptos selected based on technical scoring. "
                       f"Using {preset_key.replace('_', ' ')} strategy with ${investment_amount:,.0f} equity.",
            "strategy_preset": preset_key,
            "selected_cryptos": selected,
            "risk_config": risk_configs.get(preset_key, risk_configs["balanced_momentum"]),
            "expected_behavior": "The system will monitor selected cryptos and generate signals when "
                                 "the 6-layer pipeline confirms a high-probability setup. Expect 0-5 trades "
                                 "per day depending on market conditions.",
            "warnings": [
                "This is paper trading only — no real money is at risk.",
                "Past technical scores do not guarantee future trading performance.",
                "The system blocks trading in chaotic market conditions for safety.",
            ],
        }
