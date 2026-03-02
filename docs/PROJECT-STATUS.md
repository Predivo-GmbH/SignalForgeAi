# SignalForge — Project Status (Phases 1–7 Complete)

> **For Claude:** Use this document as the single source of truth for the project.

**Last updated:** 2026-03-02
**Last committed:** `79baeb3` on `main` (88 commits) — extensive uncommitted work beyond this
**Quality gates:** 296 backend tests, 41 frontend tests (at last commit; new tests added since)

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | React + TypeScript + Vite | 19.2 / 5.9 / 7.3 |
| Styling | Tailwind CSS + CSS custom properties | 4.2 |
| State (server) | TanStack React Query | 5.90 |
| State (client) | Zustand (persisted) | 5.0 |
| Routing | React Router DOM | 7.13 |
| Charts | lightweight-charts | 5.1 |
| Icons | lucide-react | 0.575 |
| Backend | Python 3.12 + FastAPI | 0.115 |
| ORM | SQLAlchemy 2.0 (async) + Alembic | 2.0.36 |
| Database | PostgreSQL 16 + TimescaleDB | via Docker |
| Cache/Broker | Redis 7 | via Docker |
| Task Queue | Celery 5.6 | redis broker |
| ML | hmmlearn (HMM), numpy, pandas | 0.3+ |
| AI | Anthropic SDK (Claude Haiku 4.5 / Sonnet) | 0.52+ |
| Email | Resend | 2.0+ |
| Market Data | CCXT 4.4 | exchange connectors |
| Broker (Crypto) | CCXT 4.4+ | Binance + 100 exchanges |
| Encryption | cryptography 43+ | Fernet symmetric |
| Rate Limiting | slowapi 0.1.9+ | FastAPI middleware |
| Logging | structlog 24+ | JSON structured logging |
| Testing | pytest 8.3 (backend) / Vitest 4.0 (frontend) | |
| Linting | ruff (backend) / eslint 9 (frontend) | |
| CI | GitHub Actions | on push/PR to main |

---

## Project Root: `C:\Business\Internal Projects\day-trading`

```
day-trading/
├── .github/workflows/ci.yml     # Backend lint+test, frontend build
├── backend/
│   ├── app/                     # FastAPI application (~100 .py files)
│   │   ├── advisor/             # AI Advisor: Claude client, planner, signal quality, risk tuner, feedback, pattern analyzer
│   │   ├── api/                 # REST endpoints (12 routers)
│   │   ├── auth/                # JWT auth (register, login, refresh)
│   │   ├── backtest/            # Engine + optimizer + portfolio runner
│   │   ├── core/                # Database, Redis, pub/sub, email, circuit breaker, logging, encryption
│   │   ├── data/                # CCXT ingestion, DB-backed candle storage (bulk upsert)
│   │   ├── engine/              # 6-layer signal pipeline
│   │   │   └── layers/          # regime, trend, zones, confluence, triggers, risk, hmm_regime, feedback_filter
│   │   ├── execution/           # DB-backed executor, position manager, risk checks
│   │   │   └── adapters/        # BrokerAdapter ABC, Paper, CCXT, BrokerRouter
│   │   ├── models/              # SQLAlchemy models (11 models)
│   │   ├── tasks/               # Celery tasks + Beat schedule (13 periodic tasks)
│   │   ├── ws/                  # WebSocket hub (signals + prices + trades)
│   │   ├── config.py            # Settings with SF_ env prefix + AI feature flags
│   │   ├── main.py              # FastAPI app with middleware + 12 routers (journal removed)
│   │   └── worker.py            # Celery worker + Beat schedule (13 tasks)
│   ├── tests/                   # ~50 test files
│   ├── scripts/                 # run_backtests.py, init-db.sql
│   ├── alembic/                 # 5 migration files
│   ├── docker-compose.yml       # Dev: 5 services (db, redis, api, worker, beat)
│   ├── Dockerfile               # Dev Dockerfile
│   ├── Dockerfile.prod          # Multi-stage production Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/          # Reusable UI (~20 components)
│   │   │   ├── analytics/       # EquityCurve, MetricsGrid, CorrelationMatrix
│   │   │   ├── backtest/        # BacktestForm, BacktestResults, StrategyBacktestForm, StrategyBacktestResults, WalkForwardForm, WalkForwardResults
│   │   │   ├── dashboard/       # PriceChart, StatsCards, SignalFeed, PositionsTable, RegimeWidget
│   │   │   ├── layout/          # AppLayout, Sidebar, Topbar, HelpDrawer
│   │   │   ├── settings/        # AiUsageTab
│   │   │   └── ui/              # Badge, DataTable, Pagination
│   │   ├── hooks/               # 16 data hooks (useJournal removed)
│   │   ├── lib/                 # api, auth, cn, colors, query, sidebar, theme, ws
│   │   ├── pages/               # 8 pages (+ Login/Register)
│   │   ├── App.tsx              # Router configuration
│   │   ├── main.tsx             # Entry point
│   │   └── index.css            # Theme tokens (dark/light)
│   ├── package.json
│   └── tsconfig.app.json
├── docs/
│   ├── PROJECT-STATUS.md        # This file
│   ├── SESSION-CHANGELOG-2026-03-02.md  # Detailed session changelog
│   ├── DEPLOYMENT-GUIDE.md
│   ├── SETUP-GUIDE.md
│   ├── TEAM-HANDOFF.md
│   ├── USER-GUIDE.md
│   ├── WORKFLOW-GITHUB-AND-DEPLOYMENT.md
│   ├── backtest-results-phase2.md
│   ├── trading-risk-management.md
│   └── plans/                   # Implementation plans
├── docker-compose.prod.yml      # Production Docker Compose (5 services)
├── CLAUDE.md                    # Project rules
└── SignalForge-Technical-Plan.md # Original design spec
```

