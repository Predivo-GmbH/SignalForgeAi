# SignalForge — Project Status (Phases 1–5 Complete)

> **For Claude:** Use this document as the single source of truth when starting Phase 6.
> Read this BEFORE writing any code. It tells you everything that exists.

**Last updated:** 2026-02-28
**Current commit:** `f144c59` on `main` (48 commits total)
**Quality gates:** 197 backend tests, 37 frontend tests, 0 lint errors (ruff + eslint), TypeScript clean, build succeeds (554KB JS, 30KB CSS)

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
| Backend | Python + FastAPI | 3.12 / 0.115 |
| ORM | SQLAlchemy 2.0 (async) + Alembic | 2.0.36 |
| Database | PostgreSQL 16 + TimescaleDB | via Docker |
| Cache/Broker | Redis 7 | via Docker |
| Task Queue | Celery 5.4 | redis broker |
| ML | hmmlearn (HMM), numpy, pandas | 0.3+ |
| AI | Anthropic SDK (Claude Haiku 4.5) | 0.52+ |
| Email | Resend | 2.0+ |
| Market Data | CCXT 4.4 | exchange connectors |
| Testing | pytest 8.3 (backend) / Vitest 4.0 (frontend) | |
| Linting | ruff (backend) / eslint 9 (frontend) | |
| CI | GitHub Actions | on push/PR to main |

---

## Project Root: `C:\Business\Internal Projects\day-trading`

```
day-trading/
├── .github/workflows/ci.yml     # Backend lint+test, frontend build
├── backend/
│   ├── app/                     # FastAPI application (62 .py files)
│   │   ├── api/                 # REST endpoints (10 routers)
│   │   ├── auth/                # JWT auth (register, login, refresh)
│   │   ├── backtest/            # Engine + optimizer
│   │   ├── core/                # Database, Redis, pub/sub, email
│   │   ├── data/                # CCXT ingestion, candle storage
│   │   ├── engine/              # 6-layer signal pipeline
│   │   │   └── layers/          # regime, trend, zones, confluence, triggers, risk, hmm_regime
│   │   ├── execution/           # Order executor, position manager, risk checks
│   │   ├── models/              # SQLAlchemy models (user, signal, trade, candle, strategy)
│   │   ├── tasks/               # Celery tasks (backtest, HMM training)
│   │   ├── ws/                  # WebSocket hub (signals + prices)
│   │   ├── config.py            # Settings with SF_ env prefix
│   │   ├── main.py              # FastAPI app with all routers
│   │   └── worker.py            # Celery worker entry
│   ├── tests/                   # 33 test files, 197 tests
│   ├── scripts/                 # run_backtests.py
│   ├── docker-compose.yml       # TimescaleDB + Redis
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/          # Reusable UI (14 components)
│   │   │   ├── analytics/       # EquityCurve, MetricsGrid, CorrelationMatrix
│   │   │   ├── backtest/        # BacktestForm, BacktestResults, WalkForwardForm, WalkForwardResults
│   │   │   ├── dashboard/       # PriceChart, StatsCards, SignalFeed, PositionsTable, RegimeWidget
│   │   │   ├── layout/          # AppLayout, Sidebar, Topbar
│   │   │   └── ui/              # Badge, DataTable, Pagination
│   │   ├── hooks/               # 12 data hooks
│   │   ├── lib/                 # api, auth, cn, colors, query, sidebar, theme, ws
│   │   ├── pages/               # 9 pages + tests
│   │   ├── App.tsx              # Router configuration
│   │   ├── main.tsx             # Entry point
│   │   └── index.css            # Theme tokens (dark/light)
│   ├── package.json
│   └── tsconfig.app.json
├── docs/plans/                  # 6 plan documents
├── CLAUDE.md                    # Project rules
├── SignalForge-Technical-Plan.md # Original design spec
└── kraken-reference/            # UI inspiration screenshots
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

**Key files:**
- `backend/app/auth/` — JWT auth system
- `backend/app/data/` — CCXT ingestion + candle storage
- `backend/app/engine/indicators.py` — 8 technical indicators
- `backend/app/backtest/engine.py` — BacktestEngine with full metrics
- `frontend/src/components/PasswordGate.tsx` — Password: `signalforge`

### Phase 2: Signal Engine (Commits `e7f23d2` → `86bb184`)

**What was built:**
- Complete 6-layer signal pipeline:
  - **Layer 0 — RegimeDetector**: ADX + ATR percentile → Regime enum (TRENDING, RANGING, TRANSITIONING, CHAOTIC). CHAOTIC blocks all trades.
  - **Layer 1 — TrendFilter**: Multi-timeframe EMA + ADX + Ichimoku → Trend direction + strength
  - **Layer 2 — ZoneIdentifier**: Fibonacci retracements, S/R from swing pivots, VWAP zones → EntryZone list
  - **Layer 3 — ConfluenceScorer**: 9 weighted factors (trend alignment, zone strength, momentum, etc.) → 0-100 score. Threshold: 40
  - **Layer 4 — TriggerDetector**: 5 trigger types (EMA crossover, RSI reversal, MACD cross, Bollinger bounce, volume spike). Needs 2+ confirmations.
  - **Layer 5 — RiskManager**: ATR-based stops, Fibonacci targets (TP1/TP2/TP3), Kelly-criterion position sizing
- **Layer 6 — ReversalMonitor**: 4 severity levels (caution, warning, critical, exit), actions from tighten_stop to close_position
- **SignalPipeline orchestrator** (`engine/pipeline.py`): Chains all 6 layers, early-exits on blocks, picks best zone by confluence
- **Signal + Trade DB models** with SQLAlchemy
- **Walk-Forward Optimizer** (`backtest/optimizer.py`): Grid search with k-fold train/test splits, WFOResult
- **Backtest results**: EUR/USD, BTC/USDT, SPY tested (documented in `docs/plans/`)

**Pipeline flow:**
```
Candles → Regime (block if CHAOTIC)
       → Trend (block if neutral)
       → Zones (skip if none)
       → Confluence (skip if < 40)
       → Triggers (skip if < 2 confirmations)
       → Risk (position sizing, stops, targets)
       → Signal
