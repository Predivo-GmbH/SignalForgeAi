# SignalForge — Multi-Layer Automated Trading Platform
## Technical Implementation Plan v1.0

---

## 1. Product Vision

**SignalForge** is a web-based automated trading platform that uses a multi-layer confluence scoring system to identify high-probability trade setups and execute orders automatically. Unlike simple indicator-based bots, SignalForge combines market regime detection, Fibonacci confluence zones, volume analysis, and dynamic risk management into a unified signal engine — backed by rigorous backtesting.

### Core Principles
- **Fibonacci as confluence, not standalone** — Research shows Fibonacci alone has a ~37% accuracy rate; combined with volume + multi-timeframe analysis, accuracy reaches 68%+
- **Regime-aware trading** — Different strategies for trending vs. ranging markets
- **Evidence-based only** — Every signal combination must pass backtesting before going live
- **Risk-first architecture** — ATR-based dynamic position sizing and stop-losses built into every trade

### Target Markets
- Forex (EUR/USD, GBP/USD, USD/JPY, etc.)
- Crypto (BTC/USDT, ETH/USDT, SOL/USDT)
- US Stocks/ETFs (via Alpaca)

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js)                       │
│  Dashboard │ Signal Monitor │ Backtest Lab │ Trade Journal       │
└──────────────────────────┬──────────────────────────────────────┘
                           │ WebSocket + REST
┌──────────────────────────┴──────────────────────────────────────┐
│                      API GATEWAY (FastAPI)                       │
│  Auth │ Rate Limiting │ WebSocket Hub │ REST Endpoints           │
└──────┬──────────┬───────────┬──────────────┬────────────────────┘
       │          │           │              │
┌──────┴───┐ ┌───┴────┐ ┌───┴───────┐ ┌───┴──────────┐
│  SIGNAL  │ │ BACKTEST│ │  ORDER    │ │   DATA       │
│  ENGINE  │ │ ENGINE  │ │  EXECUTOR │ │   PIPELINE   │
│ (Python) │ │(Python) │ │ (Python)  │ │  (Python)    │
└──────┬───┘ └───┬────┘ └───┬───────┘ └───┬──────────┘
       │         │          │              │
┌──────┴─────────┴──────────┴──────────────┴──────────────────────┐
│                    DATA LAYER                                    │
│  TimescaleDB (OHLCV) │ Redis (Real-time) │ PostgreSQL (App)     │
└─────────────────────────────────────────────────────────────────┘
       │                    │
┌──────┴─────────┐  ┌──────┴──────────────┐
│  MARKET DATA   │  │  BROKER APIs         │
│  PROVIDERS     │  │                      │
│  - CCXT        │  │  - Alpaca (Stocks)   │
│  - Polygon.io  │  │  - CCXT (Crypto)     │
│  - Alpha Vant. │  │  - IB (Futures/FX)   │
└────────────────┘  └─────────────────────┘
```

### Component Responsibilities

| Component | Role | Technology |
|-----------|------|------------|
| **Frontend** | Dashboard, monitoring, configuration, trade journal | Next.js 15, TailwindCSS, Recharts, TradingView Lightweight Charts |
| **API Gateway** | Authentication, routing, WebSocket management | FastAPI (Python), JWT auth, Redis pub/sub |
| **Signal Engine** | Multi-layer signal computation, confluence scoring | Python, pandas, numpy, ta-lib, scikit-learn |
| **Backtest Engine** | Historical strategy testing, optimization | Python, vectorbt or backtrader, parallel processing |
| **Order Executor** | Trade execution, position management, risk checks | Python, broker SDKs (alpaca-py, ccxt, ib_insync) |
| **Data Pipeline** | Market data ingestion, normalization, storage | Python, CCXT, WebSocket feeds, TimescaleDB |
| **TimescaleDB** | Time-series OHLCV data, tick data | PostgreSQL extension (optimized for time-series) |
| **Redis** | Real-time price cache, signal pub/sub, session state | Redis 7+ with Streams |
| **PostgreSQL** | User accounts, trade history, strategy configs | PostgreSQL 16 |

---

## 3. Tech Stack Detail

### Backend
```
Python 3.12+
├── FastAPI          — API framework (async, WebSocket support)
├── SQLAlchemy 2.0   — ORM for PostgreSQL
├── pandas / numpy   — Data manipulation & indicator calculation
├── ta-lib           — Technical indicator library (C-based, fast)
├── pandas-ta        — Additional indicators (VWAP, Supertrend, etc.)
├── scikit-learn     — HMM regime detection, ML models
├── hmmlearn         — Hidden Markov Model for regime detection
├── vectorbt         — Vectorized backtesting (fast)
├── ccxt             — Unified crypto exchange API (100+ exchanges)
├── alpaca-py        — Alpaca Trading API SDK
├── ib_insync        — Interactive Brokers API (optional)
├── celery           — Async task queue (backtesting jobs)
├── redis-py         — Redis client
├── websockets       — Real-time data feeds
└── pydantic         — Data validation
```

### Frontend
```
Next.js 15 (App Router)
├── TypeScript
├── TailwindCSS 4
├── shadcn/ui        — Component library
├── Recharts         — Performance charts, equity curves
├── Lightweight Charts (TradingView) — Candlestick charts with overlays
├── Zustand          — State management
├── React Query      — Server state / data fetching
└── Socket.io-client — Real-time updates
```

### Infrastructure
```
├── Docker + Docker Compose  — Local dev & deployment
├── TimescaleDB              — Time-series database (OHLCV storage)
├── PostgreSQL 16            — Application database
├── Redis 7                  — Cache, pub/sub, real-time state
├── Nginx                    — Reverse proxy, SSL termination
└── GitHub Actions           — CI/CD pipeline
```

---

## 4. Data Pipeline

### 4.1 Data Sources

| Source | Data Type | Markets | Update Freq |
|--------|-----------|---------|-------------|
| CCXT | OHLCV, orderbook, trades | Crypto (Binance, Coinbase, etc.) | Real-time WebSocket |
| Alpaca Market Data | OHLCV, quotes, trades | US Stocks/ETFs | Real-time WebSocket |
| Polygon.io | OHLCV, tick data | US Stocks, FX | Real-time WebSocket |
| Alpha Vantage | OHLCV (free tier fallback) | Stocks, FX, Crypto | 1-min polling |

### 4.2 Data Schema (TimescaleDB)

```sql
-- Hypertable for OHLCV candles
CREATE TABLE candles (
    time        TIMESTAMPTZ NOT NULL,
    symbol      TEXT NOT NULL,
    exchange    TEXT NOT NULL,
    timeframe   TEXT NOT NULL,          -- '1m', '5m', '15m', '1h', '4h', '1d'
    open        DOUBLE PRECISION,
    high        DOUBLE PRECISION,
    low         DOUBLE PRECISION,
    close       DOUBLE PRECISION,
    volume      DOUBLE PRECISION,
    vwap        DOUBLE PRECISION,       -- Pre-calculated VWAP
    trades      INTEGER                 -- Number of trades in candle
);

