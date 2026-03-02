"""AI Investment Advisor API — scan, plan, deploy."""

import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.models.strategy import Strategy

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/advisor", tags=["advisor"])


# ---------- Schemas ----------


class ScanRequest(BaseModel):
    top_n: int = Field(default=100, ge=10, le=200)


class PlanRequest(BaseModel):
    amount: float = Field(default=10000, ge=100, le=10_000_000)
    risk_tolerance: str = Field(default="balanced")
    scan_results: list[dict] | None = None


class DeployRequest(BaseModel):
    plan: dict


class DeployResponse(BaseModel):
    strategy_id: str
    strategy_name: str
    symbols_count: int
    message: str


# ---------- Routes ----------


@router.post("/scan")
async def scan_market(
    body: ScanRequest | None = None,
    _user_id: str = Depends(get_current_user),
):
    """Scan Binance for all liquid crypto pairs and score them technically.

    Scans up to 100+ USDT pairs with >$1M daily volume.
    This may take 1-2 minutes as it fetches candles for each pair.
    """
    req = body or ScanRequest()

    from app.advisor.scanner import MarketScanner
    from app.advisor.analyzer import TechnicalAnalyzer

    scanner = MarketScanner("binance")
    analyzer = TechnicalAnalyzer()

    # Step 1: Get top pairs by volume
    top_pairs = scanner.scan_top_pairs(top_n=req.top_n)
    symbols = [p["symbol"] for p in top_pairs]

    # Build volume rank lookup
    volume_ranks = {p["symbol"]: p["rank"] for p in top_pairs}

    # Step 2: Fetch candles for technical analysis
    candles = scanner.fetch_candles_batch(symbols, timeframe="1h", limit=200)

    # Step 3: Score each crypto
    scored = analyzer.analyze_market(candles, volume_ranks=volume_ranks)

    # Merge 24h stats from ticker data
    ticker_lookup = {p["symbol"]: p for p in top_pairs}
    for s in scored:
        ticker = ticker_lookup.get(s["symbol"], {})
        s["volume_24h"] = ticker.get("volume_24h", 0)
        s["change_pct_24h"] = ticker.get("change_pct_24h", 0)

    return {
        "pairs_scanned": len(symbols),
        "pairs_scored": len(scored),
        "results": scored,
    }


@router.post("/plan")
async def generate_plan(
    body: PlanRequest,
    _user_id: str = Depends(get_current_user),
):
    """Generate an AI-powered investment plan based on scan results.

    If scan_results are not provided, runs a fresh scan first.
    """
    from app.advisor.planner import InvestmentPlanner

    scored = body.scan_results
    if not scored:
        # Run a fresh scan
        from app.advisor.scanner import MarketScanner
        from app.advisor.analyzer import TechnicalAnalyzer

        scanner = MarketScanner("binance")
        analyzer = TechnicalAnalyzer()
        top_pairs = scanner.scan_top_pairs(top_n=100)
        volume_ranks = {p["symbol"]: p["rank"] for p in top_pairs}
        candles = scanner.fetch_candles_batch(
            [p["symbol"] for p in top_pairs], timeframe="1h", limit=200,
        )
        scored = analyzer.analyze_market(candles, volume_ranks=volume_ranks)

    planner = InvestmentPlanner()
    plan = planner.generate_plan(scored, body.amount, body.risk_tolerance)
    return plan


@router.post("/deploy", response_model=DeployResponse)
async def deploy_plan(
    body: DeployRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deploy an investment plan — creates strategy, triggers backfill, activates."""
    plan = body.plan

    selected_cryptos = plan.get("selected_cryptos", [])
    if not selected_cryptos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plan has no selected cryptos",
        )

    risk_config = plan.get("risk_config", {})
    preset = plan.get("strategy_preset", "balanced_momentum")
    symbols = [c["symbol"] for c in selected_cryptos]

    # Determine timeframes from preset
    timeframe_map = {
        "conservative_swing": ["4h"],
        "balanced_momentum": ["1h"],
        "aggressive_scalper": ["1h", "4h"],
    }
    timeframes = timeframe_map.get(preset, ["1h"])

    # Build strategy config
    config = {
        "symbols": symbols,
        "timeframes": timeframes,
        "account_equity": risk_config.get("account_equity", 10000),
        "min_confluence": risk_config.get("min_confluence", 50),
        "max_risk_per_trade": risk_config.get("max_risk_per_trade", 0.02),
        "max_daily_loss": risk_config.get("max_daily_loss", 0.06),
        "atr_sl_multiplier": risk_config.get("atr_sl_multiplier", 2.0),
        "min_risk_reward": risk_config.get("min_risk_reward", 1.5),
    }

    # Deactivate any existing active strategies for this user
    uid = uuid.UUID(user_id)
    result = await db.execute(
        select(Strategy).where(Strategy.user_id == uid, Strategy.is_active == True)  # noqa: E712
    )
    for old_strat in result.scalars().all():
        old_strat.is_active = False

    # Create new strategy
    strategy_name = f"AI Advisor — {preset.replace('_', ' ').title()}"
    strategy = Strategy(
        user_id=uid,
        name=strategy_name,
        config=config,
        is_active=True,
    )
    db.add(strategy)
    await db.commit()
    await db.refresh(strategy)

    # Trigger candle backfill for all selected symbols
    try:
        from app.worker import celery_app
        celery_app.send_task("backfill_symbols", args=[symbols, timeframes])
        logger.info("Triggered backfill for %d symbols: %s", len(symbols), symbols)
    except Exception as e:
        logger.warning("Failed to trigger backfill task: %s", e)

    return DeployResponse(
        strategy_id=str(strategy.id),
        strategy_name=strategy_name,
        symbols_count=len(symbols),
        message=f"Strategy deployed with {len(symbols)} symbols! "
                f"Candle backfill started. Paper trading will begin within 5 minutes.",
    )