```

### Phase 3: API & Paper Trading (Commits `6b39c7f` → `d02d6b9`)

**What was built:**
- **10 API routers** all under `/api` prefix:
  - `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/refresh`
  - `GET /api/signals`, `GET /api/signals/{id}`, `POST /api/signals/generate`
  - `GET /api/trades`, `GET /api/trades/{id}`, `GET /api/trades/stats`
  - `GET|POST|PUT|DELETE /api/strategies`, `PUT /api/strategies/{id}/activate`
  - `GET /api/market/symbols`, `GET /api/engine/status`
  - `POST /api/backtests`, `GET /api/backtests`
  - `GET /api/positions`, `POST /api/positions/{id}/close`
- **Auth dependency**: `get_current_user` extracts user_id from JWT Bearer token
- **Order Executor**: Pre-trade risk checks (daily loss limit, max positions, cooldown) + paper mode via Alpaca SDK
- **PositionManager**: Track open positions, trail stops, close with PnL calculation
- **Redis pub/sub**: Signal and price channels for real-time broadcasting
- **Celery setup**: Async backtest tasks, Redis broker
- **WebSocket hub**: `/ws/signals` and `/ws/prices` for real-time streaming
- **Strategies CRUD API**: Full CRUD with activate/deactivate toggle

**Auth flow:**
1. `POST /api/auth/register` → creates user, returns tokens
2. `POST /api/auth/login` → validates credentials, returns `{ access_token, refresh_token }`
3. All protected endpoints require `Authorization: Bearer <token>` header
4. `get_current_user` dependency extracts and validates JWT → returns `user_id: str`

### Phase 4: Frontend Dashboard (Commits `540ca66` → `91b3377`)

**What was built:**
- **Router + Auth**: React Router DOM with protected routes, Zustand auth store (persisted to `sf-auth` localStorage), login/register pages
- **Layout shell**: Collapsible sidebar (8 nav items), topbar with theme toggle + logout
- **9 pages**:
  1. **Dashboard** (`/`) — StatsCards (4 metrics), PriceChart (lightweight-charts candlestick), RegimeWidget, SignalFeed, PositionsTable
  2. **Signals** (`/signals`) — DataTable with 9 columns, Generate Signal button, confluence progress bars, pagination
  3. **Trades** (`/trades`) — Stats summary (4 cards) + trade history table (11 columns), P&L coloring
  4. **Backtest Lab** (`/backtest`) — Split layout: BacktestForm (left) + BacktestResults (right)
  5. **Journal** (`/journal`) — Was placeholder, now real (see Phase 5)
  6. **Strategy Config** (`/config`) — Strategy cards with CRUD, activate toggle
  7. **API Keys** (`/keys`) — Broker connection cards (Alpaca, Binance)
  8. **Analytics** (`/analytics`) — Added in Phase 5
  9. **Login/Register** (`/login`, `/register`)
- **12 hooks**: useSignals, useTrades, useTradeStats, usePositions, useAccountState, useEngineStatus, useBacktest, useStrategies, useSymbols, useSignalStream, usePriceStream, useWebSocket
- **WebSocket manager** (`lib/ws.ts`): Auto-reconnect, subscribe/unsubscribe pattern
- **API client** (`lib/api.ts`): Typed fetch wrapper with Bearer auth, 401 auto-logout

**Theme system** (CSS custom properties in `index.css`):
```
Light: bg-base=#F7F5F2, bg-surface=#FFFFFF, accent=#7B61FF, text=#1A1A2E
Dark:  bg-base=#0B0B14, bg-surface=#141420, accent=#7B61FF, text=#F0F0F5
Semantic: positive=#00D68F, negative=#FF4D6A, warning=#FFB020
```

**Sidebar navigation order:**
Dashboard → Signals → Trades → Backtest Lab → Journal → Analytics → Strategy → API Keys

### Phase 5: Advanced Features (Commits `5eede6a` → `f144c59`)

**What was built:**

#### Backend (6 commits)
1. **Sortino + Calmar ratios** in `backtest/engine.py` — added `_sortino()` and `_calmar()` methods to BacktestEngine metrics
2. **HMM Regime Detection** (`engine/layers/hmm_regime.py`):
   - `HMMRegimeModel` class with 3 states: `low_vol`, `trending`, `high_vol`
   - Features: log returns + ATR/price ratio + ADX
   - `fit()`, `predict_current()`, `state_probabilities()`, `serialize()`/`deserialize()`
   - Celery training task (`tasks/hmm_train.py`): trains on synthetic data, caches in Redis (7-day TTL)
3. **Trade Journal AI** (`api/journal.py`):
   - `POST /api/journal/analyze` — sends trade data to Claude Haiku 4.5, returns analysis/patterns/recommendations
   - `GET /api/journal/patterns` — aggregate pattern analysis from last 50 trades (rule-based: low confluence losses, tight stops, low R:R wins)
   - Gracefully degrades if `SF_ANTHROPIC_API_KEY` not set
4. **Email Alerts** (`api/alerts.py` + `core/email.py`):
   - `GET /api/alerts/config` + `PUT /api/alerts/config` — in-memory alert configuration
   - `build_signal_email()` + `build_daily_summary_email()` + `send_email()` via Resend API
   - Requires `SF_RESEND_API_KEY` and `SF_RESEND_DOMAIN`
5. **Analytics API** (`api/analytics.py`):
   - `GET /api/analytics/equity` — equity curve from closed trades with Sharpe/Sortino/Calmar ratios
   - `GET /api/analytics/correlation?symbol_a=X&symbol_b=Y` — Pearson return correlation (synthetic data for now)
6. **Walk-Forward Optimization endpoint** (`api/backtests.py`):
   - `POST /api/backtests/optimize` — WFORequest with param_grid, n_folds, train_pct → WFOResult with best_params, fold_results, out_of_sample_metrics

#### Frontend (3 commits)
1. **Journal page** — replaced placeholder with full AI journal:
   - Pattern Summary card (summary, top patterns as badges, areas to improve)
   - Recent Trades section with trade cards + per-trade "Analyze" button
   - Inline AI analysis display (analysis text, pattern badges, recommendation bullets)
   - Hooks: `useAnalyzeTrade()` mutation, `usePatternSummary()` query
2. **Walk-Forward UI** in Backtest Lab:
   - Tab toggle: "Single Backtest" / "Walk-Forward"
   - `WalkForwardForm.tsx`: symbol, timeframe, days, n-folds slider, train % slider
   - `WalkForwardResults.tsx`: best params card, OOS metrics, fold results table
   - Hook: `useRunWalkForward()` mutation
3. **Analytics page** (`/analytics`):
   - `EquityCurve.tsx` — lightweight-charts line chart, theme-aware
   - `MetricsGrid.tsx` — 6 metric cards (Total Return, Max Drawdown, Sharpe, Sortino, Calmar, data points)
   - `CorrelationMatrix.tsx` — two symbol dropdowns, correlation value with interpretation
   - Hook: `useEquityHistory()`, `useCorrelation()`
   - Added to Sidebar (BarChart2 icon) and App.tsx router

---

## All API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Health check |
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
| POST | `/api/strategies` | Yes | Create strategy |
| PUT | `/api/strategies/{id}` | Yes | Update strategy |
| DELETE | `/api/strategies/{id}` | Yes | Delete strategy |
| PUT | `/api/strategies/{id}/activate` | Yes | Toggle strategy active state |
| GET | `/api/market/symbols` | Yes | Available trading symbols |
| GET | `/api/engine/status` | Yes | Engine running status |
| POST | `/api/backtests` | Yes | Run single backtest |
| GET | `/api/backtests` | Yes | List past backtests (stub) |
| POST | `/api/backtests/optimize` | Yes | Run walk-forward optimization |
| GET | `/api/positions` | Yes | List open positions |
| POST | `/api/positions/{id}/close` | Yes | Close a position |
| POST | `/api/journal/analyze` | Yes | AI-analyze a trade (Claude Haiku) |
| GET | `/api/journal/patterns` | Yes | Aggregate pattern summary |
| GET | `/api/alerts/config` | Yes | Get alert configuration |
| PUT | `/api/alerts/config` | Yes | Update alert configuration |
| GET | `/api/analytics/equity` | Yes | Equity curve + risk metrics |
| GET | `/api/analytics/correlation` | Yes | Symbol pair correlation |
| WS | `/ws/signals` | No | Real-time signal stream |
| WS | `/ws/prices` | No | Real-time price stream |

---

## Frontend Routes

| Path | Page | Component |
|------|------|-----------|
| `/login` | Login | `LoginPage` |
| `/register` | Register | `RegisterPage` |
| `/` | Dashboard | `DashboardPage` |
| `/signals` | Signals | `SignalsPage` |
| `/trades` | Trades | `TradesPage` |
| `/backtest` | Backtest Lab | `BacktestPage` (tabs: Single / Walk-Forward) |
| `/journal` | Trade Journal | `JournalPage` |
| `/analytics` | Analytics | `AnalyticsPage` |
| `/config` | Strategy Config | `StrategyConfigPage` |
| `/keys` | API Keys | `ApiKeysPage` |

---

## Configuration (Environment Variables)

All backend env vars use `SF_` prefix. Set in `.env` file at `backend/.env`.

| Variable | Default | Description |
|----------|---------|-------------|
| `SF_DATABASE_URL` | `postgresql+asyncpg://signalforge:signalforge@localhost:5432/signalforge` | PostgreSQL connection |
| `SF_REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `SF_CELERY_BROKER_URL` | `redis://localhost:6379/1` | Celery broker |
| `SF_CELERY_RESULT_BACKEND` | `redis://localhost:6379/2` | Celery results |
| `SF_JWT_SECRET` | `dev-secret-change-in-production` | JWT signing secret |
| `SF_JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `SF_JWT_EXPIRY_MINUTES` | `30` | Access token expiry |
| `SF_JWT_REFRESH_EXPIRY_DAYS` | `7` | Refresh token expiry |
| `SF_ALPACA_API_KEY` | `` | Alpaca broker API key |
| `SF_ALPACA_API_SECRET` | `` | Alpaca broker secret |
| `SF_ALPACA_PAPER` | `True` | Use paper trading |
| `SF_ANTHROPIC_API_KEY` | `` | Claude API key (journal AI) |
| `SF_RESEND_API_KEY` | `` | Resend email API key |
| `SF_RESEND_DOMAIN` | `signalforge.dev` | Email sender domain |
| `SF_APP_NAME` | `SignalForge` | App display name |
| `SF_DEBUG` | `True` | Debug mode |
| `SF_CORS_ORIGINS` | `["http://localhost:5173"]` | CORS allowed origins |
| `VITE_API_URL` | `http://localhost:8000/api` | Frontend API base URL |