---

## Phase-by-Phase Summary

### Phase 1: Foundation (Commits `d872185` → `abecce2`)

**What was built:**
- Monorepo scaffold with `backend/` and `frontend/` directories
- Docker Compose: TimescaleDB (port 5432) + Redis (port 6379) + FastAPI (port 8000)
- GitHub Actions CI: backend lint+test, frontend build
- Frontend scaffold: Vite + React + TypeScript + Tailwind 4 + theme system
- Backend scaffold: FastAPI with health endpoint, config, test setup
- SQLAlchemy models + Alembic migrations setup
- JWT auth: register, login, refresh token endpoints
- CCXT candle ingestion pipeline + TimescaleDB storage
- Indicator library (SMA, EMA, RSI, MACD, Bollinger, ATR, ADX, Stochastic)
- Layer 1 (TrendFilter) + Layer 2 (ZoneIdentifier)
- Backtest engine + CLI runner + data pipeline
- Password gate (frontend) + login page placeholder

### Phase 2: Signal Engine (Commits `e7f23d2` → `86bb184`)

**What was built:**
- Complete 6-layer signal pipeline:
  - **Layer 0 — RegimeDetector**: ADX + ATR percentile → Regime enum (TRENDING, RANGING, TRANSITIONING, CHAOTIC). CHAOTIC blocks all trades.
  - **Layer 1 — TrendFilter**: Multi-timeframe EMA + ADX + Ichimoku → Trend direction + strength
  - **Layer 2 — ZoneIdentifier**: Fibonacci retracements, S/R from swing pivots, VWAP zones → EntryZone list
  - **Layer 3 — ConfluenceScorer**: 9 weighted factors → 0-100 score. Threshold: configurable (default 40)
  - **Layer 4 — TriggerDetector**: 5 trigger types (EMA crossover, RSI reversal, MACD cross, Bollinger bounce, volume spike). Needs 2+ confirmations.
  - **Layer 5 — RiskManager**: ATR-based stops, Fibonacci targets (TP1/TP2/TP3), Kelly-criterion position sizing
- **Layer 6 — ReversalMonitor**: 4 severity levels, actions from tighten_stop to close_position
- **SignalPipeline orchestrator** (`engine/pipeline.py`): Chains all 6 layers, early-exits on blocks with `block_reason`, picks best zone by confluence
- **Walk-Forward Optimizer**: Grid search with k-fold train/test splits

**Pipeline flow:**
```
Candles → Regime (block if CHAOTIC → block_reason: chaotic_regime)
       → Trend (block if neutral → block_reason: no_trend)
       → Zones (skip if none → block_reason: no_zones)
       → Confluence (skip if < threshold → block_reason: low_confluence)
       → Triggers (skip if < 2 confirmations → block_reason: no_trigger)
       → Risk (sizing, stops, targets → block_reason: risk_rejected:*)
       → Signal with confluence_details
```

### Phase 3: API & Paper Trading (Commits `6b39c7f` → `d02d6b9`)

**What was built:**
- 10 API routers all under `/api` prefix
- Auth dependency: `get_current_user` extracts user_id from JWT Bearer token
- Order Executor with pre-trade risk checks + paper mode
- PositionManager: Track open positions, trail stops, close with PnL
- Redis pub/sub: Signal and price channels for real-time broadcasting
- Celery setup: Async backtest tasks, Redis broker
- WebSocket hub: `/ws/signals` and `/ws/prices` for real-time streaming
- Strategies CRUD API with activate/deactivate toggle

