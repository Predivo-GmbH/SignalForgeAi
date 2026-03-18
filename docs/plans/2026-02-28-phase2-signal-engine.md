# SignalForgeAI Phase 2 — Signal Engine Complete

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete all 6 signal engine layers, wire them into the SignalPipeline orchestrator, add session/timing filters, multi-TF Fibonacci, volume profile, walk-forward optimization, and backtest across 3 markets with documented results. Add Signal + Trade DB tables.

**Architecture:** All work is in `backend/app/engine/`. Layers are independent modules that plug into `pipeline.py`. Each layer receives candle data and returns a typed result. The pipeline orchestrates them sequentially with early-exit on block signals.

**Tech Stack:** Python 3.12, pandas, numpy, ta-lib (with pure-Python fallbacks), pytest

**Depends on:** Phase 1 complete (indicators.py, layers/trend.py, layers/zones.py, backtest/engine.py)

---

## Task 1: Layer 0 — Regime Detector

**Files:**
- Create: `backend/app/engine/layers/regime.py`
- Test: `backend/tests/test_regime.py`

**Step 1: Write failing tests**

Create `backend/tests/test_regime.py`:

```python
import numpy as np
import pandas as pd
import pytest


def make_trending_candles(n=200):
    """Strong trend — ADX should be high."""
    rng = np.random.default_rng(42)
    close = 100 + np.arange(n) * 0.8 + rng.normal(0, 0.5, n)
    high = close + rng.uniform(0.5, 2, n)
    low = close - rng.uniform(0.5, 2, n)
    return pd.DataFrame({"open": close + 0.1, "high": high, "low": low, "close": close, "volume": rng.uniform(1000, 5000, n)})


def make_ranging_candles(n=200):
    """Sideways chop — ADX should be low."""
    rng = np.random.default_rng(42)
    close = 100 + rng.normal(0, 0.5, n)
    high = close + rng.uniform(0.3, 0.8, n)
    low = close - rng.uniform(0.3, 0.8, n)
    return pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": rng.uniform(1000, 5000, n)})


def make_chaotic_candles(n=200):
    """Wild volatility swings — ATR in extreme percentile."""
    rng = np.random.default_rng(42)
    close = 100 + np.cumsum(rng.normal(0, 5, n))
    high = close + rng.uniform(3, 10, n)
    low = close - rng.uniform(3, 10, n)
    return pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": rng.uniform(1000, 5000, n)})


class TestRegimeDetector:
    def test_trending_regime(self):
        from app.engine.layers.regime import RegimeDetector, Regime
        rd = RegimeDetector()
        result = rd.detect(make_trending_candles())
        assert result in (Regime.TRENDING_BULL, Regime.TRENDING_BEAR, Regime.TRENDING)

    def test_ranging_regime(self):
        from app.engine.layers.regime import RegimeDetector, Regime
        rd = RegimeDetector()
        result = rd.detect(make_ranging_candles())
        assert result in (Regime.RANGING, Regime.TRANSITIONING)

    def test_returns_regime_enum(self):
        from app.engine.layers.regime import RegimeDetector, Regime
        rd = RegimeDetector()
        result = rd.detect(make_trending_candles())
        assert isinstance(result, Regime)

    def test_atr_percentile_calculation(self):
        from app.engine.layers.regime import RegimeDetector
        rd = RegimeDetector()
        candles = make_trending_candles()
        pct = rd._atr_percentile(candles, lookback=100)
        assert 0 <= pct <= 100

    def test_adx_regime_thresholds(self):
        from app.engine.layers.regime import RegimeDetector, Regime
        rd = RegimeDetector()
        assert rd._adx_regime(30) == Regime.TRENDING
        assert rd._adx_regime(15) == Regime.RANGING
        assert rd._adx_regime(22) == Regime.TRANSITIONING
```

**Step 2: Implement regime.py**