---

## Development Commands

```bash
# Backend
cd backend
docker compose up -d                        # Start TimescaleDB + Redis
.venv/Scripts/python.exe -m pytest -q        # Run 197 tests
.venv/Scripts/python.exe -m ruff check .     # Lint (0 errors)
.venv/Scripts/python.exe -m uvicorn app.main:app --reload  # Dev server :8000
python -m app.cli backtest --symbol BTC/USDT --timeframe 1h --days 30  # CLI

# Frontend
cd frontend
npm run dev          # Dev server :5173 (password gate: "signalforge")
npx vitest run       # Run 37 tests
npm run lint         # ESLint (0 errors)
npx tsc -b --noEmit  # TypeScript check
npm run build        # Production build (554KB JS, 30KB CSS)

# Full CI check
cd backend && .venv/Scripts/python.exe -m pytest -q && .venv/Scripts/python.exe -m ruff check .
cd ../frontend && npx vitest run && npm run lint && npx tsc -b --noEmit && npm run build
```

---

## Commit History (48 commits)

### Phase 1: Foundation
| Hash | Message |
|------|---------|
| `d872185` | chore: init repo with monorepo scaffold |
| `471ba78` | feat(frontend): Vite + React + TypeScript + Tailwind 4 scaffold with theme tokens |
| `8240a51` | feat(frontend): theme system, password gate, login page placeholder |
| `bb88915` | chore(frontend): add frontend .gitignore |
| `2d99433` | docs: add agent team handoff for Phase 1 |
| `05a6ebe` | infra: Docker Compose with TimescaleDB, Redis, and FastAPI |
| `abecce2` | ci: GitHub Actions for backend lint+test and frontend build |
| `ace1434` | feat(backend): FastAPI skeleton with health endpoint, config, and test setup |
| `3a339ee` | feat(backend): SQLAlchemy models and Alembic migrations setup |
| `154e0c2` | feat(backend): JWT auth with register, login, refresh endpoints |
| `8eb0681` | feat(backend): candle storage + CCXT ingestion pipeline |
| `8e1e30e` | feat(backend): indicator library + Layer 1 (TrendFilter) + Layer 2 (ZoneIdentifier) |
| `d310e8f` | feat(backend): backtest engine + CLI + data pipeline |
| `4b45991` | docs: add original technical plan |
| `e35b07a` | Merge branch 'worktree-agent-a751c186' |