### Phase 4: Frontend Dashboard (Commits `540ca66` → `91b3377`)

**What was built:**
- Router + Auth: React Router DOM with protected routes, Zustand auth store
- Layout shell: Collapsible sidebar, topbar with theme toggle + logout
- 9 pages (many since replaced — see Phase 7)
- 12 hooks, WebSocket manager, API client with Bearer auth

**Theme system** (CSS custom properties in `index.css`):
```
Light: bg-base=#F7F5F2, bg-surface=#FFFFFF, accent=#7B61FF, text=#1A1A2E
Dark:  bg-base=#0B0B14, bg-surface=#141420, accent=#7B61FF, text=#F0F0F5
Semantic: positive=#00D68F, negative=#FF4D6A, warning=#FFB020
```

### Phase 5: Advanced Features (Commits `5eede6a` → `f144c59`)

**What was built:**
- Sortino + Calmar ratios in backtest engine
- HMM Regime Detection with 3 states (low_vol, trending, high_vol)
- Trade Journal AI (Claude Haiku analysis)
- Email Alerts via Resend API
- Analytics API (equity curve, correlation)
- Walk-Forward Optimization endpoint + frontend UI
- Analytics page (EquityCurve, MetricsGrid, CorrelationMatrix)

### Phase 6: Live Trading & Hardening (Commits `2bd97d6` → `79baeb3`)

**What was built:**
- **DB Models**: Order (17 cols), Position (14 cols), BacktestResult (13 cols)
- **Broker Adapters**: BrokerAdapter ABC, PaperAdapter, CCXTAdapter, BrokerRouter
- **Encryption + Broker API**: Fernet encryption for credentials, CRUD endpoints
- **DB-Backed Execution**: PositionManager, OrderExecutor, CandleStorage all async SQLAlchemy
- **Celery Tasks**: Ingestion, pipeline, execution, polling, position management, alerts
- **Real-Time**: Redis subscriber + WebSocket broadcasting for signals/prices/trades
- **Hardening**: Circuit breaker, rate limiting, structured logging, request IDs
- **Production Docker**: Multi-stage Dockerfile, 5-service docker-compose.prod.yml

### Phase 7: AI Advisor & Risk Management (Post-commit, uncommitted)

> This phase represents all work done after Phase 6 was committed. All changes are currently uncommitted.

#### 7a. AI Advisor System (`app/advisor/`)

**New module** — Complete AI-powered trading advisor:

1. **Claude Client** (`advisor/claude_client.py`):
   - Centralized client with 3 model tiers: FAST (Haiku), DEEP (Sonnet), EXPERT (Opus)
   - Built-in response caching (Redis, configurable TTL)
   - Daily API call limits via Redis counter
   - Automatic usage metering — all calls record tokens + cost to DB
   - Sync and async paths

2. **AI Planner** (`advisor/planner.py`):
   - Fully autonomous — analyzes market conditions and determines ALL optimal strategy parameters
   - No presets, no human risk selection — AI decides everything from market profile
   - Selects 3–15 crypto pairs from scored candidates via Claude
   - Controls pipeline sensitivity + risk management + timeframes + risk features
   - Returns None when Claude unavailable — system does not generate plans without AI

3. **Signal Quality Evaluator** (`advisor/signal_quality.py`):
   - Claude-powered second-opinion on every signal
   - Assesses 14 confluence factors, candle patterns, multi-timeframe alignment
   - Returns quality score (0–100), recommendation (strong_confirm/confirm/caution/reject)
   - Position size adjustment factor

4. **Multi-Timeframe Analyzer** (`advisor/multi_tf_analyzer.py`):
   - Synthesizes 1h + 4h + 1d data for timeframe alignment
   - Returns confidence score + alignment classification (aligned/mixed/conflicting)

5. **Risk Tuner** (`advisor/risk_tuner.py`):
   - Analyzes recent trades (5+ closed), recommends risk parameter adjustments
   - Conservative: max 20% change per parameter per cycle
   - **Only tunes risk management params**: min_confluence, max_risk_per_trade, max_daily_loss, atr_sl_multiplier, min_risk_reward
   - **Never touches pipeline sensitivity params** (min_trigger_count, trigger_lookback_candles, ema_slope_threshold) — those are strategy identity set by the AI Advisor
   - If there aren't enough trades, does nothing — zero trades is correct behavior when market doesn't match
   - No adjustments when Claude unavailable — system does not modify parameters without AI

6. **Feedback Synthesizer** (`advisor/feedback_synthesizer.py`):
   - Analyzes last 50 trades for recurring patterns (symbol losses, low-confluence failures)
   - Generates FeedbackRule objects via Claude (returns empty when Claude unavailable)
   - Rules expire after 30 days