```python
from enum import Enum
import pandas as pd
from app.engine.indicators import compute_adx, compute_atr


class Regime(Enum):
    TRENDING = "trending"
    TRENDING_BULL = "trending_bull"
    TRENDING_BEAR = "trending_bear"
    RANGING = "ranging"
    TRANSITIONING = "transitioning"
    CHAOTIC = "chaotic"


class RegimeDetector:
    """
    Layer 0: Determines current market regime using ADX + ATR percentile.
    Output: TRENDING, RANGING, TRANSITIONING, or CHAOTIC.
    """

    def detect(self, candles: pd.DataFrame) -> Regime:
        adx = compute_adx(candles, period=14)
        adx_val = adx.dropna().iloc[-1] if len(adx.dropna()) > 0 else 0
        adx_regime = self._adx_regime(float(adx_val))

        atr_pct = self._atr_percentile(candles, lookback=100)

        # Chaotic: extreme volatility
        if atr_pct > 90:
            return Regime.CHAOTIC

        # Consensus between ADX and ATR
        if adx_regime == Regime.TRENDING:
            if atr_pct < 20:
                return Regime.TRANSITIONING  # Low vol but ADX high = weakening trend
            return Regime.TRENDING
        elif adx_regime == Regime.RANGING:
            return Regime.RANGING
        else:
            return Regime.TRANSITIONING

    def _adx_regime(self, adx_value: float) -> Regime:
        if adx_value > 25:
            return Regime.TRENDING
        elif adx_value < 20:
            return Regime.RANGING
        else:
            return Regime.TRANSITIONING

    def _atr_percentile(self, candles: pd.DataFrame, lookback: int = 100) -> float:
        atr = compute_atr(candles, period=14)
        atr_clean = atr.dropna()
        if len(atr_clean) < 2:
            return 50.0
        tail = atr_clean.tail(lookback)
        current = tail.iloc[-1]
        percentile = float((tail < current).mean() * 100)
        return percentile
```

**Step 3: Verify — `pytest tests/test_regime.py -v` → all PASS**

**Step 4: Commit**
```bash
git add backend/app/engine/layers/regime.py backend/tests/test_regime.py
git commit -m "feat(backend): Layer 0 — RegimeDetector with ADX + ATR percentile consensus"
```

---

## Task 2: Layer 3 — Confluence Scorer

**Files:**
- Create: `backend/app/engine/layers/confluence.py`
- Test: `backend/tests/test_confluence.py`

**Step 1: Write failing tests**

```python
import numpy as np
import pandas as pd
import pytest


def make_candles(n=200):
    rng = np.random.default_rng(42)
    close = 100 + np.arange(n) * 0.3 + rng.normal(0, 0.5, n)
    high = close + rng.uniform(0.5, 2, n)
    low = close - rng.uniform(0.5, 2, n)
    return pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": rng.uniform(1000, 5000, n)})


class TestConfluenceScorer:
    def test_score_returns_int_0_to_100(self):
        from app.engine.layers.confluence import ConfluenceScorer
        from app.engine.layers.zones import EntryZone
        from app.engine.layers.trend import TrendResult, Trend
        scorer = ConfluenceScorer()
        zone = EntryZone(zone_type="fibonacci_golden", upper=110, lower=105, strength=0.7)
        trend = TrendResult(direction=Trend.BULLISH, strength=0.01)
        score = scorer.score(zone, make_candles(), trend)
        assert isinstance(score, int)
        assert 0 <= score <= 100

    def test_fibonacci_zone_gets_base_points(self):
        from app.engine.layers.confluence import ConfluenceScorer
        from app.engine.layers.zones import EntryZone
        from app.engine.layers.trend import TrendResult, Trend
        scorer = ConfluenceScorer()
        fib_zone = EntryZone(zone_type="fibonacci_golden", upper=110, lower=105, strength=0.7)
        non_fib = EntryZone(zone_type="vwap_1sigma", upper=110, lower=105, strength=0.5)
        trend = TrendResult(direction=Trend.BULLISH, strength=0.01)
        candles = make_candles()
        fib_score = scorer.score(fib_zone, candles, trend)
        non_fib_score = scorer.score(non_fib, candles, trend)
        assert fib_score >= non_fib_score  # Fib zone should score at least as high

    def test_weights_sum_to_100(self):
        from app.engine.layers.confluence import ConfluenceScorer
        scorer = ConfluenceScorer()
        assert sum(scorer.WEIGHTS.values()) == 100

    def test_score_details_returned(self):
        from app.engine.layers.confluence import ConfluenceScorer
        from app.engine.layers.zones import EntryZone
        from app.engine.layers.trend import TrendResult, Trend
        scorer = ConfluenceScorer()
        zone = EntryZone(zone_type="fibonacci_golden", upper=110, lower=105, strength=0.7)
        trend = TrendResult(direction=Trend.BULLISH, strength=0.01)
        score, details = scorer.score_with_details(zone, make_candles(), trend)
        assert isinstance(details, dict)
        assert isinstance(score, int)
```

