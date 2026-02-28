# Phase 5 — Advanced Features Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add HMM regime detection, AI-powered trade journal, walk-forward UI, analytics dashboard, correlation checks, and email alerts — the intelligence layer that elevates SignalForge from a basic trading tool to a professional-grade platform.

**Architecture:** HMM model stored as pickle in Redis, retrained weekly via Celery task. Claude Haiku for journal AI analysis. Resend for email alerts. Analytics page with equity curve + risk-adjusted metrics. Sortino/Calmar added to backtest engine. Walk-forward visualization in Backtest Lab. Correlation matrix via pandas on price data.

**Tech Stack:** hmmlearn (HMM), anthropic SDK (Claude Haiku), resend (email), existing lightweight-charts (equity curves), pandas correlation, Celery periodic tasks.

---

## Existing Code Inventory

### Backend
- `engine/layers/regime.py` — Layer 0 RegimeDetector: ADX + ATR percentile → Regime enum (TRENDING, RANGING, TRANSITIONING, CHAOTIC)
- `engine/pipeline.py` — SignalPipeline: 6-layer orchestrator, CHAOTIC blocks all trades
- `backtest/engine.py` — BacktestEngine: full pipeline simulation, metrics: win_rate, profit_factor, total_return, max_drawdown, sharpe_ratio, avg_risk_reward
- `backtest/optimizer.py` — WalkForwardOptimizer: grid search with k-fold train/test, WFOResult with fold_results
- `models/trade.py` — Trade model: pnl, pnl_pct, risk_reward, confluence_score, exit_reason, metadata_json
- `config.py` — Settings with env_prefix=SF_, .env file
- `api/backtests.py` — POST /backtests (sync), GET /backtests (stub)
- `tasks/backtest_task.py` — Celery task wrapper for backtests

### Frontend
- `pages/Journal.tsx` — Placeholder with 3 planned features (AI Pattern, Annotations, NL Queries)
- `pages/Backtest.tsx` — Form + results display, no walk-forward UI
- `pages/Dashboard.tsx` — StatsCards, PriceChart, SignalFeed, PositionsTable, RegimeWidget
- `hooks/useBacktest.ts` — useRunBacktest() mutation
- `components/backtest/BacktestResults.tsx` — Metrics grid display

---

## Task 1: Sortino + Calmar Metrics in Backtest Engine

**Files:**
- Modify: `backend/app/backtest/engine.py:179-232`
- Test: `backend/tests/test_backtest_metrics.py`

**Step 1: Write the test**

```python
# tests/test_backtest_metrics.py
from app.backtest.engine import BacktestEngine

def test_sortino_ratio_calculated():
    """Sortino uses only downside deviation, should differ from Sharpe."""
    engine = BacktestEngine(lookback=50)
    import pandas as pd, numpy as np
    np.random.seed(42)
    n = 300
    dates = pd.date_range("2024-01-01", periods=n, freq="1h")
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    df = pd.DataFrame({
        "open": close + np.random.randn(n) * 0.1,
        "high": close + abs(np.random.randn(n) * 0.3),
        "low": close - abs(np.random.randn(n) * 0.3),
        "close": close,
        "volume": np.random.randint(100, 10000, n).astype(float),
    }, index=dates)
    result = engine.run(df, "TEST/USD", "1h")
    assert "sortino_ratio" in result.metrics
    assert "calmar_ratio" in result.metrics
    assert isinstance(result.metrics["sortino_ratio"], float)
    assert isinstance(result.metrics["calmar_ratio"], float)
```

**Step 2: Run test to verify it fails**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_backtest_metrics.py -v`
Expected: FAIL — `sortino_ratio` not in metrics.

**Step 3: Add Sortino and Calmar to _calculate_metrics**

In `backend/app/backtest/engine.py`, add to the metrics dict returned by `_calculate_metrics()`:

```python
def _sortino(self, equity_curve: list[float]) -> float:
    eq = np.array(equity_curve)
    returns = np.diff(eq) / eq[:-1]
    if len(returns) == 0:
        return 0.0
    downside = returns[returns < 0]
    if len(downside) == 0 or np.std(downside) == 0:
        return 0.0
    return float(np.mean(returns) / np.std(downside) * np.sqrt(252))

def _calmar(self, equity_curve: list[float], initial_capital: float) -> float:
    if not equity_curve or equity_curve[-1] == initial_capital:
        return 0.0
    total_return = (equity_curve[-1] - initial_capital) / initial_capital * 100
    peak = equity_curve[0]
    max_dd = 0.0
    for val in equity_curve:
        if val > peak:
            peak = val
        dd = (peak - val) / peak * 100 if peak > 0 else 0
        max_dd = max(max_dd, dd)
    return total_return / max_dd if max_dd > 0 else 0.0
```

Add `"sortino_ratio"` and `"calmar_ratio"` keys to the metrics dict.

**Step 4: Run test**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_backtest_metrics.py -v`
Expected: PASS.

**Step 5: Run all backend tests**

Run: `cd backend && .venv/Scripts/python.exe -m pytest -q`
Expected: 184+ tests pass.

**Step 6: Commit**

```bash
git add backend/app/backtest/engine.py backend/tests/test_backtest_metrics.py
git commit -m "feat(backend): add Sortino and Calmar ratios to backtest metrics"
```

---

## Task 2: HMM Regime Detection