7. **Pattern Analyzer** (`advisor/pattern_analyzer.py`):
   - Deep trade history analysis via Claude
   - Returns metrics, patterns, strengths, weaknesses, prioritized recommendations

8. **Cost Tracking** (`advisor/pricing.py`, `advisor/anthropic_admin.py`):
   - Static pricing lookup for Haiku ($1/$5), Sonnet ($3/$15), Opus ($5/$25) per million tokens
   - Dual-source architecture: Anthropic Admin API for real billing data (when admin key available), local `ai_insights` table as fallback
   - Prepaid credit management via Redis (manual entry from Anthropic console)
   - Daily cost histogram chart, model/feature breakdown, recent call log
   - Admin API requires `sk-ant-admin-...` key (not available on individual Anthropic plans; code is dormant until key is configured)

#### 7b. Advanced Risk Management

**8 configurable risk features** added to strategy config:

| # | Feature | Config Keys | Description |
|---|---------|-------------|-------------|
| 1 | Trailing Stop | `trailing_stop_enabled`, `atr_trail_multiplier` | ATR-based trailing stop-loss |
| 2 | Drawdown Breaker | `drawdown_breaker_enabled`, `max_drawdown_pct` | Circuit breaker halts trading at drawdown limit |
| 3 | Kelly Criterion | `kelly_enabled`, `kelly_fraction`, `kelly_min_trades`, `kelly_lookback` | Dynamic position sizing from win/loss history |
| 4 | Break-Even Stop | `break_even_enabled`, `break_even_r_multiple` | Moves SL to entry after reaching R-multiple |
| 5 | Time Stop | `max_hold_hours`, `time_stop_profit_threshold_pct` | Closes positions after max hold time |
| 6 | CPPI | `cppi_enabled`, `cppi_multiplier`, `cppi_max_drawdown_pct` | Portfolio insurance — scales exposure based on drawdown cushion |
| 7 | Correlation Monitor | `correlation_monitor_enabled`, `correlation_threshold`, `correlation_auto_reduce` | Reduces correlated positions automatically |

**Strategy presets** (legacy, still in code but AI Planner now determines all parameters autonomously):
- **Conservative Swing** — min_confluence: 70, max_risk: 1%, CPPI enabled, break-even at 1.5R
- **Balanced Momentum** — min_confluence: 55, max_risk: 2%, Kelly enabled, trailing stops
- **Aggressive Scalper** — min_confluence: 40, max_risk: 3%, all features enabled

#### 7c. Feedback Filter Layer (`engine/layers/feedback_filter.py`) — NOW ACTIVE

Pipeline layer that applies learned FeedbackRule objects as pre-signal filter:
- **Wired into pipeline** (`tasks/run_pipeline.py`): called after BUY/SELL signal, before persistence
- `should_skip(symbol, regime, db, strategy_id)` → blocks signals matching `avoid_pattern` rules
- `get_confluence_override(symbol, regime, db, strategy_id)` → raises confluence threshold from `adjust_param` rules
- Empty rules table → all signals pass through (safe default)

#### 7c-ii. AI Autonomous Self-Learning Loop — ACTIVE

The system now has a fully autonomous self-learning loop:

1. **Pipeline** (every 5min): Generates signals → FeedbackFilter applies learned rules → AI enrichment → reject low-quality signals
2. **Pattern Analysis** (02:30 UTC daily): Deep analysis via Claude → stores patterns/recommendations in Redis
3. **Risk Tuner** (03:00 UTC daily): Reads pattern context from Redis + trade metrics → adjusts strategy.config parameters (max 20%/cycle)
4. **Feedback Synthesis** (04:00 UTC daily): Analyzes trade history → generates FeedbackRule objects (30-day expiry) → rules applied by FeedbackFilter

**Key behaviors:**
- AI `reject` signals are now honored in live mode (not just backtests) — signal saved as `status="rejected"`
- FeedbackFilter runs before signal persistence — bad patterns are blocked before execution
- Pattern Analyzer feeds directly into Risk Tuner via Redis (no user-facing display)
- Trade Journal API removed — pattern analysis is now system-internal only

**Core principle — strategy parameter integrity:**
The AI Advisor chose the strategy parameters for a reason. If the market doesn't match, zero trades is the correct outcome — not a problem to "fix." The Risk Tuner only adjusts risk management params based on actual trade results. Pipeline sensitivity params are strategy identity and are never auto-loosened or overridden.

#### 7d. AI Enrichment in Pipeline (`tasks/run_pipeline.py`)

The signal pipeline now enriches every trade signal with AI analysis (non-blocking):
1. Multi-timeframe confidence + alignment check
2. Signal quality score (0–100) + recommendation
3. Position size adjustment factor from AI