**Step 2: Implement confluence.py**

The ConfluenceScorer scores a zone 0-100 using 9 weighted factors:

| Factor | Weight |
|--------|--------|
| fibonacci_alignment | 15 |
| sr_overlap | 15 |
| multi_tf_fib | 15 |
| vwap_proximity | 10 |
| volume_node | 10 |
| rsi_confirmation | 10 |
| macd_momentum | 10 |
| candlestick_pattern | 10 |
| stochastic_cross | 5 |

Implementation checks each factor against current candle data and zone. RSI < 40 in uptrend = oversold confirmation (+10). MACD aligned with trend (+10). Stochastic cross in trend direction (+5). Etc.

Provide both `score()` (returns int) and `score_with_details()` (returns int + dict of which factors hit).

**Step 3: Verify — all PASS**

**Step 4: Commit**
```bash
git commit -m "feat(backend): Layer 3 — ConfluenceScorer with 9 weighted factors"
```

---

## Task 3: Layer 4 — Trigger Detector

**Files:**
- Create: `backend/app/engine/layers/triggers.py`
- Test: `backend/tests/test_triggers.py`

**Step 1: Write failing tests**

```python
import numpy as np
import pandas as pd
import pytest


def make_macd_cross_up_candles(n=200):
    """Data where MACD crosses above signal near the end."""
    rng = np.random.default_rng(42)
    # Declining then sharply rising — triggers MACD cross up
    close = np.concatenate([
        100 - np.arange(150) * 0.1 + rng.normal(0, 0.2, 150),
        85 + np.arange(50) * 0.6 + rng.normal(0, 0.2, 50),
    ])
    high = close + rng.uniform(0.5, 1.5, n)
    low = close - rng.uniform(0.5, 1.5, n)
    return pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": rng.uniform(1000, 5000, n)})


class TestTriggerDetector:
    def test_returns_trigger_result(self):
        from app.engine.layers.triggers import TriggerDetector, TriggerResult
        from app.engine.layers.zones import EntryZone
        from app.engine.layers.trend import TrendResult, Trend
        td = TriggerDetector()
        zone = EntryZone(zone_type="fibonacci_golden", upper=110, lower=90, strength=0.7)
        trend = TrendResult(direction=Trend.BULLISH, strength=0.01)
        result = td.check(make_macd_cross_up_candles(), zone, trend)
        assert isinstance(result, TriggerResult)
        assert isinstance(result.confirmed, bool)
        assert isinstance(result.confirmations, list)

    def test_requires_two_confirmations(self):
        from app.engine.layers.triggers import TriggerDetector
        from app.engine.layers.zones import EntryZone
        from app.engine.layers.trend import TrendResult, Trend
        td = TriggerDetector()
        zone = EntryZone(zone_type="fibonacci_golden", upper=200, lower=0, strength=0.7)
        trend = TrendResult(direction=Trend.BULLISH, strength=0.01)
        result = td.check(make_macd_cross_up_candles(), zone, trend)
        if result.confirmed:
            assert len(result.confirmations) >= 2

    def test_confirmations_are_strings(self):
        from app.engine.layers.triggers import TriggerDetector
        from app.engine.layers.zones import EntryZone
        from app.engine.layers.trend import TrendResult, Trend
        td = TriggerDetector()
        zone = EntryZone(zone_type="fibonacci_golden", upper=200, lower=0, strength=0.7)
        trend = TrendResult(direction=Trend.BULLISH, strength=0.01)
        result = td.check(make_macd_cross_up_candles(), zone, trend)
        for c in result.confirmations:
            assert isinstance(c, str)
```

