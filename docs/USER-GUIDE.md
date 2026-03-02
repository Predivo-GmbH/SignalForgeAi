# SignalForge User Guide

## Table of Contents

1. [What is SignalForge?](#1-what-is-signalforge)
2. [Quick Start](#2-quick-start)
3. [How the Signal Pipeline Works](#3-how-the-signal-pipeline-works)
4. [The AI Investment Advisor](#4-the-ai-investment-advisor)
5. [Strategy Presets and Configuration](#5-strategy-presets-and-configuration)
6. [Frontend Pages Guide](#6-frontend-pages-guide)
7. [Walkthrough: Deploying $10,000 for Paper Trading](#7-walkthrough-deploying-10000-for-paper-trading)
8. [What Works vs What's Coming](#8-what-works-vs-whats-coming)
9. [Configuration Reference](#9-configuration-reference)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. What is SignalForge?

SignalForge is a **multi-layer automated trading system** that uses technical analysis to generate, execute, and manage cryptocurrency trades. It is designed around three core principles:

- **Fibonacci as confluence, not standalone** — Fibonacci levels alone have ~37% accuracy. Combined with volume analysis, multi-timeframe confirmation, and momentum indicators, accuracy rises to 68%+. SignalForge uses Fibonacci as one of 9 scoring factors.
- **Regime-aware trading** — The system detects market conditions (trending, ranging, chaotic) and blocks trading during chaotic regimes to avoid losses from unpredictable volatility.
- **Risk-first architecture** — Every trade is sized based on account equity and ATR-based stop-losses. Maximum risk per trade is capped (default 2%), and position size scales with signal confidence.

### What it does

1. **Ingests real-time market data** from Binance via CCXT
2. **Analyzes price action** through a 6-layer signal pipeline (regime detection, trend filtering, zone identification, confluence scoring, trigger confirmation, risk management)
3. **Generates trading signals** when all 6 layers agree on a high-probability setup
4. **Executes trades automatically** via paper trading (simulated) or live brokers (Alpaca, Binance)
5. **Manages open positions** — monitors stop-loss and take-profit levels, closes positions when targets are hit
6. **Reports performance** — tracks all trades, calculates P&L, win rate, and other metrics

### Supported Markets

- **Crypto**: Any USDT pair on Binance (BTC/USDT, ETH/USDT, SOL/USDT, and 200+ more)
- **US Stocks/ETFs**: Via Alpaca API (SPY, QQQ, AAPL, etc.)

---

## 2. Quick Start

### Prerequisites

- Docker Desktop with WSL2 integration
- Python 3.12+
- Node.js 20+

### Setup Steps

```bash
# 1. Start infrastructure (TimescaleDB + Redis)
cd backend
docker compose up -d

# 2. Create environment file
cp .env.example .env

# 3. Install Python dependencies and run migrations
pip install -e ".[dev]"
alembic upgrade head

# 4. Start the backend API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 5. Start Celery worker (in a separate terminal)
celery -A app.worker:celery_app worker --loglevel=info

# 6. Start Celery beat scheduler (in a separate terminal)
celery -A app.worker:celery_app beat --loglevel=info

# 7. Start the frontend (in a separate terminal)
cd frontend
npm install
npm run dev
```

### First Login

1. Open **http://localhost:5173**
2. Enter password gate: `signalforge`
3. Register a new account (or use test account: `roger@signalforge.dev` / `SignalForge2026`)
4. You're in! Navigate to the **AI Advisor** page to get started.

---

## 3. How the Signal Pipeline Works

Every 5 minutes, the pipeline processes market data through 6 sequential layers. Each layer can **block** the signal — only if all 6 layers agree does a trade signal fire.

```
Candle Data (300 bars)
    │
    ▼
Layer 0: Regime Detection ──── CHAOTIC? ──→ BLOCKED
    │
    ▼
Layer 1: Trend Filter ──────── UNDETERMINED? ──→ BLOCKED
    │
    ▼
Layer 2: Zone Identification ── No zones? ──→ BLOCKED
    │
    ▼
Layer 3: Confluence Scoring ─── Score < threshold? ──→ BLOCKED
    │
    ▼
Layer 4: Trigger Detection ──── < N confirmations? ──→ BLOCKED
    │
    ▼
Layer 5: Risk Management ───── R:R too low? ──→ BLOCKED
    │
    ▼
✅ SIGNAL: BUY or SELL
```

### Layer 0: Regime Detection

Classifies the current market into one of four regimes using ADX (trend strength) and ATR percentile (volatility).

| Regime | Condition | Trading |
|--------|-----------|---------|
| **TRENDING** | ADX > 25, ATR percentile 20-90% | Allowed |
| **RANGING** | ADX < 20 | Allowed |
| **TRANSITIONING** | ADX 20-25 or mixed signals | Allowed |
| **CHAOTIC** | ATR percentile > 90% AND normalized ATR > 3% | **BLOCKED** |

The CHAOTIC regime acts as a safety circuit breaker — when volatility is extreme (like flash crashes or massive pumps), the system stops trading entirely.

### Layer 1: Trend Filter

Determines the dominant trend direction using EMA (Exponential Moving Average) alignment.

| Trend | Condition |
|-------|-----------|
| **BULLISH** | EMA 50 > EMA 100 > EMA 200, and EMA 200 slope > threshold |
| **BEARISH** | EMA 50 < EMA 100 < EMA 200, and EMA 200 slope < -threshold |
| **UNDETERMINED** | No clear alignment → **BLOCKED** |

The slope threshold (`ema_slope_threshold`) is set by the AI Advisor based on market conditions. The system only trades when there's a clear trend. No trend = no trade.

### Layer 2: Zone Identification

Finds high-probability entry zones using two methods:

1. **Fibonacci Retracement Zones** — Calculates the "golden pocket" between 38.2% and 61.8% retracement levels from the most recent swing high/low. This is where institutional money often enters.

2. **VWAP Deviation Bands** — Volume-Weighted Average Price ± 1 and 2 standard deviations. These act as dynamic support/resistance levels.

If no zones are found near the current price, trading is blocked.

### Layer 3: Confluence Scoring

Scores each zone from 0-100 using 9 weighted technical factors:

| Factor | Weight | What it measures |
|--------|--------|-----------------|
| Fibonacci Alignment | 15 | Zone is based on Fibonacci levels |
| Support/Resistance Overlap | 15 | Price has bounced off this zone ≥3 times |
| Multi-Timeframe Fibonacci | 15 | Zone strength ≥ 0.7 |
| VWAP Proximity | 10 | VWAP falls inside the zone |
| Volume Node | 10 | Average volume in zone > 120% of total average |
| RSI Confirmation | 10 | RSI < 40 (bullish) or > 60 (bearish) |
| MACD Momentum | 10 | MACD histogram confirms trend direction |
| Candlestick Pattern | 10 | Hammer, engulfing, or reversal pattern detected |
| Stochastic Cross | 5 | %K crosses %D in oversold/overbought territory |

Zones scoring below the **minimum confluence threshold** (configurable, default 50) are rejected.

### Layer 4: Trigger Detection

Requires **at least N out of 5** independent trigger conditions to fire (N is set by the AI Advisor via `min_trigger_count`, checked within the last `trigger_lookback_candles` candles):

| Trigger | Bullish Condition | Bearish Condition |
|---------|-------------------|-------------------|
| **MACD Crossover** | MACD crosses above signal line | MACD crosses below signal line |
| **RSI Midline** | RSI crosses above 50 | RSI crosses below 50 |
| **Stochastic Exit** | %K leaves oversold (< 20) | %K leaves overbought (> 80) |
| **Engulfing Pattern** | Bullish engulfing candle | Bearish engulfing candle |
| **Zone Reclaim** | Price moves into/above zone | Price moves into/below zone |

This prevents false signals — a single indicator can mislead, but multiple confirming simultaneously is much more reliable. The required count and lookback window are determined by the AI Advisor based on market conditions.

### Layer 5: Risk Management

Calculates position sizing, stop-loss, and take-profit levels:

- **Stop-Loss**: Entry price ± (ATR × multiplier). Default multiplier: 2.0x
- **Take-Profit 1**: Entry ± (SL distance × 1.618) — Fibonacci extension
- **Take-Profit 2**: Entry ± (SL distance × 2.618) — Extended Fibonacci target
- **Position Size**: `(equity × risk% × confluence_multiplier) / risk_distance`
  - Confluence multiplier = score / 100 (e.g., score 65 = 0.65x)
  - This means higher-confidence signals get larger positions
- **Risk:Reward Check**: If R:R < minimum (default 1.5), the signal is rejected

---

## 4. The AI Investment Advisor

The AI Advisor is SignalForge's flagship feature for new users. It automates the entire process of:

1. **Scanning** up to 100+ cryptocurrencies on Binance that have sufficient trading volume (>$1M/day)
2. **Analyzing** each one through the signal pipeline layers (regime, trend, momentum, volatility)
3. **Scoring** and ranking them (0-100) with recommendations (strong_buy, buy, neutral, avoid)
4. **Generating a concrete investment plan** using Claude AI — which cryptos to trade, ALL optimal strategy parameters (pipeline sensitivity + risk management + features)
5. **Auto-deploying** everything — creates the strategy, backfills historical candle data, activates paper trading

### How to Use It

1. Navigate to **AI Advisor** in the sidebar
2. Click **"Scan Market"** — the system fetches real-time data from Binance and scores every liquid crypto pair (takes 1-2 minutes)
3. Review the scored table — see which cryptos have the best technical setup right now
4. Enter your investment amount (e.g., $10,000)
5. Click **"Generate Optimal Strategy"** — Claude AI analyzes market conditions and creates a fully autonomous strategy with ALL parameters optimized
6. Review the plan — selected assets, full strategy config, AI reasoning, expected behavior, warnings
7. Click **"Deploy & Start Trading"** — strategy is created and activated automatically

### Strategy Parameter Integrity

The AI Advisor is fully autonomous — it determines ALL optimal parameters based on current market conditions. There are no presets and no human risk selection. The AI decides pipeline sensitivity, risk management, timeframes, and feature toggles.

**If the market doesn't match the strategy's conditions, zero trades is the correct outcome.** The system never auto-loosens or overrides the AI's chosen parameters to force trades. The strategy is working correctly by staying out when conditions aren't right.

### What the Scoring Means

| Score | Recommendation | Meaning |
|-------|---------------|---------|
| 70-100 | Strong Buy | Multiple strong technical signals aligned |
| 50-69 | Buy | Good setup with moderate confluence |
| 30-49 | Neutral | Mixed signals, may or may not trade |
| 0-29 | Avoid | Poor technical setup, likely blocked by pipeline |

### How Allocation Works

SignalForge doesn't allocate fixed amounts per coin (e.g., "$3K to BTC"). Instead:
- The system monitors **all selected symbols** continuously
- When the 6-layer pipeline confirms a signal for any symbol, it calculates **position size as a percentage of total equity**
- With 2% risk per trade and a 65% confluence score: risk = $10,000 × 0.02 × 0.65 = **$130 at risk per trade**
- The actual position size depends on the stop-loss distance (ATR-based)

### Algorithmic Fallback

If no Claude API key is configured (`SF_ANTHROPIC_API_KEY`), the advisor uses an algorithmic fallback that selects the top-scored cryptos and applies the matching strategy preset. The AI narrative is replaced with a data-driven summary.

---

## 5. Strategy Presets and Configuration

### Pre-Built Presets

#### Conservative Swing

Best for: Patient traders who want high-probability setups only.

| Parameter | Value | Effect |
|-----------|-------|--------|
| Symbols | BTC/USDT, ETH/USDT | Only the two most liquid cryptos |
| Timeframe | 4h | Larger candles = fewer but higher-quality signals |
| Min Confluence | 70 | Only the strongest setups pass (score ≥ 70/100) |
| Risk Per Trade | 1% | Max $100 at risk on a $10K account |
| Max Daily Loss | 4% | Stops trading after $400 loss in a day |
| ATR SL Multiplier | 2.5x | Wider stops = fewer false stop-outs |
| Min Risk:Reward | 2.0 | Only takes trades with 2:1 or better reward |

Expected behavior: 0-2 trades per week. Lower win count but higher quality.

#### Balanced Momentum (Default)

Best for: Most traders. A good starting point.

| Parameter | Value | Effect |
|-----------|-------|--------|
| Symbols | BTC/USDT, ETH/USDT, SOL/USDT | Three major cryptos |
| Timeframe | 1h | Moderate signal frequency |
| Min Confluence | 50 | Standard threshold |
| Risk Per Trade | 2% | Max $200 at risk on a $10K account |
| Max Daily Loss | 6% | $600 daily loss limit |
| ATR SL Multiplier | 2.0x | Standard volatility-based stops |
| Min Risk:Reward | 1.5 | Standard minimum R:R |

Expected behavior: 0-5 trades per day depending on market conditions.

#### Aggressive Scalper

Best for: Experienced traders comfortable with higher drawdowns.

| Parameter | Value | Effect |
|-----------|-------|--------|
| Symbols | BTC/USDT, ETH/USDT, SOL/USDT | Three major cryptos |
| Timeframes | 1h, 4h | Scans both for more opportunities |
| Min Confluence | 35 | Lower bar = more signals pass |
| Risk Per Trade | 3% | Max $300 at risk on a $10K account |
| Max Daily Loss | 8% | $800 daily loss limit |
| ATR SL Multiplier | 1.5x | Tighter stops = more signals but more stop-outs |
| Min Risk:Reward | 1.2 | Accepts lower reward ratios |

Expected behavior: 2-10 trades per day. Higher win count but more false signals.

### Custom Configuration

When creating a strategy, you can customize every parameter:

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `symbols` | string[] | Any Binance USDT pairs | Which cryptos to trade |
| `timeframes` | string[] | 1m, 5m, 15m, 1h, 4h, 1d | Candle periods to analyze |
| `account_equity` | number | $100 - $10M | Your capital (for position sizing) |
| `min_confluence` | integer | 10 - 100 | Minimum score for a signal to pass Layer 3 |
| `max_risk_per_trade` | float | 0.1% - 10% | Maximum equity risked per trade |
| `max_daily_loss` | float | 1% - 20% | Daily loss circuit breaker |
| `atr_sl_multiplier` | float | 0.5 - 5.0 | Stop-loss distance in ATR multiples |
| `min_risk_reward` | float | 0.5 - 5.0 | Minimum reward-to-risk ratio |

---

## 6. Frontend Pages Guide

### Dashboard (`/`)

The main overview page with 5 widgets:

- **Stats Cards** — Total P&L, Win Rate, Profit Factor, Total Trades
- **Price Chart** — Interactive candlestick chart (BTC/USDT, ETH/USDT, SOL/USDT) with timeframe selector. Shows real candle data from the database.
- **Regime Widget** — Current market regime status and active pipeline layers
- **Signal Feed** — Live stream of the 10 most recent signals with direction, confluence scores, and timestamps
- **Positions Table** — Open positions with entry price, current P&L, stop-loss, and take-profit levels

### AI Advisor (`/advisor`)

The investment advisor page. See [Section 4](#4-the-ai-investment-advisor) for full details.

### Signals (`/signals`)

Complete signal history with:
- Paginated table: Time, Symbol, Direction, Entry Price, SL, TP1, Position Size, Confluence Score, Regime, Status
- **Generate Signal** button for testing (uses synthetic data)
- Color-coded confluence bars (red < 30, yellow 30-60, green > 60)

### Trades (`/trades`)

Historical trade log:
- Summary stats: Total Trades, Win Rate, Profit Factor, Total P&L
- Trade table: Entry/Exit prices, P&L amount and %, Risk:Reward, Confluence score, Exit reason (stop_loss, take_profit, manual)

### Backtest Lab (`/backtest`)

Strategy backtesting with three modes:
- **Single Backtest**: Choose symbol, timeframe, and lookback period. Returns metrics + equity curve.
- **Walk-Forward Optimization**: Cross-validated parameter optimization with k-fold splits. Tests strategy robustness across different time periods.
- **Strategy Validation**: Backtest an entire AI Advisor strategy against historical data. Select a deployed strategy or an AI Advisor plan (pre-deployment), and test all selected symbols with the strategy's exact risk configuration (confluence threshold, ATR multiplier, risk per trade). Shows portfolio-level metrics and per-symbol breakdown. Also accessible via the "Validate Historically" button on the AI Advisor page after generating a plan.

### Analytics (`/analytics`)

Portfolio performance metrics:
- Equity curve chart
- Metrics: Total Return, Max Drawdown, Sharpe Ratio, Sortino Ratio, Calmar Ratio
- Correlation matrix between traded symbols

### Strategy Config (`/config`)

Strategy management:
- **Preset Cards**: Choose from Conservative Swing, Balanced Momentum, or Aggressive Scalper
- **Custom Config**: JSON editor for advanced users
- Activate/deactivate strategies (only one active at a time)
- Edit, delete, and manage multiple strategies

### API Keys (`/keys`)

Broker connection management:
- Connect **Alpaca** (US stocks/crypto) or **Binance** (crypto)
- Paper/Live mode toggle
- Encrypted credential storage

---

## 7. Walkthrough: Deploying $10,000 for Paper Trading

This is a step-by-step guide to go from zero to automated paper trading.

### Step 1: Start the System

```bash
# Terminal 1: Infrastructure
cd backend && docker compose up -d

# Terminal 2: Backend API
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 3: Celery worker
cd backend && celery -A app.worker:celery_app worker --loglevel=info

# Terminal 4: Celery beat
cd backend && celery -A app.worker:celery_app beat --loglevel=info

# Terminal 5: Frontend
cd frontend && npm run dev
```

### Step 2: Register and Log In

1. Open http://localhost:5173
2. Enter password: `signalforge`
3. Click "Register" and create your account

### Step 3: Use the AI Advisor

1. Click **"AI Advisor"** in the sidebar
2. Enter **$10,000** as your investment amount
3. Select **"Balanced"** risk tolerance
4. Click **"Scan Market"**

The system will:
- Connect to Binance's public API
- Fetch all USDT spot trading pairs with sufficient liquidity (>$1M daily volume)
- Typically finds 80-120+ tradeable pairs, ranked by 24h volume
- Download 200 candles (1h) for each pair
- Run regime detection, trend analysis, RSI, MACD, ADX on each
- Score and rank all qualifying cryptos

You'll see a table like:

| # | Symbol | Price | 24h | Score | Regime | Trend | Signal |
|---|--------|-------|-----|-------|--------|-------|--------|
| 1 | BTC/USDT | $65,000 | +1.2% | 75 | trending | ↑ | strong buy |
| 2 | ETH/USDT | $3,400 | +0.8% | 68 | trending | ↑ | buy |
| 3 | SOL/USDT | $145 | +3.1% | 62 | trending | ↑ | buy |
| ... | | | | | | | |

5. Click **"Generate AI Plan"**

Claude AI will analyze the scored data and recommend:
- Which 5-10 cryptos to include
- Which strategy preset to use
- What risk parameters to set
- What to expect over the next week

6. Click **"Deploy & Start Trading"**

This automatically:
- Creates a new strategy with the AI's recommended config
- Deactivates any previously active strategy
- Triggers a candle backfill (500 candles per symbol/timeframe)
- Activates the strategy

### Step 4: What Happens Next (Automated)

Once deployed, the Celery Beat scheduler drives the entire trading loop:

**Every 60 seconds** — `ingest_candles`:
- Fetches latest candles from Binance for all strategy symbols
- Saves to TimescaleDB

**Every 5 minutes** — `run_signal_pipeline`:
- Loads last 300 candles for each symbol/timeframe
- Runs the 6-layer pipeline with your strategy's config
- If a BUY or SELL signal fires, creates a Signal row in the DB
- Publishes to Redis for real-time dashboard updates

**Every 30 seconds** — `execute_pending_signals`:
- Picks up pending signals linked to your active strategy
- Places orders via the paper trading adapter
- Mark signals as "active"

**Every 15 seconds** — `poll_order_status`:
- Checks pending orders
- Paper orders are instantly filled
- On fill: opens a Position row in the DB

**Every 60 seconds** — `manage_positions`:
- Updates current price from latest candle
- Calculates unrealized P&L
- Checks stop-loss: if price ≤ SL (for BUY) → closes position
- Checks take-profit: if price ≥ TP (for BUY) → closes position
- Creates a Trade record on close

### Step 5: Concrete Example

Let's trace a real trade with $10,000 equity and "Balanced Momentum" settings:

**Signal Generation** (BTC/USDT at $65,000):
- Layer 0: ADX = 32 → TRENDING (allowed)
- Layer 1: EMA 50 > EMA 100 > EMA 200 → BULLISH (allowed)
- Layer 2: Fibonacci golden pocket at $64,200-$64,800, VWAP at $64,500 → Zones found
- Layer 3: Fibonacci (15) + VWAP (10) + RSI at 38 (10) + MACD positive (10) + Volume node (10) = **55/100** (passes 50 threshold)
- Layer 4: MACD crossover + RSI midline cross = **2 confirmations** (passes)
- Layer 5: ATR = $800
  - Stop-loss: $65,000 - ($800 × 2.0) = **$63,400**
  - TP1: $65,000 + ($1,600 × 1.618) = **$67,589**
  - TP2: $65,000 + ($1,600 × 2.618) = **$69,189**
  - Risk distance: $1,600
  - Risk amount: $10,000 × 0.02 × 0.55 = **$110**
  - Position size: $110 / $1,600 = **0.069 BTC** (~$4,485)
  - R:R = 1.618 (passes 1.5 minimum)

**Result**: BUY signal for 0.069 BTC at $65,000, SL $63,400, TP1 $67,589

**Execution**:
- Paper adapter fills order immediately at $65,000
- Position opened: 0.069 BTC

**Outcome A — TP1 Hit** ($67,589):
- Profit: 0.069 × ($67,589 - $65,000) = **+$178.64**
- That's a +1.79% gain on equity

**Outcome B — Stop-Loss Hit** ($63,400):
- Loss: 0.069 × ($65,000 - $63,400) = **-$110.40**
- That's a -1.10% loss on equity (exactly what we risked)

### Step 6: Monitor Performance

- **Dashboard**: Watch real-time signals, open positions, and P&L
- **Signals page**: Review all generated signals with confluence scores
- **Trades page**: See closed trades with P&L, win rate, profit factor
- **Analytics**: View equity curve and performance metrics over time
- **Journal**: Get AI analysis of your trade patterns

---

## 8. What Works vs What's Coming

### Fully Working

| Feature | Status | Notes |
|---------|--------|-------|
| 6-layer signal pipeline | Working | All layers implemented with real calculations |
| AI Investment Advisor | Working | Scans Binance, scores cryptos, generates plans |
| Strategy presets | Working | Conservative, Balanced, Aggressive |
| Strategy config drives pipeline | Working | Config controls symbols, timeframes, risk params |
| Paper trading execution | Working | Automatic via Celery tasks |
| Position sizing from pipeline | Working | Replaces previous hardcoded 0.01 quantity |
| Real-time candle ingestion | Working | CCXT + Binance, every 60 seconds |
| Dynamic symbol ingestion | Working | Reads symbols from active strategy config |
| Backtest engine | Working | Single + walk-forward optimization |
| AI trade journal | Working | Requires `SF_ANTHROPIC_API_KEY` |
| Email alerts | Working | Requires `SF_RESEND_API_KEY` |
| WebSocket real-time feeds | Working | Signals, prices, trades |
| Analytics + equity curve | Working | Sharpe, Sortino, Calmar ratios |
| HMM regime detection | Working | Trains weekly on real data |
| Broker credential management | Working | Encrypted storage for Alpaca + Binance |
| Dark/light theme | Working | Toggle in top bar |

### Working with Limitations

| Feature | Limitation |
|---------|-----------|
| Backtest data | Uses real candles if available, falls back to synthetic |
| "Generate Signal" button | Always uses synthetic candles (for quick testing) |
| Analytics correlation | Falls back to synthetic if not enough real data |
| Alpaca adapter | Wired but requires real API keys + Alpaca account |
| CCXT live adapter | Wired but requires exchange API keys |
| Email alerts | Requires Resend API key (`SF_RESEND_API_KEY`) |
| AI Journal | Requires Anthropic API key (`SF_ANTHROPIC_API_KEY`) |

### Not Yet Implemented

| Feature | Status |
|---------|--------|
| Broker reconciliation | Placeholder (no-op in paper mode) |
| Multi-strategy | Only one active strategy at a time |
| Trailing stop updates | Basic implementation, not adaptive |
| Live trading | System is paper-first; live requires thorough testing |
| Multi-user signal isolation | Signals page shows all signals, not per-user |
| Mobile responsive layout | Desktop-optimized |
| Partial take-profit | System uses TP1 only; TP2 is stored but not auto-executed |

---

## 9. Configuration Reference

### Environment Variables

All variables use the `SF_` prefix. Set them in `backend/.env`.

| Variable | Default | Description |
|----------|---------|-------------|
| `SF_DATABASE_URL` | `postgresql+asyncpg://signalforge:signalforge@localhost:5432/signalforge` | TimescaleDB connection |
| `SF_REDIS_URL` | `redis://localhost:6379/0` | Redis for pub/sub and caching |
| `SF_CELERY_BROKER_URL` | `redis://localhost:6379/1` | Celery task broker |
| `SF_CELERY_RESULT_BACKEND` | `redis://localhost:6379/2` | Celery results |
| `SF_JWT_SECRET` | `dev-secret-change-in-production` | JWT signing secret |
| `SF_JWT_EXPIRY_MINUTES` | `30` | Access token lifetime |
| `SF_ENCRYPTION_KEY` | (empty) | Fernet key for broker credentials |
| `SF_ALPACA_API_KEY` | (empty) | Alpaca broker API key |
| `SF_ALPACA_API_SECRET` | (empty) | Alpaca broker API secret |
| `SF_ALPACA_PAPER` | `true` | Use Alpaca paper trading |
| `SF_ANTHROPIC_API_KEY` | (empty) | Claude API key for AI features |
| `SF_RESEND_API_KEY` | (empty) | Resend API key for email alerts |
| `SF_DEBUG` | `true` | Debug mode |
| `SF_CORS_ORIGINS` | `["http://localhost:5173"]` | Allowed CORS origins |

### Celery Beat Schedule

| Task | Interval | Purpose |
|------|----------|---------|
| `ingest_candles` | 60s | Fetch latest candles from Binance |
| `run_signal_pipeline` | 5 min | Run 6-layer analysis, persist signals |
| `execute_pending_signals` | 30s | Place orders for pending signals |
| `poll_order_status` | 15s | Check order fills, open positions |
| `manage_positions` | 60s | Update prices, check SL/TP |
| `reconcile_broker_state` | 5 min | Sync with broker (placeholder) |
| `send_daily_summary` | Daily 17:00 UTC | Email trade summary |
| `train_hmm_regime` | Sunday 02:00 UTC | Retrain HMM model |

### Docker Services

| Service | Port | Purpose |
|---------|------|---------|
| TimescaleDB | 5432 | Time-series database |
| Redis | 6379 | Cache, pub/sub, task broker |
| FastAPI | 8000 | REST API + WebSocket |
| Vite (dev) | 5173 | Frontend development server |

---

## 10. Troubleshooting

### "No active strategy found" in Celery logs

The pipeline requires an active strategy. Go to the **Strategy** page (`/config`) and either:
- Create a new strategy from a preset and click the power icon to activate it
- Or use the **AI Advisor** (`/advisor`) which creates and activates a strategy automatically

### Pipeline always returns NO_TRADE

This is normal — the 6-layer pipeline is deliberately selective. Common reasons:
- **CHAOTIC regime**: Market volatility is too high. Wait for calmer conditions.
- **UNDETERMINED trend**: No clear EMA alignment. The system won't guess.
- **Low confluence**: Not enough technical factors agree. Raise `min_confluence` to see fewer but better signals, or lower it (e.g., 35) to see more signals.
- **Insufficient candles**: Need ≥100 candles. Wait for ingestion to backfill data.

### Chart shows wrong prices / no data

- Ensure the backend is running (`uvicorn app.main:app`)
- Ensure candles have been ingested (check Celery worker logs for "Ingested X candles")
- Ensure you're logged in (the candle API requires authentication)

### Position size is 0.01

This happens with signals created before the position_size column was added. New signals will have properly calculated sizes based on your strategy's risk parameters.

### WebSocket not connecting

- Ensure Redis is running: `docker compose ps`
- Check Redis connectivity: the backend uses Redis for pub/sub broadcasting

### Backfill taking too long

The initial candle backfill fetches 500 candles per symbol/timeframe. With 15 symbols × 2 timeframes = 30 requests, or more if the advisor selects a larger set. CCXT rate-limits each to ~1 request per second, so expect 30-60 seconds for a typical deployment.

### Frontend build errors

- Ensure Node.js 20+ is installed
- Run `npm install` in the `frontend/` directory
- If using WSL, you may need to run the frontend via Windows Node.js: `cmd.exe /c "npm run dev"`
