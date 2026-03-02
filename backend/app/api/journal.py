"""Trade Journal AI — analyse trades with Claude."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.advisor.claude_client import ModelTier, claude_client
from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.models.trade import Trade

logger = logging.getLogger(__name__)

router = APIRouter(tags=["journal"])

JOURNAL_SYSTEM_PROMPT = (
    "You are a professional trading coach. Analyse the trade provided and return "
    "a JSON object with three keys: analysis (string), patterns (list of strings), "
    "recommendations (list of strings). Respond ONLY with valid JSON."
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    trade_id: str


class TradeAnalysis(BaseModel):
    analysis: str
    patterns: list[str]
    recommendations: list[str]


class PatternSummary(BaseModel):
    summary: str
    top_patterns: list[str]
    areas_to_improve: list[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_trade_user_message(trade_data: dict) -> str:
    """Build the user message for trade analysis."""
    return (
        f"Symbol: {trade_data.get('symbol')}\n"
        f"Direction: {trade_data.get('direction')}\n"
        f"Entry price: {trade_data.get('entry_price')}\n"
        f"Exit price: {trade_data.get('exit_price')}\n"
        f"PnL: {trade_data.get('pnl')}\n"
        f"Confluence score: {trade_data.get('confluence_score')}\n"
        f"Exit reason: {trade_data.get('exit_reason')}\n"
        f"Risk/Reward: {trade_data.get('risk_reward')}"
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/journal/analyze", response_model=TradeAnalysis)
async def analyze_trade(
    body: AnalyzeRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Analyse a single trade with Claude."""
    # Fetch trade scoped to user
    result = await db.execute(
        select(Trade).where(Trade.id == body.trade_id, Trade.user_id == user_id)
    )
    trade = result.scalar_one_or_none()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    trade_data = {
        "symbol": trade.symbol,
        "direction": trade.direction,
        "entry_price": trade.entry_price,
        "exit_price": trade.exit_price,
        "pnl": trade.pnl,
        "confluence_score": trade.confluence_score,
        "exit_reason": trade.exit_reason,
        "risk_reward": trade.risk_reward,
    }

    parsed = await claude_client.ask_json(
        ModelTier.FAST,
        JOURNAL_SYSTEM_PROMPT,
        _build_trade_user_message(trade_data),
        max_tokens=500,
        cache_ttl=0,
        insight_type="trade_journal",
    )

    if parsed is not None:
        return TradeAnalysis(
            analysis=parsed.get("analysis", ""),
            patterns=parsed.get("patterns", []),
            recommendations=parsed.get("recommendations", []),
        )

    if not claude_client.available:
        return TradeAnalysis(
            analysis="AI analysis unavailable — no API key configured.",
            patterns=[],
            recommendations=["Configure ANTHROPIC_API_KEY to enable AI analysis."],
        )

    return TradeAnalysis(
        analysis="AI analysis failed. Please try again later.",
        patterns=[],
        recommendations=[],
    )


@router.get("/journal/patterns", response_model=PatternSummary)
async def get_patterns(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate pattern analysis from recent trades."""
    result = await db.execute(
        select(Trade)
        .where(Trade.user_id == user_id, Trade.pnl.is_not(None))
        .order_by(Trade.exit_time.desc())
        .limit(50)
    )
    trades = list(result.scalars().all())

    if not trades:
        return PatternSummary(
            summary="No closed trades to analyse.",
            top_patterns=[],
            areas_to_improve=[],
        )

    wins = [t for t in trades if t.pnl and t.pnl > 0]
    losses = [t for t in trades if t.pnl and t.pnl <= 0]
    total = len(trades)
    win_rate = len(wins) / total * 100 if total else 0

    patterns: list[str] = []
    improvements: list[str] = []

    # Low confluence on losses
    low_conf_losses = [t for t in losses if t.confluence_score < 50]
    if low_conf_losses:
        patterns.append(
            f"{len(low_conf_losses)} losses had confluence < 50 — avoid low-conviction entries."
        )
        improvements.append("Raise minimum confluence threshold before entering trades.")

    # Tight stops (high stop-loss hit rate)
    sl_trades = [t for t in losses if t.exit_reason == "stop_loss"]
    if len(sl_trades) > len(losses) * 0.6 and losses:
        patterns.append("Over 60% of losses are stop-loss hits — stops may be too tight.")
        improvements.append("Widen stop-loss or use ATR-based stops.")

    # Low R:R on wins
    low_rr_wins = [t for t in wins if t.risk_reward and t.risk_reward < 1.5]
    if low_rr_wins:
        patterns.append(
            f"{len(low_rr_wins)} winning trades had R:R below 1.5 — leaving money on the table."
        )
        improvements.append("Target higher risk-reward setups (>= 2.0).")

    summary = (
        f"Analysed {total} recent trades: {len(wins)} wins, {len(losses)} losses "
        f"({win_rate:.1f}% win rate)."
    )

    return PatternSummary(
        summary=summary,
        top_patterns=patterns,
        areas_to_improve=improvements,
    )


class EnhancedPatternSummary(BaseModel):
    summary: str
    performance_metrics: dict = {}
    patterns: list[dict] = []
    strengths: list[str] = []
    weaknesses: list[str] = []
    recommendations: list[dict] = []


@router.get("/journal/patterns/deep", response_model=EnhancedPatternSummary)
async def get_deep_patterns(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deep AI-powered pattern analysis from trade history (Sonnet)."""
    from app.advisor.pattern_analyzer import PatternAnalyzer
    from app.config import settings

    if settings.ai_pattern_analysis_enabled and claude_client.available:
        analyzer = PatternAnalyzer()
        result = await analyzer.analyze_deep(user_id, db)
        return EnhancedPatternSummary(**result)

    # Fallback to basic algorithmic analysis
    analyzer = PatternAnalyzer()
    result = analyzer._algorithmic_fallback(
        await _load_recent_trades(user_id, db),
    )
    return EnhancedPatternSummary(**result)


async def _load_recent_trades(user_id: str, db: AsyncSession) -> list:
    """Load recent closed trades for a user."""
    result = await db.execute(
        select(Trade)
        .where(Trade.user_id == user_id, Trade.pnl.is_not(None))
        .order_by(Trade.exit_time.desc())
        .limit(100)
    )
    return list(result.scalars().all())