SELECT create_hypertable('candles', 'time');
CREATE INDEX idx_candles_symbol ON candles (symbol, timeframe, time DESC);

-- Continuous aggregates for higher timeframes
CREATE MATERIALIZED VIEW candles_1h
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS time,
    symbol, exchange,
    first(open, time) AS open,
    max(high) AS high,
    min(low) AS low,
    last(close, time) AS close,
    sum(volume) AS volume
FROM candles
WHERE timeframe = '1m'
GROUP BY time_bucket('1 hour', time), symbol, exchange;
```

### 4.3 Data Flow

```
Exchange WebSocket
    │
    ▼
Data Ingestion Worker (Python asyncio)
    │
    ├──► TimescaleDB (persistent OHLCV storage)
    │
    ├──► Redis Stream (real-time price events)
    │         │
    │         ▼
    │    Signal Engine (consumes stream, computes indicators)
    │         │
    │         ├──► Redis (current indicator values cache)
    │         │
    │         └──► Signal Events ──► Order Executor
    │
    └──► WebSocket Hub ──► Frontend (live chart updates)
```

---

## 5. Signal Engine — The Core

### 5.1 Multi-Layer Signal Pipeline

The signal engine processes each symbol/timeframe pair through 6 sequential layers. Each layer can **block** or **pass** the signal to the next layer.

```python
class SignalPipeline:
    """
    Main signal processing pipeline.
    Each layer returns a LayerResult with pass/block decision and metadata.
    """

    def process(self, symbol: str, timeframe: str, candles: pd.DataFrame) -> Signal:
        # Layer 0: Market Regime Detection
        regime = self.regime_detector.detect(candles)
        if regime == Regime.CHAOTIC:
            return Signal.NO_TRADE("Chaotic regime detected")

        # Layer 1: Trend Direction (Master Filter)
        trend = self.trend_filter.evaluate(candles)
        if trend == Trend.UNDETERMINED:
            return Signal.NO_TRADE("No clear trend")

        # Layer 2: Entry Zone Identification
        zones = self.zone_identifier.find_zones(candles, trend)
        if not zones:
            return Signal.NO_TRADE("No active entry zones")

        # Layer 3: Confluence Scoring
        for zone in zones:
            score = self.confluence_scorer.score(zone, candles, trend)
            if score < 50:
                continue  # Skip low-quality setups

            # Layer 4: Entry Trigger Detection
            trigger = self.trigger_detector.check(candles, zone, trend)
            if trigger.confirmed:

                # Layer 5: Risk Management Calculation
                risk = self.risk_manager.calculate(
                    candles, zone, trend, score
                )

                return Signal(
                    action=trend.direction,     # BUY or SELL
                    symbol=symbol,
                    entry_price=trigger.price,
                    stop_loss=risk.stop_loss,
                    take_profit=risk.take_profit,
                    position_size=risk.position_size,
                    confluence_score=score,
                    regime=regime,
                    metadata={
                        "zone": zone.to_dict(),
                        "triggers": trigger.confirmations,
                        "risk_reward": risk.ratio
                    }
                )

        return Signal.NO_TRADE("No confirmed triggers at active zones")