### Phase 2: Signal Engine
| Hash | Message |
|------|---------|
| `e7f23d2` | docs: Phase 2 signal engine implementation plan |
| `feb2f42` | feat(backend): Layer 0 — RegimeDetector with ADX + ATR percentile consensus |
| `4252900` | feat(backend): Layer 3 — ConfluenceScorer with 9 weighted factors |
| `a5bb08d` | feat(backend): Layer 4 — TriggerDetector with 5 trigger types, 2+ confirmation rule |
| `7296cb6` | feat(backend): Layer 5 — RiskManager with ATR stops, Fib targets, position sizing |
| `9556673` | feat(backend): Layer 6 — ReversalMonitor with severity-based exit actions |
| `a869eb0` | feat(backend): SignalPipeline orchestrator + session/timing filters |
| `466e5be` | feat(backend): Signal + Trade DB models |
| `4864427` | feat(backend): full pipeline backtest + walk-forward optimization |
| `4c6ce07` | docs: Phase 2 backtest results across EUR/USD, BTC/USDT, SPY |
| `86bb184` | fix(backend): sort imports and remove unused import (ruff) |

### Phase 3: API & Paper Trading
| Hash | Message |
|------|---------|
| `6b39c7f` | docs: Phase 3 API & paper trading implementation plan |
| `432b2e8` | feat(backend): auth dependency (get_current_user) + Alpaca/Celery config |
| `a24083f` | feat(backend): Order Executor with pre-trade risk checks + paper mode |
| `edb5233` | feat(backend): Market data + engine status endpoints |
| `e717387` | feat(backend): Signals REST API — list, get, generate endpoints |
| `492d39f` | feat(backend): PositionManager — track, trail, close positions with PnL |
| `6fc2751` | feat(backend): Trades REST API — list, get, stats endpoints |
| `8f863f2` | feat(backend): Celery setup + async backtest task |
| `44e6ac1` | fix(backend): sanitise inf/NaN in backtest metrics for JSON serialization |
| `8fd2e8c` | feat(backend): Redis connection + signal/price pub/sub channels |
| `d672d35` | feat(backend): Strategies CRUD API with activate/deactivate |
| `2f186b2` | merge: resolve main.py conflict — register all API routers |
| `ccd58a6` | feat(backend): WebSocket hub — real-time signal and price streaming |
| `007ed54` | feat(backend): Phase 3 integration — positions API + full pipeline E2E test |
| `d02d6b9` | fix(backend): remove duplicate Celery config entries |