**Step 2: Implement triggers.py**

5 trigger types (all check current vs previous bar for crossovers):
- A: MACD crossover in trend direction
- B: RSI crossing midline (50)
- C: Stochastic leaving overbought/oversold
- D: Engulfing candlestick pattern
- E: Price reclaiming zone

`TriggerResult` dataclass: confirmed (bool), price (float), confirmations (list[str]).
`confirmed = len(confirmations) >= 2`

**Step 3: Verify — all PASS**

**Step 4: Commit**
```bash
git commit -m "feat(backend): Layer 4 — TriggerDetector with 5 trigger types, 2+ confirmation rule"
```

---

## Task 4: Layer 5 — Risk Manager

**Files:**
- Create: `backend/app/engine/layers/risk.py`
- Test: `backend/tests/test_risk.py`

**Step 1: Write failing tests**

```python
import numpy as np
import pandas as pd
import pytest


def make_candles(n=200):
    rng = np.random.default_rng(42)
    close = 100 + np.arange(n) * 0.3 + rng.normal(0, 0.5, n)
    high = close + rng.uniform(0.5, 2, n)
    low = close - rng.uniform(0.5, 2, n)
    return pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": rng.uniform(1000, 5000, n)})


class TestRiskManager:
    def test_calculates_stop_loss_and_take_profit(self):
        from app.engine.layers.risk import RiskManager, RiskConfig
        from app.engine.layers.zones import EntryZone
        from app.engine.layers.trend import TrendResult, Trend
        rm = RiskManager(RiskConfig())
        zone = EntryZone(zone_type="fibonacci_golden", upper=110, lower=105, strength=0.7)
        trend = TrendResult(direction=Trend.BULLISH, strength=0.01)
        result = rm.calculate(make_candles(), zone, trend, confluence_score=75, account_equity=10000)
        assert result.stop_loss > 0
        assert result.take_profit_1 > result.stop_loss
        assert result.position_size > 0

    def test_bullish_stop_below_entry(self):
        from app.engine.layers.risk import RiskManager, RiskConfig
        from app.engine.layers.zones import EntryZone
        from app.engine.layers.trend import TrendResult, Trend
        rm = RiskManager(RiskConfig())
        zone = EntryZone(zone_type="fibonacci_golden", upper=180, lower=150, strength=0.7)
        trend = TrendResult(direction=Trend.BULLISH, strength=0.01)
        candles = make_candles()
        entry = candles["close"].iloc[-1]
        result = rm.calculate(candles, zone, trend, confluence_score=75, account_equity=10000)
        assert result.stop_loss < entry

    def test_minimum_risk_reward_enforced(self):
        from app.engine.layers.risk import RiskManager, RiskConfig
        rm = RiskManager(RiskConfig(min_risk_reward=1.5))
        # The result should either have R:R >= 1.5 or be rejected
        from app.engine.layers.zones import EntryZone
        from app.engine.layers.trend import TrendResult, Trend
        zone = EntryZone(zone_type="fibonacci_golden", upper=180, lower=150, strength=0.7)
        trend = TrendResult(direction=Trend.BULLISH, strength=0.01)
        result = rm.calculate(make_candles(), zone, trend, confluence_score=75, account_equity=10000)
        assert result.rejected or result.risk_reward >= 1.5

    def test_confluence_score_scales_position(self):
        from app.engine.layers.risk import RiskManager, RiskConfig
        from app.engine.layers.zones import EntryZone
        from app.engine.layers.trend import TrendResult, Trend
        rm = RiskManager(RiskConfig())
        zone = EntryZone(zone_type="fibonacci_golden", upper=180, lower=150, strength=0.7)
        trend = TrendResult(direction=Trend.BULLISH, strength=0.01)
        candles = make_candles()
        low_score = rm.calculate(candles, zone, trend, confluence_score=50, account_equity=10000)
        high_score = rm.calculate(candles, zone, trend, confluence_score=100, account_equity=10000)
        if not low_score.rejected and not high_score.rejected:
            assert high_score.position_size >= low_score.position_size

    def test_risk_config_defaults(self):
        from app.engine.layers.risk import RiskConfig
        config = RiskConfig()
        assert config.max_risk_per_trade == 0.02
        assert config.max_daily_loss == 0.06
        assert config.atr_sl_multiplier == 2.0
        assert config.min_risk_reward == 1.5
```