New columns on Signal model: `ai_quality_score`, `ai_reasoning`, `ai_recommendation`, `mtf_confidence`, `mtf_alignment`

#### 7e. Execution Risk Checks (`tasks/execute_signals.py`)

Pre-execution checks added:
- **Drawdown breaker**: Queries DrawdownBreaker, reduces or blocks sizing
- **Correlation penalty**: Reduces position size for correlated holdings
- Both are config-driven (opt-in per strategy)

#### 7f. Portfolio Backtester (`backtest/portfolio_runner.py`)

Runs portfolio-level backtests across all symbols in a strategy:
- Divides capital equally across symbols
- Runs engine per symbol, aggregates equity curves
- Returns per-symbol + portfolio-level metrics (return, Sharpe, Sortino, max drawdown)

#### 7g. Data Models (`models/ai_insight.py`)

Two new SQLAlchemy models:
- **AIInsight**: Audit trail for all AI API calls (type, model, tokens, latency, cost_usd, reasoning, result_json)
- **FeedbackRule**: Auto-generated trading rules (type, conditions, confidence, is_active, expires_at)

#### 7h. Frontend Restructure

**Major UI overhaul** — consolidated from 9 pages to 8 workflow-oriented pages:

| Route | Page | Description |
|-------|------|-------------|
| `/` | Dashboard | StatsCards, PriceChart (6 timeframes), RegimeWidget, SignalFeed, PositionsTable |
| `/advisor` | AI Advisor | 3-step workflow: Scan Market → Generate Plan → Deploy Strategy. Master-detail layout with scan history sidebar |
| `/strategies` | Strategies | List deployed strategies with performance metrics (P&L, win rate, Sharpe). Activate/deactivate/delete |
| `/strategies/:id` | Strategy Detail | Signals tab (paginated signal table) + Validation tab (integrated backtest) |
| `/backtest` | Backtest | Standalone strategy validation — test deployed strategies or AI plans |
| `/trades` | Trades | Trade history, execution log, performance metrics |
| `/analytics` | Analytics | Equity curve, metrics grid, correlation matrix |
| `/settings` | Settings | 3 tabs: Connections (broker API keys), Alerts (email config), AI Usage (cost tracking) |

**Sidebar navigation:** Dashboard → AI Advisor → Strategies → Trades → Analytics → Settings

**Pages removed** (redirected to new locations):
- `/signals` → `/strategies`
- `/config` → `/strategies`
- `/journal` → `/trades`
- `/keys` → `/settings`
- `/guide` → `/` (HelpDrawer in layout header)

**New components:**
- `StrategyBacktestForm` / `StrategyBacktestResults` — Strategy-aware backtest UI
- `HelpDrawer` — Slide-out markdown user guide
- `AiUsageTab` — Claude API cost dashboard with daily charts, credit management, call logs

**New hooks:**
- `useAiUsage` — AI cost/usage data
- `useAlertConfig` — Alert preferences CRUD
- `useStrategyBacktest` — Run strategy backtests

#### 7i. Infrastructure & Bug Fixes (2026-03-02)

See `docs/SESSION-CHANGELOG-2026-03-02.md` for full details:

- **Docker Compose**: Added `worker` and `beat` services to dev compose (5 services total)
- **Ingestion**: Expanded from 2 to 6 timeframes (1m, 5m, 15m, 1h, 4h, 1d)
- **Candle Storage**: Replaced row-by-row upsert with bulk PostgreSQL `ON CONFLICT DO UPDATE` — concurrent-safe and faster
- **Pipeline Logging**: Added `block_reason` to all pipeline output for debugging
- **Broker UI**: Removed non-functional paper mode from Settings connect form — live-only
- **DB Migrations**: 3 new Alembic migrations (AI columns, AI insights table, cost_usd column)

---