**Files:**
- Create: `backend/app/engine/layers/hmm_regime.py`
- Modify: `backend/app/engine/layers/regime.py` — add HMM integration
- Create: `backend/app/tasks/hmm_train.py` — Celery periodic training task
- Test: `backend/tests/test_hmm_regime.py`

**Step 1: Install hmmlearn**

Add `hmmlearn>=0.3.0` to `pyproject.toml` dependencies.

Run: `cd backend && pip install hmmlearn`

**Step 2: Write HMM regime test**

```python
# tests/test_hmm_regime.py
import numpy as np
import pandas as pd
from app.engine.layers.hmm_regime import HMMRegimeModel

def test_hmm_fit_and_predict():
    """HMM model should fit on features and predict regime states."""
    np.random.seed(42)
    n = 500
    dates = pd.date_range("2024-01-01", periods=n, freq="1h")
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    df = pd.DataFrame({
        "open": close + np.random.randn(n) * 0.1,
        "high": close + abs(np.random.randn(n) * 0.3),
        "low": close - abs(np.random.randn(n) * 0.3),
        "close": close,
        "volume": np.random.randint(100, 10000, n).astype(float),
    }, index=dates)
    model = HMMRegimeModel(n_states=3)
    model.fit(df)
    regime = model.predict_current(df)
    assert regime in ("low_vol", "trending", "high_vol")

def test_hmm_state_probabilities():
    """HMM should return state probabilities for current bar."""
    np.random.seed(42)
    n = 500
    dates = pd.date_range("2024-01-01", periods=n, freq="1h")
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    df = pd.DataFrame({
        "open": close + np.random.randn(n) * 0.1,
        "high": close + abs(np.random.randn(n) * 0.3),
        "low": close - abs(np.random.randn(n) * 0.3),
        "close": close,
        "volume": np.random.randint(100, 10000, n).astype(float),
    }, index=dates)
    model = HMMRegimeModel(n_states=3)
    model.fit(df)
    probs = model.state_probabilities(df)
    assert len(probs) == 3
    assert abs(sum(probs.values()) - 1.0) < 0.01
```

**Step 3: Implement HMMRegimeModel**

```python
# backend/app/engine/layers/hmm_regime.py
"""HMM-based regime detection using Gaussian Hidden Markov Model."""

import pickle

import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM

from app.engine.indicators import compute_atr, compute_adx


class HMMRegimeModel:
    """3-state HMM for market regime classification."""

    STATE_LABELS = {0: "low_vol", 1: "trending", 2: "high_vol"}

    def __init__(self, n_states: int = 3):
        self.n_states = n_states
        self.model: GaussianHMM | None = None
        self._state_map: dict[int, str] = {}

    def _extract_features(self, candles: pd.DataFrame) -> np.ndarray:
        """Extract features: log returns, ATR/price ratio, ADX."""
        close = candles["close"].values
        log_returns = np.diff(np.log(close))

        atr = compute_atr(candles, period=14).values
        adx = compute_adx(candles, period=14).values

        # Align lengths (drop NaN leading values)
        min_len = min(len(log_returns), len(atr[~np.isnan(atr)]), len(adx[~np.isnan(adx)]))
        lr = log_returns[-min_len:]
        atr_ratio = (atr[-min_len:] / close[-min_len:])
        adx_vals = adx[-min_len:]

        # Replace NaN with 0
        atr_ratio = np.nan_to_num(atr_ratio, 0.0)
        adx_vals = np.nan_to_num(adx_vals, 0.0)

        return np.column_stack([lr, atr_ratio, adx_vals])

    def fit(self, candles: pd.DataFrame) -> None:
        """Train the HMM on historical candle data."""
        features = self._extract_features(candles)
        self.model = GaussianHMM(
            n_components=self.n_states,
            covariance_type="full",
            n_iter=100,
            random_state=42,
        )
        self.model.fit(features)
        # Map states to labels by mean ATR ratio (feature index 1)
        means = self.model.means_[:, 1]  # ATR ratio means
        sorted_states = np.argsort(means)
        self._state_map = {
            int(sorted_states[0]): "low_vol",
            int(sorted_states[1]): "trending",
            int(sorted_states[2]): "high_vol",
        }

    def predict_current(self, candles: pd.DataFrame) -> str:
        """Predict regime for the most recent bar."""
        if self.model is None:
            return "trending"  # fallback
        features = self._extract_features(candles)
        states = self.model.predict(features)
        return self._state_map.get(int(states[-1]), "trending")

    def state_probabilities(self, candles: pd.DataFrame) -> dict[str, float]:
        """Get probability distribution over states for current bar."""
        if self.model is None:
            return {"low_vol": 0.33, "trending": 0.34, "high_vol": 0.33}
        features = self._extract_features(candles)
        probs = self.model.predict_proba(features)
        last_probs = probs[-1]
        return {
            self._state_map.get(i, f"state_{i}"): float(last_probs[i])
            for i in range(self.n_states)
        }

    def serialize(self) -> bytes:
        return pickle.dumps({"model": self.model, "state_map": self._state_map})

    @classmethod
    def deserialize(cls, data: bytes) -> "HMMRegimeModel":
        obj = pickle.loads(data)
        instance = cls()
        instance.model = obj["model"]
        instance._state_map = obj["state_map"]
        return instance
```

**Step 4: Create Celery training task**