### Phase 4: Frontend Dashboard
| Hash | Message |
|------|---------|
| `540ca66` | docs: add Phase 4 frontend dashboard implementation plan |
| `7cf1952` | feat(frontend): install react-router-dom, @tanstack/react-query, lightweight-charts |
| `4dacac3` | feat(frontend): add API client, auth store, and query client |
| `14788a0` | feat(frontend): add router, auth pages, and protected routes |
| `bd249f5` | feat(frontend): add layout shell with sidebar, topbar, and app layout |
| `a436d3b` | feat(frontend): add all 7 pages — Dashboard, Signals, Trades, Backtest, Strategy, Keys, Journal |
| `e746d87` | feat(frontend): add WebSocket manager with signal and price stream hooks |
| `91b3377` | feat(frontend): wire all 7 real pages into router, remove PlaceholderPage |

### Phase 5: Advanced Features
| Hash | Message |
|------|---------|
| `5eede6a` | docs: add Phase 5 advanced features implementation plan |
| `74707c2` | feat(api): add Trade Journal AI endpoints with Claude Haiku analysis |
| `91c0b35` | feat(api): add email alerts via Resend with signal and daily summary emails |
| `631601f` | feat(api): add analytics endpoints with equity curve and correlation |
| `751842e` | feat(api): add walk-forward optimization endpoint to backtests |
| `0bcaaae` | feat(backtest): add Sortino and Calmar ratios to backtest metrics |
| `2eca352` | feat(engine): add HMM-based regime detection layer |
| `dfa1fda` | feat(frontend): add Trade Journal page and Walk-Forward Optimization tab |
| `7c1522c` | feat(frontend): add Analytics page with equity curve, metrics grid, and correlation analysis |
| `df9dc1b` | Merge branch 'worktree-agent-a435410d' |
| `f144c59` | fix: resolve all ruff lint errors — unused imports and line length |