## All API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Health check (DB + Redis) |
| POST | `/api/auth/register` | No | Create user account |
| POST | `/api/auth/login` | No | Login, returns JWT tokens |
| POST | `/api/auth/refresh` | No | Refresh access token |
| GET | `/api/signals` | Yes | List signals (limit/offset) |
| GET | `/api/signals/{id}` | Yes | Get signal by ID |
| POST | `/api/signals/generate` | Yes | Generate new signal for symbol |
| GET | `/api/trades` | Yes | List trades (limit/offset) |
| GET | `/api/trades/{id}` | Yes | Get trade by ID |
| GET | `/api/trades/stats` | Yes | Trade statistics summary |
| GET | `/api/strategies` | Yes | List strategies |
| GET | `/api/strategies/presets` | Yes | List strategy presets |
| POST | `/api/strategies` | Yes | Create strategy |
| PUT | `/api/strategies/{id}` | Yes | Update strategy |
| DELETE | `/api/strategies/{id}` | Yes | Delete strategy |
| PUT | `/api/strategies/{id}/activate` | Yes | Toggle strategy active state |
| POST | `/api/strategies/{id}/tune` | Yes | AI risk tuning |
| GET | `/api/strategies/{id}/feedback-rules` | Yes | List feedback rules |
| POST | `/api/strategies/{id}/feedback-rules/{rule_id}/toggle` | Yes | Toggle feedback rule |
| POST | `/api/strategies/{id}/synthesize-feedback` | Yes | Generate feedback rules |
| GET | `/api/market/symbols` | No | Available trading symbols |
| GET | `/api/market/candles/{symbol}/{tf}` | Yes | Candle data from DB |
| GET | `/api/engine/status` | No | Engine running status |
| POST | `/api/backtests` | Yes | Run single backtest (persisted) |
| GET | `/api/backtests` | Yes | List past backtests from DB |
| POST | `/api/backtests/optimize` | Yes | Run walk-forward optimization |
| POST | `/api/backtests/strategy` | Yes | Portfolio backtest (all symbols) |
| GET | `/api/positions` | Yes | List open positions (DB-backed) |
| GET | `/api/positions/account` | Yes | Account state (equity, PnL, open count) |
| POST | `/api/positions/{id}/close` | Yes | Close a position (creates Trade row) |
| POST | `/api/broker` | Yes | Store encrypted broker connection |
| GET | `/api/broker` | Yes | List broker connections (masked) |
| DELETE | `/api/broker/{id}` | Yes | Remove broker connection |
| GET | `/api/alerts/config` | Yes | Get alert configuration |
| PUT | `/api/alerts/config` | Yes | Update alert configuration |
| GET | `/api/analytics/equity` | Yes | Equity curve + risk metrics |
| GET | `/api/analytics/correlation` | Yes | Symbol pair correlation |
| GET | `/api/advisor/scan` | Yes | AI market scan |
| POST | `/api/advisor/plan` | Yes | Generate investment plan |
| POST | `/api/advisor/deploy` | Yes | Deploy plan as strategy |
| GET | `/api/ai-usage` | Yes | AI usage & cost summary (dual-source: Anthropic Admin API or local) |
| PUT | `/api/ai-usage/credit` | Yes | Update prepaid credit amount |
| WS | `/ws/signals` | No | Real-time signal stream |
| WS | `/ws/prices` | No | Real-time price stream |
| WS | `/ws/trades` | No | Real-time trade stream |

---

## Frontend Routes

| Path | Page | Component |
|------|------|-----------|
| `/login` | Login | `LoginPage` |
| `/register` | Register | `RegisterPage` |
| `/` | Dashboard | `DashboardPage` |
| `/advisor` | AI Advisor | `AdvisorPage` |
| `/strategies` | Strategies | `StrategiesPage` |
| `/strategies/:id` | Strategy Detail | `StrategyDetailPage` |
| `/backtest` | Backtest | `BacktestPage` |
| `/trades` | Trades | `TradesPage` |
| `/analytics` | Analytics | `AnalyticsPage` |
| `/settings` | Settings | `SettingsPage` |

---

## Database Models (11 total)

| Model | Table | Key Columns |
|-------|-------|-------------|
| User | users | id, email, hashed_password, alert_config (JSON) |
| Signal | signals | id, strategy_id, symbol, timeframe, direction, entry/SL/TP, confluence_score, regime, status, ai_quality_score, ai_reasoning, ai_recommendation, mtf_confidence, mtf_alignment |
| Trade | trades | id, user_id, symbol, side, entry_price, exit_price, pnl, position_size |
| Strategy | strategies | id, user_id, name, config (JSON), is_active |
| Order | orders | id, user_id, signal_id, broker_order_id, status, filled_price |
| Position | positions | id, user_id, order_id, entry_price, current_price, sl, tp, unrealized_pnl |
| Candle | candles | time, symbol, exchange, timeframe, OHLCV (composite PK) |
| BrokerConnection | broker_connections | id, user_id, broker, api_key_enc, api_secret_enc, is_paper |
| BacktestResult | backtest_results | id, user_id, strategy_id, metrics (JSON), trade_count |
| AIInsight | ai_insights | id, insight_type, signal_id, strategy_id, model, tokens_in, tokens_out, latency_ms, cost_usd, reasoning, result_json |
| FeedbackRule | feedback_rules | id, strategy_id, rule_type, description, conditions (JSON), confidence, is_active, expires_at |