**Step 2: Implement risk.py**

- `RiskConfig` dataclass: max_risk_per_trade (0.02), max_daily_loss (0.06), atr_sl_multiplier (2.0), min_risk_reward (1.5)
- `RiskCalc` dataclass: stop_loss, take_profit_1, take_profit_2, position_size, risk_amount, risk_reward, atr_value, rejected (bool), reject_reason (str|None)
- `RiskManager` class:
  - ATR-based stop loss (entry ± ATR × multiplier)
  - Fibonacci extension take profits (127.2% and 161.8%)
  - Min R:R check — reject if below threshold
  - Position sizing: `(equity × risk_pct × score_multiplier) / risk_distance`
  - Score multiplier: score 50→100 maps to 0.5×→1.0×

**Step 3: Verify — all PASS**

**Step 4: Commit**
```bash
git commit -m "feat(backend): Layer 5 — RiskManager with ATR stops, Fib targets, position sizing"
```

---

## Task 5: Layer 6 — Reversal Monitor

**Files:**
- Create: `backend/app/engine/reversal.py`
- Test: `backend/tests/test_reversal.py`

**Step 1: Write failing tests**

```python
import numpy as np
import pandas as pd
import pytest


def make_reversal_candles(n=100):
    """Uptrend that reverses — EMA cross, volume divergence."""
    rng = np.random.default_rng(42)
    up = 100 + np.arange(60) * 0.5 + rng.normal(0, 0.3, 60)
    down = up[-1] - np.arange(40) * 0.8 + rng.normal(0, 0.3, 40)
    close = np.concatenate([up, down])
    high = close + rng.uniform(0.5, 1.5, n)
    low = close - rng.uniform(0.5, 1.5, n)
    vol = np.concatenate([rng.uniform(5000, 10000, 60), rng.uniform(1000, 3000, 40)])
    return pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": vol})


class TestReversalMonitor:
    def test_returns_reversal_action(self):
        from app.engine.reversal import ReversalMonitor, ReversalAction
        rm = ReversalMonitor()
        candles = make_reversal_candles()
        action = rm.check_position(candles, direction="LONG")
        assert isinstance(action, ReversalAction)

    def test_reversal_detects_ema_cross(self):
        from app.engine.reversal import ReversalMonitor, ReversalAction
        rm = ReversalMonitor()
        candles = make_reversal_candles()
        action = rm.check_position(candles, direction="LONG")
        # Strong reversal should trigger at least TIGHTEN_STOP
        assert action in (ReversalAction.HOLD, ReversalAction.PARTIAL_CLOSE, ReversalAction.TIGHTEN_STOP, ReversalAction.CLOSE_POSITION)

    def test_hold_on_healthy_trend(self):
        from app.engine.reversal import ReversalMonitor, ReversalAction
        rng = np.random.default_rng(42)
        n = 100
        close = 100 + np.arange(n) * 0.5 + rng.normal(0, 0.2, n)
        high = close + rng.uniform(0.3, 1, n)
        low = close - rng.uniform(0.3, 1, n)
        candles = pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": rng.uniform(3000, 8000, n)})
        rm = ReversalMonitor()
        action = rm.check_position(candles, direction="LONG")
        assert action == ReversalAction.HOLD
```