```

### 5.2 Layer 0 — Market Regime Detection

```python
class RegimeDetector:
    """
    Determines current market regime using multiple methods.
    Output: TRENDING_BULL, TRENDING_BEAR, RANGING, CHAOTIC
    """

    def detect(self, candles: pd.DataFrame) -> Regime:
        # Method 1: ADX-based (fast, simple)
        adx = ta.ADX(candles['high'], candles['low'], candles['close'], timeperiod=14)
        adx_regime = self._adx_regime(adx.iloc[-1])

        # Method 2: ATR expansion/contraction
        atr = ta.ATR(candles['high'], candles['low'], candles['close'], timeperiod=14)
        atr_percentile = self._atr_percentile(atr, lookback=100)

        # Method 3: Hidden Markov Model (retrained weekly)
        hmm_regime = self.hmm_model.predict_regime(candles)

        # Consensus vote
        return self._consensus(adx_regime, atr_percentile, hmm_regime)

    def _adx_regime(self, adx_value: float) -> Regime:
        if adx_value > 25:
            return Regime.TRENDING
        elif adx_value < 20:
            return Regime.RANGING
        else:
            return Regime.TRANSITIONING

    def _atr_percentile(self, atr_series, lookback=100):
        """
        ATR in top 10% = high volatility (caution)
        ATR in bottom 20% = low volatility (breakout imminent)
        ATR between 20-80% = normal conditions
        """
        current = atr_series.iloc[-1]
        percentile = (atr_series.tail(lookback) < current).mean() * 100
        return percentile
```

### 5.3 Layer 1 — Trend Direction Filter

```python
class TrendFilter:
    """
    Determines the dominant trend direction.
    Uses 200 EMA as primary, VWAP as intraday, and EMA alignment for strength.
    """

    def evaluate(self, candles: pd.DataFrame) -> TrendResult:
        close = candles['close']

        # Primary: 200 EMA
        ema_200 = ta.EMA(close, timeperiod=200)
        above_200 = close.iloc[-1] > ema_200.iloc[-1]

        # Secondary: 50 & 100 EMA alignment
        ema_50 = ta.EMA(close, timeperiod=50)
        ema_100 = ta.EMA(close, timeperiod=100)
        ema_aligned_bull = ema_50.iloc[-1] > ema_100.iloc[-1] > ema_200.iloc[-1]
        ema_aligned_bear = ema_50.iloc[-1] < ema_100.iloc[-1] < ema_200.iloc[-1]

        # Intraday: VWAP (for day trading timeframes)
        vwap = self._calculate_vwap(candles)
        above_vwap = close.iloc[-1] > vwap.iloc[-1] if vwap is not None else None

        # Trend strength via slope of 200 EMA
        ema_slope = (ema_200.iloc[-1] - ema_200.iloc[-20]) / ema_200.iloc[-20]

        if ema_aligned_bull and ema_slope > 0.001:
            return TrendResult(Trend.BULLISH, strength=abs(ema_slope), vwap_aligned=above_vwap)
        elif ema_aligned_bear and ema_slope < -0.001:
            return TrendResult(Trend.BEARISH, strength=abs(ema_slope), vwap_aligned=above_vwap)
        else:
            return TrendResult(Trend.UNDETERMINED, strength=0, vwap_aligned=above_vwap)
```

### 5.4 Layer 2 — Entry Zone Identification

```python
class ZoneIdentifier:
    """
    Finds potential entry zones using Fibonacci, VWAP bands,
    support/resistance levels, and volume profile.
    """

    def find_zones(self, candles: pd.DataFrame, trend: TrendResult) -> list[EntryZone]:
        zones = []

        # A) Fibonacci Retracement Zones
        fib_zones = self._fibonacci_zones(candles, trend)
        zones.extend(fib_zones)

        # B) VWAP Deviation Bands
        vwap_zones = self._vwap_deviation_zones(candles)
        zones.extend(vwap_zones)

        # C) Historical Support/Resistance
        sr_zones = self._support_resistance_zones(candles)
        zones.extend(sr_zones)

        # D) Volume Profile High-Volume Nodes
        vp_zones = self._volume_profile_zones(candles)
        zones.extend(vp_zones)

        return zones

    def _fibonacci_zones(self, candles, trend):
        """
        Identify swing high/low, draw Fibonacci levels.
        Multi-timeframe: also check higher TF Fibonacci for alignment.
        """
        swing_high, swing_low = self._find_swings(candles)

        if trend.direction == Trend.BULLISH:
            # Uptrend: Fib from swing low to swing high
            fib_levels = self._calculate_fib_levels(swing_low, swing_high)
        else:
            # Downtrend: Fib from swing high to swing low
            fib_levels = self._calculate_fib_levels(swing_high, swing_low)

        # Golden zone: 0.382 to 0.618
        golden_zone = EntryZone(
            type="fibonacci_golden",
            upper=fib_levels[0.382],
            lower=fib_levels[0.618],
            strength=0.7,  # Base strength
            levels=fib_levels
        )

        return [golden_zone]

    def _calculate_fib_levels(self, start: float, end: float) -> dict:
        diff = end - start
        return {
            0.0: end,
            0.236: end - 0.236 * diff,
            0.382: end - 0.382 * diff,
            0.5: end - 0.5 * diff,
            0.618: end - 0.618 * diff,
            0.786: end - 0.786 * diff,
            1.0: start,
        }

    def _vwap_deviation_zones(self, candles):
        """VWAP ±1σ and ±2σ bands as mean-reversion zones."""
        vwap = self._calculate_vwap(candles)
        std = candles['close'].rolling(20).std()

        return [
            EntryZone(type="vwap_1sigma", upper=vwap + std, lower=vwap - std, strength=0.5),
            EntryZone(type="vwap_2sigma", upper=vwap + 2*std, lower=vwap - 2*std, strength=0.8),
        ]