---

## Phase 6: Live Trading & Hardening — PLANNED (Ready for Implementation)

**Design doc**: `docs/plans/2026-02-28-phase6-live-trading-design.md` (approved)
**Implementation plan**: `docs/plans/2026-02-28-phase6-implementation.md` (13 tasks, 5 waves)
**Commits**: `561e4d1` (design doc), `525b8c7` (implementation plan)

### Key Decisions Made
- **Approach**: Monolithic scheduler (Celery Beat within existing FastAPI + Celery backend)
- **Brokers**: Alpaca (stocks) + CCXT/Binance (crypto) behind unified BrokerAdapter ABC
- **Encryption**: Fernet symmetric via `SF_ENCRYPTION_KEY` for broker API credentials
- **Deployment**: Production Docker Compose (`docker-compose.prod.yml`) with 5 services

### What Phase 6 Builds
1. **Broker Adapter Layer**: ABC + AlpacaAdapter + CCXTAdapter + PaperAdapter + BrokerRouter
2. **DB-Backed Execution**: Order model, Position model (replace in-memory), BacktestResult model
3. **Celery Beat Tasks**: 8 scheduled tasks (ingest candles, run pipeline, execute signals, poll orders, manage positions, daily summary, HMM retrain, broker reconciliation)
4. **WebSocket Broadcasting**: Redis subscriber → ConnectionManager.broadcast() for signals/prices/trades
5. **Hardening**: Circuit breakers per broker, slowapi rate limiting, structlog JSON logging, enhanced health checks
6. **Production Docker**: Multi-stage Dockerfile, docker-compose.prod.yml (timescaledb + redis + api + worker + beat)
7. **Frontend Wiring**: API Keys page to /api/broker CRUD, useTradeStream hook, real correlation data