```python
# backend/app/tasks/hmm_train.py
"""Weekly HMM model retraining task."""

from app.engine.layers.hmm_regime import HMMRegimeModel
from app.worker import celery_app


@celery_app.task(name="train_hmm_regime")
def train_hmm_regime(symbol: str = "BTC/USDT", timeframe: str = "1h"):
    """Retrain HMM regime model on latest data and cache in Redis."""
    import pandas as pd, numpy as np

    # Generate synthetic data for now (real data comes from CCXT ingestion)
    np.random.seed(None)
    n = 2000
    dates = pd.date_range(end=pd.Timestamp.now(), periods=n, freq="1h")
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    df = pd.DataFrame({
        "open": close + np.random.randn(n) * 0.1,
        "high": close + abs(np.random.randn(n) * 0.3),
        "low": close - abs(np.random.randn(n) * 0.3),
        "close": close,
        "volume": np.random.randint(100, 10000, n).astype(float),
    }, index=dates)

    model = HMMRegimeModel(n_states=3)
    model.fit(df)

    # Cache serialized model in Redis
    import redis
    from app.config import settings
    r = redis.Redis.from_url(settings.redis_url)
    r.set(f"hmm_model:{symbol}:{timeframe}", model.serialize(), ex=7 * 86400)

    return {"status": "trained", "symbol": symbol, "timeframe": timeframe}
```

**Step 5: Run tests**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_hmm_regime.py -v`
Expected: PASS.

**Step 6: Commit**

```bash
git add backend/app/engine/layers/hmm_regime.py backend/app/tasks/hmm_train.py \
  backend/tests/test_hmm_regime.py backend/pyproject.toml
git commit -m "feat(backend): add HMM regime detection with weekly retraining"
```

---

## Task 3: Trade Journal AI — Backend

**Files:**
- Create: `backend/app/api/journal.py`
- Modify: `backend/app/config.py` — add anthropic_api_key
- Modify: `backend/app/main.py` — register journal router
- Test: `backend/tests/test_journal_api.py`

**Step 1: Install anthropic SDK**

Add `anthropic>=0.52.0` to `pyproject.toml` dependencies.

Run: `cd backend && pip install anthropic`

**Step 2: Write test**

```python
# tests/test_journal_api.py
from unittest.mock import AsyncMock, patch
from app.api.journal import _build_trade_prompt

def test_build_trade_prompt_includes_trade_data():
    """Prompt should contain trade symbol, direction, and P&L."""
    trade_data = {
        "symbol": "BTC/USDT",
        "direction": "BUY",
        "entry_price": 50000,
        "exit_price": 51000,
        "pnl": 200,
        "confluence_score": 72,
        "exit_reason": "take_profit",
    }
    prompt = _build_trade_prompt(trade_data)
    assert "BTC/USDT" in prompt
    assert "BUY" in prompt
    assert "200" in prompt

def test_build_trade_prompt_handles_losing_trade():
    trade_data = {
        "symbol": "EUR/USD",
        "direction": "SELL",
        "entry_price": 1.0800,
        "exit_price": 1.0850,
        "pnl": -150,
        "confluence_score": 45,
        "exit_reason": "stop_loss",
    }
    prompt = _build_trade_prompt(trade_data)
    assert "stop_loss" in prompt
    assert "-150" in prompt
```

**Step 3: Implement journal API**

```python
# backend/app/api/journal.py
"""Trade Journal API — AI-powered trade analysis using Claude Haiku."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.config import settings
from app.core.database import get_db
from app.models.trade import Trade

router = APIRouter(prefix="/journal", tags=["journal"])


class AnalyzeRequest(BaseModel):
    trade_id: str
    additional_context: str | None = None


class AnalyzeResponse(BaseModel):
    trade_id: str
    analysis: str
    patterns: list[str]
    recommendations: list[str]


class PatternSummaryResponse(BaseModel):
    total_trades_analyzed: int
    summary: str
    top_patterns: list[str]
    areas_to_improve: list[str]


def _build_trade_prompt(trade_data: dict) -> str:
    """Build the analysis prompt for Claude Haiku."""
    return f"""Analyze this trading journal entry and provide actionable feedback.

Trade Details:
- Symbol: {trade_data.get('symbol', 'Unknown')}
- Direction: {trade_data.get('direction', 'Unknown')}
- Entry Price: {trade_data.get('entry_price', 'N/A')}
- Exit Price: {trade_data.get('exit_price', 'N/A')}
- P&L: {trade_data.get('pnl', 0)}
- Confluence Score: {trade_data.get('confluence_score', 'N/A')}
- Exit Reason: {trade_data.get('exit_reason', 'Unknown')}
- Risk/Reward: {trade_data.get('risk_reward', 'N/A')}

Provide:
1. A brief analysis of the trade quality (2-3 sentences)
2. Patterns identified (e.g., "entered on low confluence", "held through reversal")
3. Specific recommendations for improvement