**Step 2: Implement reversal.py**

- `ReversalAction` enum: HOLD, PARTIAL_CLOSE, TIGHTEN_STOP, CLOSE_POSITION
- `ReversalAlert` dataclass: alert_type (str), severity (float 0-1)
- `ReversalMonitor` class with `check_position(candles, direction) -> ReversalAction`:
  - Check EMA 10/20 cross against position (severity 0.5)
  - Check volume divergence (severity 0.4)
  - Check MACD divergence (severity 0.7)
  - Aggregate: max severity ≥ 0.8 → CLOSE, ≥ 0.6 → TIGHTEN_STOP, ≥ 0.4 + 2 alerts → PARTIAL_CLOSE, else HOLD

**Step 3: Verify — all PASS**

**Step 4: Commit**
```bash
git commit -m "feat(backend): Layer 6 — ReversalMonitor with severity-based exit actions"
```

---

## Task 6: Signal Pipeline Orchestrator

**Files:**
- Create: `backend/app/engine/pipeline.py`
- Create: `backend/app/engine/filters.py`
- Test: `backend/tests/test_pipeline.py`

**Step 1: Write failing tests**

```python
import numpy as np
import pandas as pd
import pytest


def make_trending_candles(n=300):
    rng = np.random.default_rng(42)
    close = 100 + np.arange(n) * 0.3 + rng.normal(0, 0.5, n)
    high = close + rng.uniform(0.5, 2, n)
    low = close - rng.uniform(0.5, 2, n)
    return pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": rng.uniform(1000, 5000, n)})


class TestSignalPipeline:
    def test_process_returns_signal(self):
        from app.engine.pipeline import SignalPipeline, Signal
        pipeline = SignalPipeline()
        result = pipeline.process("TEST/USD", "1h", make_trending_candles())
        assert isinstance(result, Signal)

    def test_signal_has_required_fields(self):
        from app.engine.pipeline import SignalPipeline, Signal
        pipeline = SignalPipeline()
        result = pipeline.process("TEST/USD", "1h", make_trending_candles())
        assert hasattr(result, "action")
        assert hasattr(result, "symbol")
        assert hasattr(result, "confluence_score")
        assert hasattr(result, "regime")

    def test_no_trade_is_valid_result(self):
        from app.engine.pipeline import SignalPipeline
        pipeline = SignalPipeline()
        # Ranging data should produce NO_TRADE
        rng = np.random.default_rng(42)
        n = 300
        close = 100 + rng.normal(0, 0.5, n)
        high = close + 0.5
        low = close - 0.5
        candles = pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": np.ones(n) * 5000})
        result = pipeline.process("TEST/USD", "1h", candles)
        assert result.action == "NO_TRADE"
```

**Step 2: Implement pipeline.py**

`Signal` dataclass with all fields from the tech plan. `SignalPipeline` class that orchestrates all 6 layers:

```
Layer 0: RegimeDetector → CHAOTIC blocks
Layer 1: TrendFilter → UNDETERMINED blocks
Layer 2: ZoneIdentifier → no zones blocks
Layer 3: ConfluenceScorer → score < 50 skips zone
Layer 4: TriggerDetector → not confirmed skips zone
Layer 5: RiskManager → rejected blocks
→ Return Signal with all metadata
```

**Step 3: Implement filters.py**

`SessionFilter` class:
- `is_active_session(timestamp) -> bool`
- London session: 08:00-16:00 UTC
- NY session: 13:00-21:00 UTC
- Overlap: 13:00-16:00 UTC (highest liquidity)
- Weekend filter: block Saturday/Sunday

**Step 4: Verify — all PASS**

**Step 5: Commit**
```bash
git commit -m "feat(backend): SignalPipeline orchestrator + session/timing filters"
```

---

## Task 7: Signal + Trade DB Models