```

### 5.5 Layer 3 — Confluence Scoring

```python
class ConfluenceScorer:
    """
    Scores a potential trade zone on a 0-100 scale.
    Minimum 50 to trade. Higher score = larger position.
    """

    WEIGHTS = {
        "fibonacci_alignment": 15,
        "sr_overlap": 15,
        "multi_tf_fib": 15,
        "vwap_proximity": 10,
        "volume_node": 10,
        "rsi_confirmation": 10,
        "macd_momentum": 10,
        "candlestick_pattern": 10,
        "stochastic_cross": 5,
    }

    def score(self, zone: EntryZone, candles: pd.DataFrame, trend: TrendResult) -> int:
        total = 0
        details = {}

        # 1. Fibonacci level present in zone
        if zone.type.startswith("fibonacci"):
            total += self.WEIGHTS["fibonacci_alignment"]
            details["fibonacci"] = True

        # 2. Previous S/R level overlaps with zone
        sr_levels = self._find_sr_levels(candles, lookback=200)
        if self._level_in_zone(sr_levels, zone):
            total += self.WEIGHTS["sr_overlap"]
            details["sr_overlap"] = True

        # 3. Multi-timeframe Fibonacci alignment
        higher_tf_fib = self._get_higher_tf_fibs(zone.symbol)
        if self._fibs_align(zone, higher_tf_fib):
            total += self.WEIGHTS["multi_tf_fib"]
            details["multi_tf_fib"] = True

        # 4. VWAP proximity (price near VWAP)
        vwap = self._calculate_vwap(candles)
        if abs(candles['close'].iloc[-1] - vwap.iloc[-1]) / vwap.iloc[-1] < 0.005:
            total += self.WEIGHTS["vwap_proximity"]
            details["vwap_proximity"] = True

        # 5. Volume Profile high-volume node in zone
        vol_profile = self._volume_profile(candles)
        if self._high_volume_node_in_zone(vol_profile, zone):
            total += self.WEIGHTS["volume_node"]
            details["volume_node"] = True

        # 6. RSI confirmation
        rsi = ta.RSI(candles['close'], timeperiod=14)
        if trend.direction == Trend.BULLISH and rsi.iloc[-1] < 40:
            total += self.WEIGHTS["rsi_confirmation"]  # Oversold in uptrend = good entry
        elif trend.direction == Trend.BEARISH and rsi.iloc[-1] > 60:
            total += self.WEIGHTS["rsi_confirmation"]  # Overbought in downtrend

        # 7. MACD momentum aligned with trend
        macd, signal, hist = ta.MACD(candles['close'])
        if trend.direction == Trend.BULLISH and macd.iloc[-1] > signal.iloc[-1]:
            total += self.WEIGHTS["macd_momentum"]
        elif trend.direction == Trend.BEARISH and macd.iloc[-1] < signal.iloc[-1]:
            total += self.WEIGHTS["macd_momentum"]

        # 8. Candlestick pattern at zone
        pattern = self._detect_candlestick_pattern(candles, trend)
        if pattern:
            total += self.WEIGHTS["candlestick_pattern"]
            details["pattern"] = pattern

        # 9. Stochastic cross
        slowk, slowd = ta.STOCH(candles['high'], candles['low'], candles['close'])
        if trend.direction == Trend.BULLISH and slowk.iloc[-1] > slowd.iloc[-1] and slowk.iloc[-2] <= slowd.iloc[-2]:
            total += self.WEIGHTS["stochastic_cross"]

        return total
```

### 5.6 Layer 4 — Entry Triggers

```python
class TriggerDetector:
    """
    Checks for specific entry conditions.
    Requires 2+ confirmations from different indicator types.
    """

    def check(self, candles, zone, trend) -> TriggerResult:
        confirmations = []

        # Trigger A: MACD crossover in trend direction
        macd, signal, hist = ta.MACD(candles['close'])
        if trend.direction == Trend.BULLISH:
            if macd.iloc[-1] > signal.iloc[-1] and macd.iloc[-2] <= signal.iloc[-2]:
                confirmations.append("macd_cross_up")
        else:
            if macd.iloc[-1] < signal.iloc[-1] and macd.iloc[-2] >= signal.iloc[-2]:
                confirmations.append("macd_cross_down")

        # Trigger B: RSI crossing midline (50)
        rsi = ta.RSI(candles['close'], timeperiod=14)
        if trend.direction == Trend.BULLISH and rsi.iloc[-1] > 50 and rsi.iloc[-2] <= 50:
            confirmations.append("rsi_cross_above_50")
        elif trend.direction == Trend.BEARISH and rsi.iloc[-1] < 50 and rsi.iloc[-2] >= 50:
            confirmations.append("rsi_cross_below_50")

        # Trigger C: Stochastic leaving overbought/oversold
        slowk, slowd = ta.STOCH(candles['high'], candles['low'], candles['close'])
        if trend.direction == Trend.BULLISH and slowk.iloc[-2] < 20 and slowk.iloc[-1] > 20:
            confirmations.append("stoch_exit_oversold")
        elif trend.direction == Trend.BEARISH and slowk.iloc[-2] > 80 and slowk.iloc[-1] < 80:
            confirmations.append("stoch_exit_overbought")

        # Trigger D: Engulfing candlestick
        if self._is_engulfing(candles, trend.direction):
            confirmations.append("engulfing_candle")

        # Trigger E: Price reclaiming zone (confirmation candle close)
        if self._price_reclaimed_zone(candles, zone, trend):
            confirmations.append("zone_reclaim")

        # Require 2+ different confirmations
        confirmed = len(confirmations) >= 2
        return TriggerResult(
            confirmed=confirmed,
            price=candles['close'].iloc[-1],
            confirmations=confirmations
        )