Format your response as JSON:
{{"analysis": "...", "patterns": ["..."], "recommendations": ["..."]}}"""


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_trade(
    body: AnalyzeRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Analyze a single trade using Claude Haiku."""
    uid = uuid.UUID(user_id)
    result = await db.execute(
        select(Trade).where(Trade.id == uuid.UUID(body.trade_id), Trade.user_id == uid)
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

    if not settings.anthropic_api_key:
        # Fallback when no API key configured
        return AnalyzeResponse(
            trade_id=body.trade_id,
            analysis="AI analysis requires an Anthropic API key. Configure SF_ANTHROPIC_API_KEY in your environment.",
            patterns=[],
            recommendations=["Configure your Anthropic API key to enable AI trade analysis."],
        )

    import anthropic
    import json

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    prompt = _build_trade_prompt(trade_data)
    if body.additional_context:
        prompt += f"\n\nAdditional context from trader: {body.additional_context}"

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    response_text = message.content[0].text

    try:
        parsed = json.loads(response_text)
    except json.JSONDecodeError:
        parsed = {"analysis": response_text, "patterns": [], "recommendations": []}

    return AnalyzeResponse(
        trade_id=body.trade_id,
        analysis=parsed.get("analysis", response_text),
        patterns=parsed.get("patterns", []),
        recommendations=parsed.get("recommendations", []),
    )


@router.get("/patterns", response_model=PatternSummaryResponse)
async def get_pattern_summary(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregate pattern analysis across all trades."""
    uid = uuid.UUID(user_id)
    result = await db.execute(
        select(Trade).where(Trade.user_id == uid, Trade.pnl.isnot(None)).limit(50)
    )
    trades = result.scalars().all()

    if not trades:
        return PatternSummaryResponse(
            total_trades_analyzed=0,
            summary="No closed trades to analyze yet.",
            top_patterns=[],
            areas_to_improve=[],
        )

    wins = [t for t in trades if t.pnl and t.pnl > 0]
    losses = [t for t in trades if t.pnl and t.pnl <= 0]

    summary = f"Analyzed {len(trades)} trades: {len(wins)} wins, {len(losses)} losses."
    patterns = []
    improvements = []

    if losses:
        avg_loss_confluence = sum(t.confluence_score for t in losses) / len(losses)
        if avg_loss_confluence < 50:
            patterns.append("Losing trades have low average confluence scores")
            improvements.append("Consider raising minimum confluence threshold")

        sl_exits = [t for t in losses if t.exit_reason == "stop_loss"]
        if len(sl_exits) > len(losses) * 0.7:
            patterns.append("Most losses hit stop loss — stops may be too tight")
            improvements.append("Review ATR-based stop loss multiplier")

    if wins:
        avg_rr = sum(t.risk_reward for t in wins if t.risk_reward) / max(len([t for t in wins if t.risk_reward]), 1)
        if avg_rr < 1.5:
            patterns.append("Average R:R on wins is below 1.5")
            improvements.append("Consider wider take-profit targets")

    return PatternSummaryResponse(
        total_trades_analyzed=len(trades),
        summary=summary,
        top_patterns=patterns,
        areas_to_improve=improvements,
    )
```

**Step 4: Add config and register router**

Add to `config.py`:
```python
anthropic_api_key: str = ""
```

Add to `main.py`:
```python
from app.api.journal import router as journal_router
app.include_router(journal_router, prefix="/api")
```

**Step 5: Run tests**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_journal_api.py -v`
Expected: PASS.

**Step 6: Commit**

```bash
git add backend/app/api/journal.py backend/app/config.py backend/app/main.py \
  backend/tests/test_journal_api.py backend/pyproject.toml
git commit -m "feat(backend): add AI trade journal API with Claude Haiku analysis"
```

---

## Task 4: Email Alerts via Resend

**Files:**
- Create: `backend/app/core/email.py`
- Create: `backend/app/api/alerts.py`
- Modify: `backend/app/config.py` — add resend_api_key, alert_email
- Modify: `backend/app/main.py` — register alerts router
- Test: `backend/tests/test_alerts.py`

**Step 1: Install resend**

Add `resend>=2.0.0` to `pyproject.toml`.

Run: `cd backend && pip install resend`

**Step 2: Write test**

```python
# tests/test_alerts.py
from app.core.email import build_signal_email

def test_build_signal_email_html():
    """Email HTML should contain signal details."""
    html = build_signal_email(
        symbol="BTC/USDT",
        direction="BUY",
        confluence_score=78,
        entry_price=50000,
        stop_loss=49000,
        take_profit=52000,
    )
    assert "BTC/USDT" in html
    assert "BUY" in html
    assert "78" in html

def test_build_daily_summary_email():
    from app.core.email import build_daily_summary_email
    html = build_daily_summary_email(
        total_pnl=1250.50,
        trades_today=5,
        win_rate=60.0,
        open_positions=2,
    )
    assert "$1,250.50" in html
    assert "5" in html
```

**Step 3: Implement email module**

```python
# backend/app/core/email.py
"""Email sending via Resend."""

from app.config import settings


def build_signal_email(
    symbol: str, direction: str, confluence_score: int,
    entry_price: float, stop_loss: float, take_profit: float,
) -> str:
    color = "#00D68F" if direction == "BUY" else "#FF4D6A"
    return f"""
    <div style="font-family: Inter, sans-serif; max-width: 500px; margin: 0 auto;">
      <h2 style="color: {color};">🔔 New {direction} Signal — {symbol}</h2>
      <table style="width: 100%; border-collapse: collapse;">
        <tr><td style="padding: 8px; color: #8B8BA0;">Confluence</td><td style="padding: 8px; font-weight: bold;">{confluence_score}/100</td></tr>
        <tr><td style="padding: 8px; color: #8B8BA0;">Entry</td><td style="padding: 8px; font-family: monospace;">${entry_price:,.2f}</td></tr>
        <tr><td style="padding: 8px; color: #8B8BA0;">Stop Loss</td><td style="padding: 8px; font-family: monospace;">${stop_loss:,.2f}</td></tr>
        <tr><td style="padding: 8px; color: #8B8BA0;">Take Profit</td><td style="padding: 8px; font-family: monospace;">${take_profit:,.2f}</td></tr>
      </table>
      <p style="color: #8B8BA0; font-size: 12px; margin-top: 16px;">— SignalForge</p>
    </div>"""


def build_daily_summary_email(
    total_pnl: float, trades_today: int, win_rate: float, open_positions: int,
) -> str:
    pnl_color = "#00D68F" if total_pnl >= 0 else "#FF4D6A"
    return f"""
    <div style="font-family: Inter, sans-serif; max-width: 500px; margin: 0 auto;">
      <h2>📊 Daily Trading Summary</h2>
      <table style="width: 100%; border-collapse: collapse;">
        <tr><td style="padding: 8px; color: #8B8BA0;">P&L Today</td><td style="padding: 8px; color: {pnl_color}; font-weight: bold; font-family: monospace;">${total_pnl:,.2f}</td></tr>
        <tr><td style="padding: 8px; color: #8B8BA0;">Trades</td><td style="padding: 8px;">{trades_today}</td></tr>
        <tr><td style="padding: 8px; color: #8B8BA0;">Win Rate</td><td style="padding: 8px;">{win_rate:.1f}%</td></tr>
        <tr><td style="padding: 8px; color: #8B8BA0;">Open Positions</td><td style="padding: 8px;">{open_positions}</td></tr>
      </table>
      <p style="color: #8B8BA0; font-size: 12px; margin-top: 16px;">— SignalForge</p>
    </div>"""


async def send_email(to: str, subject: str, html: str) -> bool:
    """Send an email via Resend. Returns True on success."""
    if not settings.resend_api_key:
        return False
    import resend
    resend.api_key = settings.resend_api_key
    try:
        resend.Emails.send({
            "from": f"SignalForge <alerts@{settings.resend_domain}>",
            "to": [to],
            "subject": subject,
            "html": html,
        })
        return True
    except Exception:
        return False
```

**Step 4: Implement alerts API**

```python
# backend/app/api/alerts.py
"""Alert configuration and email notification endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/alerts", tags=["alerts"])

# In-memory alert config (single-user for now)
_alert_config: dict = {
    "email_on_signal": True,
    "email_daily_summary": True,
    "min_confluence_alert": 60,
    "alert_email": "",
}


class AlertConfig(BaseModel):
    email_on_signal: bool = True
    email_daily_summary: bool = True
    min_confluence_alert: int = 60
    alert_email: str = ""


@router.get("/config", response_model=AlertConfig)
async def get_alert_config(_user_id: str = Depends(get_current_user)):
    return AlertConfig(**_alert_config)


@router.put("/config", response_model=AlertConfig)
async def update_alert_config(
    body: AlertConfig,
    _user_id: str = Depends(get_current_user),
):
    _alert_config.update(body.model_dump())
    return AlertConfig(**_alert_config)
```

**Step 5: Add config keys and register router**

Add to `config.py`:
```python
resend_api_key: str = ""
resend_domain: str = "signalforge.dev"
```

Add to `main.py`:
```python
from app.api.alerts import router as alerts_router
app.include_router(alerts_router, prefix="/api")
```

**Step 6: Run tests**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_alerts.py -v`
Expected: PASS.

**Step 7: Commit**

```bash
git add backend/app/core/email.py backend/app/api/alerts.py backend/app/config.py \
  backend/app/main.py backend/tests/test_alerts.py backend/pyproject.toml
git commit -m "feat(backend): add email alerts via Resend with signal + daily summary"
```

---

## Task 5: Analytics + Correlation API

**Files:**
- Create: `backend/app/api/analytics.py`
- Modify: `backend/app/main.py` — register analytics router
- Test: `backend/tests/test_analytics.py`

**Step 1: Write test**

```python
# tests/test_analytics.py
from app.api.analytics import compute_correlation

def test_correlation_identical_series():
    """Identical price series should have correlation of 1.0."""
    import numpy as np
    prices_a = list(np.cumsum(np.random.randn(100)) + 100)
    corr = compute_correlation(prices_a, prices_a)
    assert abs(corr - 1.0) < 0.01

def test_correlation_inverse_series():
    """Inverse series should have correlation near -1.0."""
    import numpy as np
    prices_a = list(np.cumsum(np.random.randn(100)) + 100)
    prices_b = [200 - p for p in prices_a]
    corr = compute_correlation(prices_a, prices_b)
    assert corr < -0.9
```

**Step 2: Implement analytics API**

```python
# backend/app/api/analytics.py
"""Analytics endpoints — equity history, correlation, risk metrics."""

import uuid

import numpy as np
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.models.trade import Trade

router = APIRouter(prefix="/analytics", tags=["analytics"])


class EquityPoint(BaseModel):
    date: str
    equity: float
    drawdown_pct: float


class EquityHistoryResponse(BaseModel):
    points: list[EquityPoint]
    total_return_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float


class CorrelationResponse(BaseModel):
    symbol_a: str
    symbol_b: str
    correlation: float


def compute_correlation(prices_a: list[float], prices_b: list[float]) -> float:
    """Compute Pearson correlation between two price series."""
    a = np.array(prices_a)
    b = np.array(prices_b)
    min_len = min(len(a), len(b))
    a, b = a[-min_len:], b[-min_len:]
    if len(a) < 2:
        return 0.0
    ret_a = np.diff(a) / a[:-1]
    ret_b = np.diff(b) / b[:-1]
    if np.std(ret_a) == 0 or np.std(ret_b) == 0:
        return 0.0
    return float(np.corrcoef(ret_a, ret_b)[0, 1])


@router.get("/equity", response_model=EquityHistoryResponse)
async def equity_history(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    initial_equity: float = Query(default=10000),
):
    """Build equity curve from closed trade history."""
    uid = uuid.UUID(user_id)
    result = await db.execute(
        select(Trade)
        .where(Trade.user_id == uid, Trade.pnl.isnot(None))
        .order_by(Trade.exit_time.asc())
    )
    trades = result.scalars().all()

    if not trades:
        return EquityHistoryResponse(
            points=[], total_return_pct=0, max_drawdown_pct=0,
            sharpe_ratio=0, sortino_ratio=0, calmar_ratio=0,
        )

    equity = initial_equity
    peak = equity
    max_dd = 0.0
    points: list[EquityPoint] = []
    equities: list[float] = [equity]

    for t in trades:
        equity += t.pnl
        equities.append(equity)
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak * 100 if peak > 0 else 0
        max_dd = max(max_dd, dd)
        points.append(EquityPoint(
            date=t.exit_time.isoformat() if t.exit_time else t.created_at.isoformat(),
            equity=round(equity, 2),
            drawdown_pct=round(dd, 2),
        ))

    # Risk-adjusted metrics
    eq = np.array(equities)
    returns = np.diff(eq) / eq[:-1]
    sharpe = float(np.mean(returns) / np.std(returns) * np.sqrt(252)) if np.std(returns) > 0 else 0
    downside = returns[returns < 0]
    sortino = float(np.mean(returns) / np.std(downside) * np.sqrt(252)) if len(downside) > 0 and np.std(downside) > 0 else 0
    total_return = (equity - initial_equity) / initial_equity * 100
    calmar = total_return / max_dd if max_dd > 0 else 0

    return EquityHistoryResponse(
        points=points,
        total_return_pct=round(total_return, 2),
        max_drawdown_pct=round(max_dd, 2),
        sharpe_ratio=round(sharpe, 4),
        sortino_ratio=round(sortino, 4),
        calmar_ratio=round(calmar, 4),
    )


@router.get("/correlation", response_model=CorrelationResponse)
async def symbol_correlation(
    symbol_a: str = Query(...),
    symbol_b: str = Query(...),
):
    """Compute return correlation between two symbols (stub — uses synthetic data)."""
    # Real implementation will query candles from TimescaleDB
    rng = np.random.default_rng(hash(f"{symbol_a}{symbol_b}") % 2**32)
    prices_a = list(100 + np.cumsum(rng.standard_normal(200) * 0.5))
    prices_b = list(100 + np.cumsum(rng.standard_normal(200) * 0.5))
    corr = compute_correlation(prices_a, prices_b)
    return CorrelationResponse(
        symbol_a=symbol_a, symbol_b=symbol_b, correlation=round(corr, 4)
    )
```

**Step 3: Register router**

Add to `main.py`:
```python
from app.api.analytics import router as analytics_router
app.include_router(analytics_router, prefix="/api")
```

**Step 4: Run tests**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_analytics.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/api/analytics.py backend/app/main.py backend/tests/test_analytics.py
git commit -m "feat(backend): add analytics API with equity history and correlation"
```

---

## Task 6: Walk-Forward Optimization API

**Files:**
- Modify: `backend/app/api/backtests.py` — add WFO endpoint
- Test: `backend/tests/test_wfo_api.py`

**Step 1: Write test**

```python
# tests/test_wfo_api.py
from app.api.backtests import WFORequest

def test_wfo_request_defaults():
    req = WFORequest(symbol="BTC/USDT", timeframe="1h")
    assert req.n_folds == 3
    assert req.train_pct == 0.7
    assert len(req.param_grid) > 0
```

**Step 2: Add WFO endpoint to backtests.py**

Add to `backend/app/api/backtests.py`:

```python
class WFORequest(BaseModel):
    symbol: str
    timeframe: str
    days: int = Field(default=90, ge=30, le=365)
    n_folds: int = Field(default=3, ge=2, le=10)
    train_pct: float = Field(default=0.7, ge=0.5, le=0.9)
    param_grid: dict = Field(default={
        "atr_sl_multiplier": [1.5, 2.0, 2.5],
        "min_confluence": [40, 50, 60],
    })


@router.post("/backtests/optimize")
async def run_walk_forward(body: WFORequest):
    """Run walk-forward optimization."""
    from app.backtest.optimizer import WalkForwardOptimizer
    import pandas as pd, numpy as np

    np.random.seed(42)
    n = body.days * 24
    dates = pd.date_range(end=pd.Timestamp.now(), periods=n, freq="1h")
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    candles = pd.DataFrame({
        "open": close + np.random.randn(n) * 0.1,
        "high": close + abs(np.random.randn(n) * 0.3),
        "low": close - abs(np.random.randn(n) * 0.3),
        "close": close,
        "volume": np.random.randint(100, 10000, n).astype(float),
    }, index=dates)

    optimizer = WalkForwardOptimizer()
    result = optimizer.optimize(
        candles=candles,
        symbol=body.symbol,
        timeframe=body.timeframe,
        param_grid=body.param_grid,
        n_folds=body.n_folds,
        train_pct=body.train_pct,
    )

    # Sanitize inf/NaN
    def sanitize(v):
        if isinstance(v, float) and (np.isinf(v) or np.isnan(v)):
            return None
        return v

    def sanitize_dict(d):
        return {k: sanitize(v) for k, v in d.items()}

    return {
        "best_params": result.best_params,
        "out_of_sample_metrics": sanitize_dict(result.out_of_sample_metrics),
        "fold_results": [
            {**fr, "oos_metrics": sanitize_dict(fr["oos_metrics"])}
            for fr in result.fold_results
        ],
    }
```

**Step 3: Run test**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_wfo_api.py -v`
Expected: PASS.

**Step 4: Commit**

```bash
git add backend/app/api/backtests.py backend/tests/test_wfo_api.py
git commit -m "feat(backend): add walk-forward optimization API endpoint"
```

---

## Task 7: Trade Journal — Frontend

**Files:**
- Modify: `frontend/src/pages/Journal.tsx` — replace placeholder
- Create: `frontend/src/hooks/useJournal.ts`
- Test: `frontend/src/pages/__tests__/Journal.test.tsx` — update

**Step 1: Create journal hooks**

```typescript
// frontend/src/hooks/useJournal.ts
import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface AnalyzeResponse {
  trade_id: string;
  analysis: string;
  patterns: string[];
  recommendations: string[];
}

interface PatternSummary {
  total_trades_analyzed: number;
  summary: string;
  top_patterns: string[];
  areas_to_improve: string[];
}

export function useAnalyzeTrade() {
  return useMutation({
    mutationFn: (data: { trade_id: string; additional_context?: string }) =>
      api.post<AnalyzeResponse>("/journal/analyze", data),
  });
}

export function usePatternSummary() {
  return useQuery({
    queryKey: ["journal", "patterns"],
    queryFn: () => api.get<PatternSummary>("/journal/patterns"),
  });
}
```

**Step 2: Replace Journal page placeholder**

Replace `frontend/src/pages/Journal.tsx`:
- Pattern Summary card at top (from `usePatternSummary()`)
- Trade list with "Analyze" button on each trade (from `useTrades()`)
- Click "Analyze" → calls `useAnalyzeTrade()` mutation → shows AI analysis card
- Analysis card: analysis text, patterns as badges, recommendations as bullet list
- Keep the planned features section at bottom for features not yet built

**Step 3: Update test**

Update `frontend/src/pages/__tests__/Journal.test.tsx`:
```typescript
import { render, screen } from "@testing-library/react";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { JournalPage } from "../Journal";

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter>{children}</MemoryRouter>
  </QueryClientProvider>
);

describe("JournalPage", () => {
  test("renders page heading", () => {
    render(<JournalPage />, { wrapper });
    expect(screen.getByText("Trade Journal")).toBeInTheDocument();
  });
});
```

**Step 4: Run tests + lint + build**

Run:
```bash
cd frontend && npx vitest run
cd frontend && npm run lint
cd frontend && npm run build
```

**Step 5: Commit**

```bash
git add frontend/src/pages/Journal.tsx frontend/src/hooks/useJournal.ts \
  frontend/src/pages/__tests__/Journal.test.tsx
git commit -m "feat(frontend): implement Trade Journal with AI analysis"
```

---

## Task 8: Analytics Page — Frontend

**Files:**
- Create: `frontend/src/pages/Analytics.tsx`
- Create: `frontend/src/hooks/useAnalytics.ts`
- Create: `frontend/src/components/analytics/EquityCurve.tsx`
- Create: `frontend/src/components/analytics/MetricsGrid.tsx`
- Create: `frontend/src/components/analytics/CorrelationMatrix.tsx`
- Modify: `frontend/src/App.tsx` — add /analytics route
- Modify: `frontend/src/components/layout/Sidebar.tsx` — add Analytics nav item
- Test: `frontend/src/pages/__tests__/Analytics.test.tsx`

**Step 1: Create analytics hooks**

```typescript
// frontend/src/hooks/useAnalytics.ts
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface EquityPoint {
  date: string;
  equity: number;
  drawdown_pct: number;
}

interface EquityHistory {
  points: EquityPoint[];
  total_return_pct: number;
  max_drawdown_pct: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  calmar_ratio: number;
}

interface CorrelationResult {
  symbol_a: string;
  symbol_b: string;
  correlation: number;
}

export function useEquityHistory() {
  return useQuery({
    queryKey: ["analytics", "equity"],
    queryFn: () => api.get<EquityHistory>("/analytics/equity"),
  });
}

export function useCorrelation(symbolA: string, symbolB: string) {
  return useQuery({
    queryKey: ["analytics", "correlation", symbolA, symbolB],
    queryFn: () =>
      api.get<CorrelationResult>(`/analytics/correlation?symbol_a=${symbolA}&symbol_b=${symbolB}`),
    enabled: !!symbolA && !!symbolB && symbolA !== symbolB,
  });
}
```

**Step 2: Implement EquityCurve component**

`frontend/src/components/analytics/EquityCurve.tsx`:
- Uses `lightweight-charts` line series
- Shows equity over time with green line
- Drawdown area chart below (red fill)
- Responsive, dark theme matching

**Step 3: Implement MetricsGrid**

`frontend/src/components/analytics/MetricsGrid.tsx`:
- 6 metric cards: Total Return %, Max Drawdown %, Sharpe Ratio, Sortino Ratio, Calmar Ratio, Profit Factor
- Font-mono for values, colored positive/negative

**Step 4: Implement CorrelationMatrix**

`frontend/src/components/analytics/CorrelationMatrix.tsx`:
- Heatmap grid of symbol correlations
- Color: green (positive) to red (negative)
- Uses the 9 supported symbols
- Click cell shows detailed correlation value

**Step 5: Assemble Analytics page**

`frontend/src/pages/Analytics.tsx`:
- Header: "Performance Analytics"
- MetricsGrid at top
- EquityCurve (full width)
- CorrelationMatrix below
- Uses `useEquityHistory()` and `useCorrelation()` hooks

**Step 6: Wire into router + sidebar**

Update `App.tsx`: Add `<Route path="analytics" element={<AnalyticsPage />} />`
Update `Sidebar.tsx`: Add Analytics nav item (BarChart3 icon, /analytics)

**Step 7: Test**

```typescript
// frontend/src/pages/__tests__/Analytics.test.tsx
import { render, screen } from "@testing-library/react";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { AnalyticsPage } from "../Analytics";

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter>{children}</MemoryRouter>
  </QueryClientProvider>
);

describe("AnalyticsPage", () => {
  test("renders page heading", () => {
    render(<AnalyticsPage />, { wrapper });
    expect(screen.getByText("Performance Analytics")).toBeInTheDocument();
  });
});
```

**Step 8: Run tests + lint + build**

**Step 9: Commit**

```bash
git add frontend/src/pages/Analytics.tsx frontend/src/hooks/useAnalytics.ts \
  frontend/src/components/analytics/ frontend/src/App.tsx \
  frontend/src/components/layout/Sidebar.tsx frontend/src/pages/__tests__/Analytics.test.tsx
git commit -m "feat(frontend): add Analytics page with equity curve and correlation matrix"
```

---

## Task 9: Walk-Forward UI in Backtest Lab

**Files:**
- Create: `frontend/src/components/backtest/WalkForwardForm.tsx`
- Create: `frontend/src/components/backtest/WalkForwardResults.tsx`
- Create: `frontend/src/hooks/useWalkForward.ts`
- Modify: `frontend/src/pages/Backtest.tsx` — add WFO tab
- Test: `frontend/src/pages/__tests__/Backtest.test.tsx` — update

**Step 1: Create WFO hook**

```typescript
// frontend/src/hooks/useWalkForward.ts
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface WFORequest {
  symbol: string;
  timeframe: string;
  days: number;
  n_folds: number;
  train_pct: number;
  param_grid: Record<string, number[]>;
}

interface WFOResult {
  best_params: Record<string, number>;
  out_of_sample_metrics: Record<string, number | null>;
  fold_results: Array<{
    fold: number;
    params: Record<string, number>;
    oos_metrics: Record<string, number | null>;
    oos_score: number;
  }>;
}

export function useRunWalkForward() {
  return useMutation({
    mutationFn: (req: WFORequest) => api.post<WFOResult>("/backtests/optimize", req),
  });
}
```

**Step 2: Implement WFO form + results**

`WalkForwardForm.tsx`: Same symbol/TF as backtest form + n_folds slider (2-10), train_pct slider (50-90%), param grid editor.

`WalkForwardResults.tsx`: Best params card, fold results table (fold #, score, metrics), out-of-sample summary.

**Step 3: Add tab toggle to Backtest page**

Modify `frontend/src/pages/Backtest.tsx`:
- Two tabs at top: "Standard Backtest" | "Walk-Forward Optimization"
- Tab 1: existing BacktestForm + BacktestResults
- Tab 2: WalkForwardForm + WalkForwardResults

**Step 4: Run tests + lint + build**

**Step 5: Commit**

```bash
git add frontend/src/components/backtest/WalkForwardForm.tsx \
  frontend/src/components/backtest/WalkForwardResults.tsx \
  frontend/src/hooks/useWalkForward.ts frontend/src/pages/Backtest.tsx \
  frontend/src/pages/__tests__/Backtest.test.tsx
git commit -m "feat(frontend): add Walk-Forward Optimization UI to Backtest Lab"
```

---

## Task 10: Final Integration + Lint + Build

**Files:**
- All modified files from Tasks 7-9

**Step 1: Run all frontend tests**

Run: `cd frontend && npx vitest run`
Expected: All tests pass.

**Step 2: Run lint**

Run: `cd frontend && npm run lint`
Expected: 0 errors.

**Step 3: Run all backend tests**

Run: `cd backend && .venv/Scripts/python.exe -m pytest -q`
Expected: All tests pass.

**Step 4: Run backend lint**

Run: `cd backend && .venv/Scripts/python.exe -m ruff check .`
Expected: 0 errors.

**Step 5: Build frontend**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

**Step 6: Final commit**

```bash
git add -A
git commit -m "feat: Phase 5 complete — HMM regime, AI journal, analytics, WFO UI, alerts"
```

---

## Agent Team Structure

### Wave 1: Backend Features (parallel)
- **@ml-engineer** (Tasks 1-2): Sortino/Calmar metrics + HMM regime detection
- **@api-builder** (Tasks 3-6): Trade Journal AI + Email Alerts + Analytics API + WFO endpoint

### Wave 2: Frontend Features (parallel, depends on Wave 1)
- **@frontend-journal** (Tasks 7, 9): Journal page + Walk-Forward UI
- **@frontend-analytics** (Task 8): Analytics page with equity curve + correlation

### Wave 3: Integration (depends on Wave 2)
- **Task 10**: Final integration on main (done by orchestrator, not agent)

### Merge Order
1. Merge @ml-engineer → main
2. Merge @api-builder → main (may need conflict resolution in main.py, config.py)
3. Merge @frontend-journal and @frontend-analytics → main (may conflict in App.tsx, Sidebar.tsx)
4. Run full test suite + lint + build