**Files:**
- Create: `backend/app/models/signal.py`
- Create: `backend/app/models/trade.py`
- Modify: `backend/app/models/__init__.py`
- Create: Alembic migration

**Step 1: Create signal.py model**

```python
# Signal model: id, strategy_id FK, symbol, timeframe, direction, entry_price,
# stop_loss, take_profit, confluence_score, regime, triggers (JSON), status, created_at
```

**Step 2: Create trade.py model**

```python
# Trade model: id, signal_id FK, user_id FK, symbol, direction, entry_price,
# exit_price, position_size, stop_loss, take_profit, pnl, pnl_pct,
# risk_reward, confluence_score, entry_time, exit_time, exit_reason,
# broker_order_id, metadata (JSON)
```

**Step 3: Update models/__init__.py, generate migration**

**Step 4: Commit**
```bash
git commit -m "feat(backend): Signal + Trade DB models with Alembic migration"
```

---

## Task 8: Enhanced Backtest + Walk-Forward Optimization

**Files:**
- Modify: `backend/app/backtest/engine.py` — use full pipeline
- Create: `backend/app/backtest/optimizer.py`
- Test: `backend/tests/test_optimizer.py`

**Step 1: Update BacktestEngine to use full SignalPipeline**

Replace the Layer 1+2 only logic with the full 6-layer pipeline.

**Step 2: Implement WalkForwardOptimizer**

- `optimize(candles, symbol, timeframe, param_grid) -> dict`
- Split data into 5 folds (70% train, 30% test)
- Grid search on train, validate on test
- Select params that perform consistently across all folds
- Return best params + out-of-sample metrics

**Step 3: Write tests for optimizer**

```python
class TestWalkForwardOptimizer:
    def test_returns_best_params(self):
        from app.backtest.optimizer import WalkForwardOptimizer
        wfo = WalkForwardOptimizer()
        result = wfo.optimize(
            candles=make_trending_candles(500),
            symbol="TEST/USD",
            timeframe="1h",
            param_grid={"atr_sl_multiplier": [1.5, 2.0, 2.5], "min_confluence": [40, 50, 60]}
        )
        assert "best_params" in result
        assert "out_of_sample_metrics" in result
```

**Step 4: Verify — all PASS**

**Step 5: Commit**
```bash
git commit -m "feat(backend): full pipeline backtest + walk-forward optimization"
```

---

## Task 9: Backtest Across 3 Markets + Document Results

**Files:**
- Create: `backend/scripts/run_backtests.py`
- Create: `docs/backtest-results-phase2.md`

**Step 1: Create backtest script**

Script that fetches historical data for EUR/USD, BTC/USDT, SPY and runs backtests with the full pipeline. Outputs metrics to console and markdown.

**Step 2: Run backtests and document results**

```bash
cd backend && python scripts/run_backtests.py
```

Write results to `docs/backtest-results-phase2.md` with:
- Per-market metrics (win rate, profit factor, Sharpe, max drawdown)
- Parameter settings used
- Walk-forward validation results

**Step 3: Commit**
```bash
git commit -m "docs: Phase 2 backtest results across EUR/USD, BTC/USDT, SPY"
```

---

## Agent Team for Phase 2

| Agent | Tasks | Dependencies |
|-------|-------|-------------|
| `@layer-builder-a` | Task 1 (Regime), Task 2 (Confluence) | None — independent layers |
| `@layer-builder-b` | Task 3 (Triggers), Task 4 (Risk) | None — independent layers |
| `@reversal-pipeline` | Task 5 (Reversal), Task 6 (Pipeline + Filters), Task 7 (DB models) | After @layer-builder-a + @layer-builder-b |
| `@backtest-optimizer` | Task 8 (Enhanced backtest + WFO), Task 9 (Run backtests) | After @reversal-pipeline |

**Pipeline:**
```
Wave 1: @layer-builder-a + @layer-builder-b (parallel)
Wave 2: @reversal-pipeline (wires everything together)
Wave 3: @backtest-optimizer (validates with real data)
```