```

### 5.7 Layer 5 — Risk Management

```python
class RiskManager:
    """
    ATR-based dynamic stop-loss, position sizing, and profit targets.
    """

    def __init__(self, config: RiskConfig):
        self.max_risk_pct = config.max_risk_per_trade   # e.g., 0.02 (2%)
        self.max_daily_loss = config.max_daily_loss      # e.g., 0.06 (6%)
        self.atr_sl_multiplier = config.atr_sl_multiplier # e.g., 2.0
        self.min_risk_reward = config.min_risk_reward     # e.g., 1.5

    def calculate(self, candles, zone, trend, confluence_score) -> RiskCalc:
        # ATR for dynamic stop-loss
        atr = ta.ATR(candles['high'], candles['low'], candles['close'], timeperiod=14)
        current_atr = atr.iloc[-1]
        entry_price = candles['close'].iloc[-1]

        # Stop-loss: ATR-based
        if trend.direction == Trend.BULLISH:
            stop_loss = entry_price - (current_atr * self.atr_sl_multiplier)
            # Don't place stop above the zone's lower bound
            stop_loss = min(stop_loss, zone.lower - current_atr * 0.5)
        else:
            stop_loss = entry_price + (current_atr * self.atr_sl_multiplier)
            stop_loss = max(stop_loss, zone.upper + current_atr * 0.5)

        # Risk distance
        risk_distance = abs(entry_price - stop_loss)

        # Profit targets via Fibonacci extensions
        fib_ext_1 = entry_price + (risk_distance * 1.272)  # TP1: 127.2% extension
        fib_ext_2 = entry_price + (risk_distance * 1.618)  # TP2: 161.8% extension

        # Minimum risk/reward check
        potential_reward = abs(fib_ext_1 - entry_price)
        risk_reward = potential_reward / risk_distance
        if risk_reward < self.min_risk_reward:
            return RiskCalc.REJECTED("Risk/reward too low")

        # Position sizing: risk-based
        account_equity = self._get_account_equity()
        risk_amount = account_equity * self.max_risk_pct

        # Scale position with confluence score (50-100 maps to 0.5x-1.0x)
        score_multiplier = 0.5 + (confluence_score - 50) / 100
        adjusted_risk = risk_amount * score_multiplier

        position_size = adjusted_risk / risk_distance

        # Daily loss check
        if self._daily_loss_exceeded():
            return RiskCalc.REJECTED("Daily loss limit reached")

        return RiskCalc(
            stop_loss=stop_loss,
            take_profit_1=fib_ext_1,
            take_profit_2=fib_ext_2,
            position_size=position_size,
            risk_amount=adjusted_risk,
            risk_reward=risk_reward,
            atr_value=current_atr
        )
```

### 5.8 Layer 6 — Reversal Protection (Active Trade Monitoring)

```python
class ReversalMonitor:
    """
    Monitors open positions for signs of trend reversal.
    Can trigger early exit before stop-loss is hit.
    """

    def check_position(self, position, candles) -> ReversalAlert:
        alerts = []

        # 1. MACD Divergence
        if self._macd_divergence(candles, position.direction):
            alerts.append(ReversalAlert("macd_divergence", severity=0.7))

        # 2. Trendline break
        if self._trendline_broken(candles, position.direction):
            alerts.append(ReversalAlert("trendline_break", severity=0.8))

        # 3. Double top/bottom formation
        if self._double_pattern(candles, position.direction):
            alerts.append(ReversalAlert("double_pattern", severity=0.6))

        # 4. EMA crossover (10/20) against position
        ema10 = ta.EMA(candles['close'], 10)
        ema20 = ta.EMA(candles['close'], 20)
        if position.direction == "LONG" and ema10.iloc[-1] < ema20.iloc[-1]:
            alerts.append(ReversalAlert("ema_cross_against", severity=0.5))

        # 5. Volume declining on new highs/lows
        if self._volume_divergence(candles, position.direction):
            alerts.append(ReversalAlert("volume_divergence", severity=0.4))

        # Calculate aggregate severity
        if alerts:
            max_severity = max(a.severity for a in alerts)
            if max_severity >= 0.8:
                return ReversalAction.CLOSE_POSITION
            elif max_severity >= 0.6:
                return ReversalAction.TIGHTEN_STOP  # Move stop to breakeven
            elif max_severity >= 0.4 and len(alerts) >= 2:
                return ReversalAction.PARTIAL_CLOSE  # Close 50% of position

        return ReversalAction.HOLD
