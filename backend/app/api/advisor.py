"""AI Investment Advisor API — scan, plan, deploy.

The AI advisor is fully autonomous: it analyzes market conditions and
determines ALL optimal strategy parameters. No presets, no human risk
selection. The human provides investment amount and approves deployment.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models.strategy import Strategy

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/advisor", tags=["advisor"])


# ---------- Schemas ----------


class ScanRequest(BaseModel):
    top_n: int = Field(default=100, ge=10, le=200)


class PlanRequest(BaseModel):
    amount: float = Field(default=10000, ge=100, le=10_000_000)
    scan_results: list[dict] | None = None


class DeployRequest(BaseModel):
    plan: dict

    @field_validator('plan')
    @classmethod
    def validate_plan_structure(cls, v):
        required_keys = {'selected_cryptos', 'strategy_config'}
        missing = required_keys - set(v.keys())
        if missing:
            raise ValueError(f"Plan missing required keys: {missing}")
        if not isinstance(v.get('selected_cryptos'), list):
            raise ValueError("selected_cryptos must be a list")
        if not isinstance(v.get('strategy_config'), dict):
            raise ValueError("strategy_config must be a dict")
        return v


class DeployResponse(BaseModel):
    strategy_id: str
    strategy_name: str
    symbols_count: int
    message: str


# ---------- Routes ----------


@router.post("/scan")
@limiter.limit("3/minute")
async def scan_market(
    request: Request,
    body: ScanRequest | None = None,
    _user_id: str = Depends(get_current_user),
):
    """Scan Binance for all liquid crypto pairs and score them technically.

    Returns scored cryptos and a market profile for the AI advisor.
    """
    req = body or ScanRequest()

    from app.advisor.analyzer import TechnicalAnalyzer
    from app.advisor.scanner import MarketScanner

    # Step 0: Connect to Binance
    try:
        scanner = MarketScanner("binance")
    except Exception:
        logger.exception("Failed to initialize Binance connection")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Cannot connect to exchange. Please try again later.",
        )

    # Step 1: Get top pairs by volume
    try:
        top_pairs = scanner.scan_top_pairs(top_n=req.top_n)
    except Exception:
        logger.exception("Failed to scan Binance markets")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch market data. Please try again later.",
        )

    if not top_pairs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No liquid trading pairs found on Binance. Try again later.",
        )

    symbols = [p["symbol"] for p in top_pairs]
    volume_ranks = {p["symbol"]: p["rank"] for p in top_pairs}

    # Step 2: Fetch candles for technical analysis
    try:
        candles = scanner.fetch_candles_batch(symbols, timeframe="1h", limit=200)
    except Exception:
        logger.exception("Failed to fetch candle data")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch candle data. Please try again later.",
        )

    if not candles:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Fetched tickers but no candle data returned. Binance may be rate-limiting.",
        )

    # Step 3: Score each crypto
    try:
        analyzer = TechnicalAnalyzer()
        scored = analyzer.analyze_market(candles, volume_ranks=volume_ranks)
    except Exception:
        logger.exception("Technical analysis failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Technical analysis failed. Please try again later.",
        )

    # Merge 24h stats from ticker data
    ticker_lookup = {p["symbol"]: p for p in top_pairs}
    for s in scored:
        ticker = ticker_lookup.get(s["symbol"], {})
        s["volume_24h"] = ticker.get("volume_24h", 0)
        s["change_pct_24h"] = ticker.get("change_pct_24h", 0)

    # Step 4: Market profile (raw metrics for the AI advisor)
    market_profile = analyzer.compute_market_profile(scored)

    return {
        "pairs_scanned": len(symbols),
        "pairs_scored": len(scored),
        "results": scored,
        "market_profile": market_profile,
    }


@router.post("/plan")
@limiter.limit("5/minute")
async def generate_plan(
    request: Request,
    body: PlanRequest,
    _user_id: str = Depends(get_current_user),
):
    """Generate an AI-powered optimal strategy based on scan results.

    The AI advisor determines ALL parameters autonomously — no presets,
    no human risk selection. Just provide the investment amount.
    """
    from app.advisor.planner import InvestmentPlanner

    scored = body.scan_results
    market_profile = None
    if not scored:
        # Run a fresh scan
        from app.advisor.analyzer import TechnicalAnalyzer
        from app.advisor.scanner import MarketScanner

        try:
            scanner = MarketScanner("binance")
            analyzer = TechnicalAnalyzer()
            top_pairs = scanner.scan_top_pairs(top_n=100)
            volume_ranks = {p["symbol"]: p["rank"] for p in top_pairs}
            candles = scanner.fetch_candles_batch(
                [p["symbol"] for p in top_pairs], timeframe="1h", limit=200,
            )
            scored = analyzer.analyze_market(candles, volume_ranks=volume_ranks)
            market_profile = analyzer.compute_market_profile(scored)
        except Exception:
            logger.exception("Fresh scan for plan generation failed")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Market scan failed. Please try again later.",
            )

    try:
        planner = InvestmentPlanner()
        plan = planner.generate_plan(scored, body.amount, market_profile)
    except Exception:
        logger.exception("Plan generation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Plan generation failed. Please try again later.",
        )

    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI advisor is currently unavailable. The system cannot generate "
                   "investment plans without AI analysis. Please try again later.",
        )

    return plan


@router.post("/deploy", response_model=DeployResponse)
@limiter.limit("5/minute")
async def deploy_plan(
    request: Request,
    body: DeployRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deploy an AI-generated plan — creates strategy, triggers backfill, activates.

    Takes the AI's complete strategy_config directly. No preset lookup needed.
    """
    plan = body.plan

    selected_cryptos = plan.get("selected_cryptos", [])
    if not selected_cryptos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plan has no selected cryptos",
        )

    # Get the AI's full strategy config
    strategy_config = plan.get("strategy_config", plan.get("risk_config", {}))
    symbols_candidate = [c["symbol"] for c in selected_cryptos]
    timeframes = strategy_config.get("timeframes", ["1h"])

    # ------------------------------------------------------------------
    # Quality gate: only deploy symbols that show a non-chaotic regime
    # and minimum confluence — same bar as universe_discovery promotion.
    # This prevents symbols that will never trade from polluting the watchlist.
    # ------------------------------------------------------------------
    import pandas as pd

    from app.config import settings as _settings
    from app.data.storage import CandleStorage
    from app.engine.pipeline import SignalPipeline

    primary_timeframe = timeframes[0]
    min_candles_needed = _settings.universe_promotion_lookback_candles

    pipeline = SignalPipeline(
        min_confluence=strategy_config.get("min_confluence", 50),
    )

    quality_passed: list[str] = []
    quality_rejected: list[tuple[str, str]] = []

    for sym in symbols_candidate:
        try:
            candles_data = await CandleStorage.load_candles_db(
                db, sym, primary_timeframe, limit=min_candles_needed,
            )
            if len(candles_data) < 100:
                quality_rejected.append((sym, f"only {len(candles_data)} candles"))
                logger.info(
                    "deploy quality gate: %s rejected — only %d candles",
                    sym, len(candles_data),
                )
                continue
            df = pd.DataFrame(candles_data)
            result = pipeline.process(sym, primary_timeframe, df)
            # AI-deploy gate: only block chaotic regime — the market is too noisy for
            # any reliable signal. Low confluence in a trending regime is fine; it means
            # no trigger has fired yet, not that the symbol is permanently worthless.
            if result.regime == "chaotic":
                quality_rejected.append((sym, "chaotic_regime"))
                logger.info("deploy quality gate: %s rejected — chaotic regime", sym)
                continue
            logger.info(
                "deploy quality gate: %s passed (regime=%s, confluence=%d)",
                sym, result.regime, result.confluence_score,
            )
            quality_passed.append(sym)
        except Exception:
            logger.warning(
                "deploy quality gate: check failed for %s — including anyway",
                sym, exc_info=True,
            )
            quality_passed.append(sym)

    if len(quality_passed) >= 3:
        symbols = quality_passed
        logger.info(
            "deploy quality gate: %d/%d symbols passed: %s | rejected: %s",
            len(quality_passed), len(symbols_candidate), quality_passed, quality_rejected,
        )
    else:
        # Too few passed — deploy all candidates rather than an empty strategy
        symbols = symbols_candidate
        logger.warning(
            "deploy quality gate: only %d/%d passed — deploying all %d to avoid empty strategy",
            len(quality_passed), len(symbols_candidate), len(symbols_candidate),
        )

    # Build the final config — AI's config is used directly
    from app.api.strategies import StrategyConfig

    config = {
        "symbols": symbols,
        "timeframes": timeframes,
        **strategy_config,
    }
    config["symbols"] = symbols
    # Record source for every deployed symbol so the watchlist API never needs
    # to infer it from Redis state (which can misclassify ai_deploy as universe_discovery).
    config["symbol_sources"] = {sym: "ai_deploy" for sym in symbols}

    # Validate through Pydantic model (fills in defaults for any missing fields)
    try:
        validated = StrategyConfig(**config)
        config = validated.model_dump()
        # Pydantic may drop unknown keys — restore symbol_sources
        config["symbol_sources"] = {sym: "ai_deploy" for sym in symbols}
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Invalid strategy configuration: {e}")
    except Exception:
        logger.exception("Unexpected error validating strategy config")
        raise HTTPException(status_code=422, detail="Invalid strategy configuration")

    uid = uuid.UUID(user_id)

    # Deactivate any previously active strategies before creating the new one
    from sqlalchemy import update as sa_update

    await db.execute(
        sa_update(Strategy).where(Strategy.is_active == True).values(is_active=False)  # noqa: E712
    )

    # Create new strategy
    strategy_name = "AI Advisor — Optimal"
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

    rejected_note = (
        f" ({len(quality_rejected)} symbol(s) filtered by quality gate)"
        if quality_rejected else ""
    )
    return DeployResponse(
        strategy_id=str(strategy.id),
        strategy_name=strategy_name,
        symbols_count=len(symbols),
        message=f"Optimal strategy deployed with {len(symbols)} symbols{rejected_note}! "
                f"Candle backfill started. Paper trading will begin within 5 minutes.",
    )