**Alembic migration chain:** `23e8e2f4176c` → `a1b2c3d4e5f6` → `b2c3d4e5f6a7` → `c3d4e5f6a7b8` → `d4e5f6a7b8c9`

---

## Configuration (Environment Variables)

All backend env vars use `SF_` prefix. Set in `.env` file at `backend/.env`.

| Variable | Default | Description |
|----------|---------|-------------|
| `SF_DATABASE_URL` | `postgresql+asyncpg://signalforge:signalforge@localhost:5432/signalforge` | PostgreSQL connection |
| `SF_REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `SF_CELERY_BROKER_URL` | `redis://redis:6379/1` | Celery broker |
| `SF_CELERY_RESULT_BACKEND` | `redis://redis:6379/2` | Celery results |
| `SF_JWT_SECRET` | `dev-secret-change-in-production` | JWT signing secret |
| `SF_JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `SF_JWT_EXPIRY_MINUTES` | `30` | Access token expiry |
| `SF_JWT_REFRESH_EXPIRY_DAYS` | `7` | Refresh token expiry |
| `SF_ANTHROPIC_API_KEY` | `` | Claude API key (AI advisor, signal quality, risk tuner, pattern analysis) |
| `SF_ANTHROPIC_ADMIN_API_KEY` | `` | Anthropic Admin API (cost tracking) |
| `SF_RESEND_API_KEY` | `` | Resend email API key |
| `SF_RESEND_DOMAIN` | `signalforge.dev` | Email sender domain |
| `SF_APP_NAME` | `SignalForge` | App display name |
| `SF_DEBUG` | `True` | Debug mode |
| `SF_ENCRYPTION_KEY` | `` | Fernet key for broker credential encryption |
| `SF_CORS_ORIGINS` | `["http://localhost:5173"]` | CORS allowed origins |
| `VITE_API_URL` | `http://localhost:8000/api` | Frontend API base URL |

**AI Feature Flags** (all in config.py):

| Variable | Default | Description |
|----------|---------|-------------|
| `ai_signal_quality_enabled` | `True` | Enable AI signal quality evaluation |
| `ai_risk_tuning_enabled` | `True` | Enable adaptive risk parameter tuning |
| `ai_feedback_loop_enabled` | `True` | Enable feedback rule synthesis |
| `ai_multi_timeframe_enabled` | `True` | Enable multi-timeframe analysis |
| `ai_pattern_analysis_enabled` | `True` | Enable pattern analysis |
| `ai_signal_quality_cache_ttl` | `300` | Signal quality cache TTL (seconds) |
| `ai_risk_tuning_interval_hours` | `24` | Hours between risk tuning runs |
| `ai_max_daily_api_calls` | `500` | Max Claude API calls per day |
| `ai_prepaid_credit_usd` | `0.0` | Prepaid AI credit balance |

---

## Celery Beat Schedule (13 tasks)

| Task | Schedule | Description |
|------|----------|-------------|
| `ingest_candles` | Every 60s | Fetch OHLCV for all symbols × 6 timeframes (1m, 5m, 15m, 1h, 4h, 1d) |
| `run_signal_pipeline` | Every 5 min | Run 6-layer pipeline + FeedbackFilter + AI enrichment per symbol |
| `execute_pending_signals` | Every 30s | Execute pending signals with risk checks via PaperAdapter |
| `poll_order_status` | Every 15s | Check order status, open positions on fill |
| `manage_positions` | Every 60s | Monitor SL/TP/trailing/time-stop, close positions |
| `reconcile_broker_state` | Every 5 min | Reconcile broker state (no-op in paper mode) |
| `check_correlations` | Every 5 min | Check cross-symbol correlations |
| `flush_ai_usage` | Every 60s | Flush AI usage metrics from Redis to DB |
| `send_daily_summary` | Daily 17:00 UTC | Aggregate trades, send email summary |
| `train_hmm_regime` | Sundays 02:00 UTC | Retrain HMM regime models |
| `periodic_pattern_analysis` | Daily 02:30 UTC | Deep pattern analysis → Redis cache for Risk Tuner |
| `adaptive_risk_tuning` | Daily 03:00 UTC | AI-driven risk parameter adjustment (reads pattern context) |
| `synthesize_feedback_rules` | Daily 04:00 UTC | Generate feedback rules from trade patterns |

**Self-learning loop schedule:** Pattern Analysis (02:30) → Risk Tuner (03:00) → Feedback Synthesis (04:00) → FeedbackFilter (every 5min pipeline run)

---

## Development Commands