```

---

## 6. Backtesting Engine

### 6.1 Architecture

```python
class BacktestEngine:
    """
    Vectorized backtesting engine using vectorbt for speed.
    Tests the full signal pipeline on historical data.
    """

    def run(self, config: BacktestConfig) -> BacktestResult:
        # Load historical data
        candles = self.data_loader.load(
            symbol=config.symbol,
            timeframe=config.timeframe,
            start=config.start_date,
            end=config.end_date
        )

        # Initialize pipeline with same config as live
        pipeline = SignalPipeline(config.strategy_params)

        # Walk-forward simulation
        trades = []
        equity_curve = [config.initial_capital]

        for i in range(config.lookback, len(candles)):
            window = candles.iloc[:i+1]

            # Check for signal
            signal = pipeline.process(config.symbol, config.timeframe, window)

            if signal.action != "NO_TRADE":
                trade = self._simulate_trade(signal, candles.iloc[i:], equity_curve[-1])
                trades.append(trade)
                equity_curve.append(equity_curve[-1] + trade.pnl)

        return BacktestResult(
            trades=trades,
            equity_curve=equity_curve,
            metrics=self._calculate_metrics(trades, equity_curve, config.initial_capital)
        )

    def _calculate_metrics(self, trades, equity_curve, initial_capital):
        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl <= 0]

        return {
            "total_trades": len(trades),
            "win_rate": len(wins) / len(trades) * 100 if trades else 0,
            "profit_factor": sum(t.pnl for t in wins) / abs(sum(t.pnl for t in losses)) if losses else float('inf'),
            "total_return_pct": (equity_curve[-1] - initial_capital) / initial_capital * 100,
            "max_drawdown_pct": self._max_drawdown(equity_curve),
            "sharpe_ratio": self._sharpe_ratio(equity_curve),
            "avg_risk_reward": np.mean([t.risk_reward for t in wins]) if wins else 0,
            "max_consecutive_wins": self._max_consecutive(trades, True),
            "max_consecutive_losses": self._max_consecutive(trades, False),
            "avg_trade_duration": np.mean([t.duration for t in trades]) if trades else 0,
        }
```

### 6.2 Walk-Forward Optimization

```python
class WalkForwardOptimizer:
    """
    Prevents overfitting by splitting data into in-sample (train)
    and out-of-sample (test) windows.
    """

    def optimize(self, symbol, timeframe, full_data, param_grid):
        # Split into 5 folds: 70% train, 30% test each
        folds = self._create_folds(full_data, n_folds=5, train_pct=0.7)

        results = []
        for fold in folds:
            # Optimize on train data
            best_params = self._grid_search(fold.train, param_grid)

            # Validate on test data (unseen)
            test_result = self.backtest_engine.run(
                BacktestConfig(
                    symbol=symbol,
                    timeframe=timeframe,
                    data=fold.test,
                    strategy_params=best_params
                )
            )
            results.append({
                "params": best_params,
                "in_sample": fold.train_metrics,
                "out_of_sample": test_result.metrics
            })

        # Select params that perform consistently across all folds
        return self._select_robust_params(results)
```

---

## 7. Order Execution

### 7.1 Execution Flow

```
Signal Engine ──► Signal Queue (Redis)
                       │
                       ▼
              ┌─────────────────┐
              │  Pre-Trade      │
              │  Risk Checks    │
              │                 │
              │  • Daily loss   │
              │  • Max positions│
              │  • Correlation  │
              │  • Margin check │
              └────────┬────────┘
                       │ PASS
                       ▼
              ┌─────────────────┐
              │  Order Router   │
              │                 │
              │  Alpaca ──► US  │
              │  CCXT ──► Crypto│
              │  IB ──► FX/Fut │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  Position       │
              │  Manager        │
              │                 │
              │  • Track fills  │
              │  • Set SL/TP   │
              │  • Trail stops  │
              │  • Monitor      │
              └─────────────────┘
```

### 7.2 Broker Integration

```python
class OrderExecutor:
    """
    Unified order execution across multiple brokers.
    """

    def __init__(self):
        self.brokers = {
            "stocks": AlpacaBroker(api_key, secret_key, paper=True),
            "crypto": CCXTBroker(exchange='binance', api_key, secret),
            # "forex": IBBroker(host, port, client_id)  # Optional Phase 3
        }

    async def execute_signal(self, signal: Signal):
        broker = self._route_to_broker(signal.symbol)

        # Pre-trade checks
        if not self._pre_trade_checks(signal):
            return ExecutionResult.REJECTED

        # Place entry order
        entry_order = await broker.place_order(
            symbol=signal.symbol,
            side=signal.action,
            qty=signal.position_size,
            type="limit",
            limit_price=signal.entry_price,
            time_in_force="gtc"
        )

        # Set bracket orders (stop-loss + take-profit)
        if entry_order.filled:
            await broker.place_oco_order(
                symbol=signal.symbol,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit_1,
                qty=signal.position_size
            )

            # Log trade
            await self.trade_logger.log(signal, entry_order)

        return ExecutionResult(order=entry_order, signal=signal)