### Agent Team Waves (5 waves, 13 agents)

| Wave | Agents | Deps |
|------|--------|------|
| 1 | `@db-models`, `@broker-adapters`, `@crypto-api` | None |
| 2 | `@position-manager`, `@order-executor`, `@candle-storage` | Wave 1 |
| 3 | `@ingestion-tasks`, `@execution-tasks`, `@alert-tasks` | Wave 2 |
| 4 | `@realtime`, `@hardening` | Wave 3 |
| 5 | `@docker-prod`, `@frontend-wiring` | Wave 4 |

### New Dependencies (to install)
- `alpaca-py>=0.30.0` — Alpaca broker SDK
- `structlog>=24.0.0` — Structured logging
- `slowapi>=0.1.9` — FastAPI rate limiting
- `cryptography>=43.0.0` — Fernet encryption

### New Env Vars
- `SF_ENCRYPTION_KEY` — Fernet key for broker credential encryption (generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)

### Implementation Status
- [ ] Wave 1: Foundation (models, adapters, encryption)
- [ ] Wave 2: Core Wiring (positions, executor, candle storage)
- [ ] Wave 3: Celery Tasks (ingestion, execution, alerts)
- [ ] Wave 4: Real-Time + Hardening (WebSocket, circuit breakers)
- [ ] Wave 5: Production + Frontend (Docker, API Keys page)

---

## Agent Team Pattern Used

Each phase was built using **Cloud Agent Teams** — named agents dispatched via Task tool with `isolation: "worktree"`, working in dependency-ordered waves:

- **Phase 1**: 3 agents (infra, backend, frontend) in 2 waves
- **Phase 2**: 2 agents (layers, pipeline) in 2 waves
- **Phase 3**: 3 agents (auth+execution, APIs, integration) in 3 waves
- **Phase 4**: 4 agents (@frontend-scaffold, @page-builder-a, @page-builder-b, @ws-integrator) in 3 waves
- **Phase 5**: 4 agents (@ml-engineer, @api-builder, @frontend-journal, @frontend-analytics) in 2 waves
- **Phase 6**: 13 agents in 5 waves (PLANNED, not started)

Each wave was merged to main after verification. All worktree branches have been cleaned up.