```bash
# Backend — Docker (recommended for development)
cd backend
docker.exe compose up -d                   # Start all 5 services (db, redis, api, worker, beat)
docker.exe compose logs worker --tail=30   # Check worker logs
docker.exe compose logs beat --tail=20     # Check beat logs
docker.exe compose restart worker beat     # Restart after code changes

# Backend — Local (testing/linting)
cd backend
.venv/Scripts/python.exe -m pytest -q        # Run tests
.venv/Scripts/python.exe -m ruff check .     # Lint

# Frontend
cd frontend
npm run dev          # Dev server :5173 (password gate: "signalforge")
npx vitest run       # Tests
npm run lint         # ESLint
npx tsc -b --noEmit  # TypeScript check
npm run build        # Production build

# Production Docker
docker compose -f docker-compose.prod.yml up -d  # All 5 services

# Check candle data
docker.exe compose exec db psql -U signalforge -c \
  "SELECT timeframe, COUNT(*) FROM candles WHERE symbol='BTC/USDT' GROUP BY timeframe ORDER BY timeframe;"
```

> **Note:** Use `docker.exe` (not `docker`) on WSL2 with Docker Desktop for Windows.

---

## Current System State (as of 2026-03-02)

### Running Services
| Service | Status | Port |
|---------|--------|------|
| db (TimescaleDB) | Healthy | 5432 |
| redis | Healthy | 6379 |
| api (FastAPI) | Running | 8000 |
| worker (Celery) | Running | — |
| beat (Celery) | Running | — |

### Active Strategy
- **Name:** AI Advisor — Conservative Swing
- **Symbols:** 15 (NEAR, MORPHO, AIXBT, ZRO, ENSO, FORM, SUN, BTC, DOGE, JUP, ALICE, XRP, SAHARA, OG, 1000SATS — all `/USDT`)
- **Timeframe:** 4h
- **min_confluence:** 70
- **Status:** Active, no trades yet — all symbols blocked by chaotic_regime / no_trend / low_confluence

### Database
- **Candles:** ~55,000+ rows (15+ symbols × 6 timeframes × ~500 each)
- **Signals:** Growing (all NO_TRADE currently)
- **Strategies:** 1 active
- **Orders/Positions/Trades:** 0 (conditions not yet met)

---

## Known Issues & Future Work

1. **Broker connections not wired to execution** — `execute_signals.py` always creates a fresh PaperAdapter. Stored broker connections are never read. Needs wiring for live trading.
2. **HMM convergence warnings** — Some symbols show `Model is not converging` for HMM regime detection. May need more training data or parameter adjustment.
3. **WSL2 clock drift** — Beat logs show 1-hour drift between WSL2 and Windows Docker. Does not affect functionality.
4. **2 pre-existing test failures** — `test_evaluate_sync_fallback_on_none` (AI evaluation edge case) and `test_strategy_backtest_conservative_preset` (`_make_sample_plan()` keyword mismatch). Not blocking.

---

## Commit History (91 commits on main)

### Phase 1–6: See git log (88 commits from `d872185` to `79baeb3`)

### Phase 7+: Commits `033faa0` and `dc52284`
- AI Advisor module (9 files: claude_client, planner, signal_quality, risk_tuner, feedback_synthesizer, multi_tf_analyzer, pattern_analyzer, pricing, anthropic_admin)
- AI Usage & Cost Tracking: dual-source API (`GET /api/ai-usage`, `PUT /api/ai-usage/credit`), frontend dashboard with daily cost chart, model/feature breakdown, credit management
- `flush_ai_usage` Celery task: flushes sync-path usage records from Redis queue to DB every 60s
- Advanced risk management (8 configurable features)
- Feedback filter pipeline layer — **now wired into pipeline** (was dormant)
- Portfolio backtester
- AIInsight + FeedbackRule models + 3 Alembic migrations
- Frontend restructure (5 pages removed, 4 new pages, 3 new components, 3 new hooks)
- AI Planner redesigned — fully autonomous, no presets, AI picks all parameters from market conditions
- Docker Compose worker + beat services
- Candle ingestion expanded to 6 timeframes
- Bulk upsert storage optimization
- Pipeline block_reason logging
- Broker connect form cleanup (paper mode removed)
- **Self-learning loop activated:** FeedbackFilter wired, AI reject honored in live mode, pattern analysis → Risk Tuner, feedback synthesis daily
- **Trade Journal deprecated:** Router removed from main.py, frontend cleaned, useJournal.ts deleted
- `periodic_pattern_analysis` Celery task: stores pattern insights in Redis for Risk Tuner consumption
- 4 new test files (test_backtest_strategy, test_claude_client, test_risk_tuner, test_signal_quality)
- **Alpaca broker removed** (`dc52284`): adapter deleted, `alpaca-py` dependency removed, config/env vars cleaned, all docs updated, Binance-only via CCXT