```

---

## 8. Frontend — Dashboard Design

### 8.1 Main Views

```
┌───────────────────────────────────────────────────────────────┐
│  📊 SignalForge Dashboard                              [⚙️]   │
├───────┬───────────────────────────────────────────────────────┤
│       │                                                       │
│ NAV   │  ┌─────────────────────────────────────────────────┐  │
│       │  │  📈 Live Chart (TradingView Lightweight)        │  │
│ Home  │  │  Candlesticks + EMA overlay + Fib levels       │  │
│       │  │  + VWAP bands + S/R zones + Active signals     │  │
│ Signals│ │                                                 │  │
│       │  └─────────────────────────────────────────────────┘  │
│ Trades│                                                       │
│       │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│ Back- │  │ Active Trades │  │ Confluence   │  │  Regime    │  │
│ test  │  │ ▲ EUR/USD +12 │  │ Score: 75/100│  │ 🟢 TREND  │  │
│       │  │ ▼ BTC/USD -5  │  │ Score: 62/100│  │ ADX: 31.4 │  │
│ Journal│ └──────────────┘  └──────────────┘  └────────────┘  │
│       │                                                       │
│ Config│  ┌─────────────────────────────────────────────────┐  │
│       │  │  📋 Signal Feed (Real-time)                     │  │
│       │  │  14:32 EUR/USD BUY  Score:75 RR:2.1 ✅ Filled  │  │
│       │  │  14:28 BTC/USD SELL Score:52 RR:1.6 ⏳ Pending │  │
│       │  │  14:15 GBP/USD BUY  Score:43 ❌ Below threshold│  │
│       │  └─────────────────────────────────────────────────┘  │
└───────┴───────────────────────────────────────────────────────┘
```

### 8.2 Key Pages

| Page | Purpose |
|------|---------|
| **Dashboard** | Live chart with signal overlays, active positions, regime indicator, P&L summary |
| **Signal Monitor** | Real-time signal feed with confluence breakdown, filter by symbol/score/regime |
| **Trade History** | All executed trades with entry/exit, P&L, confluence score, replay on chart |
| **Backtest Lab** | Configure and run backtests, compare strategies, equity curves, optimization |
| **Trade Journal** | AI-assisted trade analysis, pattern recognition in wins/losses |
| **Strategy Config** | Adjust all layer parameters, indicator settings, risk rules |
| **API Keys** | Configure broker connections (Alpaca, exchange API keys) |

---

## 9. Database Schema (PostgreSQL)

```sql
-- Users
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Strategy Configurations
CREATE TABLE strategies (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id),
    name            TEXT NOT NULL,
    is_active       BOOLEAN DEFAULT FALSE,
    config          JSONB NOT NULL,  -- All layer parameters
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Broker Connections
CREATE TABLE broker_connections (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id),
    broker          TEXT NOT NULL,       -- 'alpaca', 'binance', 'ib'
    api_key_enc     BYTEA NOT NULL,      -- Encrypted
    api_secret_enc  BYTEA NOT NULL,      -- Encrypted
    is_paper        BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Trade Signals (generated)
CREATE TABLE signals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id     UUID REFERENCES strategies(id),
    symbol          TEXT NOT NULL,
    timeframe       TEXT NOT NULL,
    direction       TEXT NOT NULL,       -- 'BUY' or 'SELL'
    entry_price     DOUBLE PRECISION,
    stop_loss       DOUBLE PRECISION,
    take_profit     DOUBLE PRECISION,
    confluence_score INTEGER,
    regime          TEXT,
    triggers        JSONB,              -- List of trigger confirmations
    status          TEXT DEFAULT 'pending', -- pending, executed, expired, cancelled
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Executed Trades
CREATE TABLE trades (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id       UUID REFERENCES signals(id),
    user_id         UUID REFERENCES users(id),
    symbol          TEXT NOT NULL,
    direction       TEXT NOT NULL,
    entry_price     DOUBLE PRECISION NOT NULL,
    exit_price      DOUBLE PRECISION,
    position_size   DOUBLE PRECISION NOT NULL,
    stop_loss       DOUBLE PRECISION,
    take_profit     DOUBLE PRECISION,
    pnl             DOUBLE PRECISION,
    pnl_pct         DOUBLE PRECISION,
    risk_reward     DOUBLE PRECISION,
    confluence_score INTEGER,
    entry_time      TIMESTAMPTZ NOT NULL,
    exit_time       TIMESTAMPTZ,
    exit_reason     TEXT,               -- 'take_profit', 'stop_loss', 'reversal', 'manual'
    broker_order_id TEXT,
    metadata        JSONB               -- Full signal context for journaling
);

-- Backtest Results
CREATE TABLE backtests (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id),
    strategy_config JSONB NOT NULL,
    symbol          TEXT NOT NULL,
    timeframe       TEXT NOT NULL,
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    metrics         JSONB NOT NULL,     -- win_rate, sharpe, drawdown, etc.
    equity_curve    JSONB,              -- Array of equity values
    trades          JSONB,              -- Array of trade objects
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 10. Phased Build Roadmap

### Phase 1 — Foundation (Weeks 1-4)
**Goal: Data pipeline + basic signal engine + backtest capability**

- [ ] Project scaffolding (monorepo: `/backend`, `/frontend`, `/shared`)
- [ ] Docker Compose: TimescaleDB, PostgreSQL, Redis
- [ ] Data pipeline: CCXT integration, candle ingestion, TimescaleDB storage
- [ ] Indicator library: EMA, RSI, MACD, ATR, Stochastic, VWAP, Fibonacci
- [ ] Layer 1 (Trend Filter) + Layer 2 (Zone Identifier) implementation
- [ ] Basic backtest engine with walk-forward testing
- [ ] CLI tool to run backtests and output metrics
- [ ] Unit tests for all indicator calculations

**Deliverable:** Run backtests from CLI, see win rate / profit factor / equity curve

### Phase 2 — Signal Engine Complete (Weeks 5-8)
**Goal: Full 6-layer pipeline + confluence scoring**

- [ ] Layer 0: Regime detection (ADX + ATR percentile)
- [ ] Layer 3: Confluence scorer (all 9 factors)
- [ ] Layer 4: Trigger detector (5 trigger types)
- [ ] Layer 5: ATR-based risk management
- [ ] Layer 6: Reversal monitor
- [ ] Session/timing filter (London, NY sessions)
- [ ] News event filter (calendar integration)
- [ ] Multi-timeframe Fibonacci alignment
- [ ] Volume Profile calculation
- [ ] Run backtests across EUR/USD, BTC/USDT, SPY — tune parameters
- [ ] Walk-forward optimization to prevent overfitting

**Deliverable:** Full signal pipeline backtested across 3 markets, documented results

### Phase 3 — API & Paper Trading (Weeks 9-12)
**Goal: FastAPI backend + Alpaca paper trading**

- [ ] FastAPI application with auth (JWT)
- [ ] REST endpoints: signals, trades, strategies, backtests
- [ ] WebSocket: real-time signal feed + price updates
- [ ] Alpaca paper trading integration
- [ ] CCXT paper/testnet trading (Binance testnet)
- [ ] Order executor with pre-trade risk checks
- [ ] Position manager (track open positions, trail stops)
- [ ] Redis pub/sub for signal → executor flow
- [ ] Trade logging to PostgreSQL
- [ ] Error handling, retry logic, circuit breakers

**Deliverable:** Signals auto-execute on Alpaca paper account, all trades logged

### Phase 4 — Frontend Dashboard (Weeks 13-16)
**Goal: Full web UI for monitoring and configuration**

- [ ] Next.js app with auth
- [ ] Dashboard: live chart (TradingView Lightweight Charts)
- [ ] Signal overlay on chart (Fibonacci levels, S/R, entry/exit)
- [ ] Real-time signal feed via WebSocket
- [ ] Active positions panel with P&L
- [ ] Regime indicator widget
- [ ] Trade history table with filters and stats
- [ ] Backtest Lab: configure, run, compare results
- [ ] Strategy configuration UI (all layer parameters)
- [ ] Broker connection setup (Alpaca API keys)
- [ ] Mobile-responsive design

**Deliverable:** Fully functional web dashboard, paper trading live

### Phase 5 — Advanced Features (Weeks 17-20)
**Goal: ML regime detection, trade journal, optimization**

- [ ] HMM-based regime detection (retrained weekly)
- [ ] Trade journal with AI analysis (pattern recognition in losses)
- [ ] Walk-forward optimization UI in Backtest Lab
- [ ] Multi-symbol portfolio management
- [ ] Correlation check (avoid over-exposure to same direction)
- [ ] Alert system (email/push when signals fire)
- [ ] Performance analytics dashboard
- [ ] Equity curve visualization
- [ ] Risk-adjusted metrics (Sharpe, Sortino, Calmar)

**Deliverable:** ML-enhanced regime detection, comprehensive analytics

### Phase 6 — Live Trading & Hardening (Weeks 21-24)
**Goal: Go live with real money (small positions)**

- [ ] Live trading mode (Alpaca real account)
- [ ] Live crypto trading (Binance/Coinbase via CCXT)
- [ ] Enhanced error handling & monitoring
- [ ] Logging & alerting (trade failures, API errors)
- [ ] Rate limiting & API quota management
- [ ] Graceful degradation (continue monitoring if broker API down)
- [ ] Daily P&L reports (email)
- [ ] Deployment to cloud (VPS/Docker)
- [ ] SSL, security audit, encrypted API key storage
- [ ] Documentation & runbook

**Deliverable:** Production-ready automated trading system

---

## 11. Key Risk Mitigations

| Risk | Mitigation |
|------|------------|
| **Overfitting** | Walk-forward validation, out-of-sample testing, minimum 200 trades per backtest |
| **API failures** | Retry logic, circuit breakers, graceful degradation, position state recovery |
| **Slippage** | Limit orders preferred, account for spread in backtests, avoid low-liquidity times |
| **News events** | Economic calendar integration, pause trading around high-impact events |
| **Regime change** | HMM re-training weekly, ATR-based regime detection in real-time |
| **Runaway losses** | Daily loss limit (6%), max consecutive loss pause (3), max position count |
| **Data quality** | Multiple data sources, candle validation, gap detection |
| **Over-leverage** | Hard cap on position sizing, never exceed 2% risk per trade |

---

## 12. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Win Rate | >55% | Backtested + live |
| Profit Factor | >1.5 | Total wins / total losses |
| Max Drawdown | <15% | Peak-to-trough equity decline |
| Sharpe Ratio | >1.5 | Risk-adjusted returns |
| Average R:R | >1.5:1 | Average reward / risk per trade |
| Monthly Return | 3-8% | With 1-2% risk per trade |
| System Uptime | >99.5% | Signal engine availability |

---

## 13. Estimated Costs

| Item | Monthly Cost | Notes |
|------|-------------|-------|
| VPS (4 CPU, 8GB RAM) | ~$40 | Hetzner or DigitalOcean |
| TimescaleDB Cloud (optional) | $0-30 | Self-hosted in Docker = free |
| Polygon.io Market Data | $0-29 | Free tier for delayed, $29 for real-time |
| Alpaca | Free | Commission-free, paper trading included |
| CCXT / Exchange APIs | Free | Rate limits apply |
| Domain + SSL | ~$15/year | Cloudflare for free SSL |
| **Total** | **~$40-100/mo** | |

---

*This plan is a living document. Parameters, indicator combinations, and risk rules should be continuously refined through backtesting and live performance analysis.*
