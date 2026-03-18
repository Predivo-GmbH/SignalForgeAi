# SignalForgeAI — Design Document

**Date**: 2026-02-28
**Status**: Approved
**Reference**: `SignalForgeAI-Technical-Plan.md`
**Inspiration**: Kraken web UI (284 screenshots in `kraken-reference/`)

---

## 1. Product Summary

SignalForgeAI is a web-based automated trading platform using a multi-layer confluence scoring system. It combines market regime detection, Fibonacci confluence zones, volume analysis, and dynamic risk management into a unified signal engine — backed by rigorous backtesting.

**Target Markets**: Forex (EUR/USD, GBP/USD, USD/JPY), Crypto (BTC/USDT, ETH/USDT, SOL/USDT), US Stocks/ETFs (via Alpaca).

**Users**: Single-user initially, architected for multi-tenancy later.

---

## 2. Stack Decision

**Approach B: React+Vite + FastAPI** (chosen over Next.js or Supabase alternatives)

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | React 18 + Vite + TypeScript | Consistent with all other projects (Arivioo, SignalScore, Predivo, APIs) |
| Styling | Tailwind 4 + shadcn/ui | Standard stack, Kraken-inspired token system |
| State | TanStack Query + Zustand | Server state + client state separation |
| Charts | TradingView Lightweight Charts | Industry standard for candlestick charts |
| Real-time | Socket.io-client | WebSocket connection to FastAPI |
| Backend | Python 3.12 + FastAPI | Required for trading libraries (ta-lib, vectorbt, ccxt, hmmlearn) |
| Task Queue | Celery + Redis | Async backtest jobs |
| Database | PostgreSQL 16 + TimescaleDB | Single instance — TimescaleDB is a PG extension |
| Cache/PubSub | Redis 7 | Real-time price streams, signal pub/sub, indicator cache |
| Reverse Proxy | Nginx + Let's Encrypt | SSL termination on VPS |
| Deploy (FE) | GitHub Actions → FTP to Predivo | Same pattern as all other projects |
| Deploy (BE) | Docker Compose on Hetzner/DO VPS | All services colocated |

---

## 3. System Architecture

```
PREDIVO HOSTING (Apache FTP)
  React 18 + Vite SPA (static dist/)
  GitHub Actions → FTP deploy
  Password gate: signalforge2026
        │
        │ REST + WebSocket (HTTPS)
        ▼
VPS (Hetzner/DO, Docker Compose)
  ├── Nginx (reverse proxy, SSL via LE)
  ├── FastAPI (REST + WebSocket hub)
  ├── Signal Engine (persistent process, consumes Redis streams)
  ├── Data Ingestion Worker (asyncio, exchange WebSocket feeds)
  ├── Celery Worker (async backtest jobs)
  ├── Order Executor (Alpaca, CCXT)
  ├── TimescaleDB+PG16 (single instance)
  └── Redis 7 (cache, pub/sub, streams)
        │
        ▼
  Market Data (CCXT, Polygon, Alpha Vantage)
  Broker APIs (Alpaca, Binance — paper → live)
```

### Docker Compose Services

| Service | Image | Purpose |
|---------|-------|---------|
| `api` | Custom Dockerfile | FastAPI + WebSocket hub |
| `engine` | Same image, different entrypoint | Signal engine process |
| `worker` | Same image + Celery | Backtest jobs |
| `ingestion` | Same image, different entrypoint | Data feed consumer |
| `db` | timescale/timescaledb:latest-pg16 | PostgreSQL + TimescaleDB |
| `redis` | redis:7-alpine | Cache, pub/sub, streams |
| `nginx` | nginx:alpine | Reverse proxy + SSL |

### Real-time Data Flow

```
Exchange WebSocket → Data Ingestion Worker (asyncio)
  ├── TimescaleDB (persist OHLCV)
  ├── Redis Stream "prices:{symbol}"
  │     ├── Signal Engine (consumes, computes layers 0-5)
  │     │     ├── Redis "signals" stream → Order Executor
  │     │     └── Redis "indicators:{symbol}" (cache)
  │     └── FastAPI WS Hub → Frontend (live charts)
  └── FastAPI WS Hub → Frontend (price tickers)
```

---

## 4. Frontend Design

### Design Inspiration

Kraken Pro trading interface — dark-first, purple accent, data-dense, collapsible sidebar.

### Theme (User-Toggleable, Default Dark)

| Token | Dark | Light |
|-------|------|-------|
| bg-base | `#0B0B14` | `#F7F5F2` |
| bg-surface | `#141420` | `#FFFFFF` |
| bg-elevated | `#1C1C2E` | `#F0EDE8` |
| border | `#2A2A3C` | `#E5E2DC` |
| text-primary | `#F0F0F5` | `#1A1A2E` |
| text-secondary | `#8B8BA0` | `#6B6B80` |
| accent-primary | `#7B61FF` | `#7B61FF` |
| accent-primary-soft | `#7B61FF20` | `#7B61FF15` |
| positive | `#00D68F` | `#00A870` |
| negative | `#FF4D6A` | `#E03E52` |
| warning | `#FFB020` | `#E09A00` |

**Typography**: Inter (UI), JetBrains Mono (prices/numbers/code).

### Layout

- Collapsible left sidebar (icons-only when collapsed)
- Top bar: Logo + global search + settings/profile
- Bottom ticker strip: live prices for watched symbols
- Main content: full-width, page-dependent

### Pages (7 + Auth)

| Page | Route | Content |
|------|-------|---------|
| Dashboard | `/` | TradingView chart + signal overlays, active positions, regime indicator, P&L cards, signal feed |
| Signals | `/signals` | Signal history table, filters, confluence breakdown |
| Trades | `/trades` | Trade history, P&L, R:R, chart replay |
| Backtest Lab | `/backtest` | Configure → run → equity curve + metrics, compare runs |
| Trade Journal | `/journal` | AI-assisted trade review, pattern recognition |
| Strategy Config | `/config` | All 6 layer parameters as form controls |
| API Keys | `/keys` | Broker connections, encrypted storage, paper/live toggle |
| Auth | `/login`, `/register` | Centered card layout |

---

## 5. Backend Design

### Project Structure

```
backend/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── alembic/versions/
├── app/
│   ├── main.py                 # FastAPI app
│   ├── config.py               # pydantic-settings
│   ├── auth/                   # JWT auth
│   ├── api/                    # REST + WebSocket endpoints
│   ├── engine/
│   │   ├── pipeline.py         # SignalPipeline orchestrator
│   │   ├── layers/             # 6 layers (regime, trend, zones, confluence, triggers, risk)
│   │   ├── reversal.py         # ReversalMonitor
│   │   └── indicators.py       # ta-lib / pandas-ta wrapper
│   ├── backtest/
│   │   ├── engine.py           # vectorbt
│   │   ├── optimizer.py        # Walk-forward
│   │   └── tasks.py            # Celery tasks
│   ├── execution/
│   │   ├── executor.py         # OrderExecutor
│   │   ├── brokers/            # Alpaca, CCXT wrappers
│   │   └── position_manager.py
│   ├── data/
│   │   ├── ingestion.py        # WebSocket consumer
│   │   ├── providers/          # CCXT, Alpaca, Polygon feeds
│   │   └── storage.py          # TimescaleDB helpers
│   ├── models/                 # SQLAlchemy models
│   └── core/                   # DB, Redis, security, events
```

### API Endpoints

**Auth**: POST `/auth/register`, `/auth/login`, `/auth/refresh`
**Signals**: GET `/signals`, GET `/signals/:id`, WS `/ws/signals`
**Trades**: GET `/trades`, GET `/trades/:id`, GET `/trades/stats`, WS `/ws/trades`
**Backtests**: POST `/backtests`, GET `/backtests/:id`, GET `/backtests`
**Strategies**: CRUD `/strategies`, POST `/strategies/:id/activate`
**Brokers**: CRUD `/brokers`, POST `/brokers/:id/test`
**Market Data**: GET `/candles/:symbol/:tf`, GET `/symbols`, WS `/ws/prices`
**System**: GET `/health`, GET `/engine/status`

### Database (Single PG16+TimescaleDB Instance)

- `public` schema: users, strategies, broker_connections, signals, trades, backtests
- `candles` hypertable: OHLCV time-series with continuous aggregates
- Alembic for migrations

---

## 6. Phased Roadmap

No time-boxing — build fast, phases are logical order only.

### Phase 1 — Foundation
Project scaffolding, Docker Compose, FastAPI skeleton, JWT auth, Alembic, data pipeline (CCXT → TimescaleDB), indicator library, Layers 1-2, basic BacktestEngine, CLI tool, frontend scaffold (Vite + tokens + auth pages + password gate), GitHub CI.

### Phase 2 — Signal Engine Complete
Layers 0, 3, 4, 5, 6. Session/timing filter. Multi-TF Fibonacci. Volume Profile. Backtest across 3 markets. Walk-forward optimization. Signal + Trade DB tables.

### Phase 3 — API & Paper Trading
All REST endpoints. WebSocket hub. Real-time data ingestion. Redis Streams. Signal engine as persistent process. Alpaca paper trading. CCXT testnet. OrderExecutor + PositionManager. Celery worker. Nginx + SSL on VPS.

### Phase 4 — Frontend Dashboard
JSONC Design Brief → token system → components. Layout shell. Dashboard (TradingView chart + overlays). All 7 pages. WebSocket integration. Deploy to Predivo.

### Phase 5 — Advanced Features
HMM regime detection. Trade Journal (Claude Haiku AI). Walk-forward UI. Portfolio view. Correlation checks. Email alerts (Resend). Analytics dashboard.

### Phase 6 — Live Trading & Hardening
Live mode (Alpaca real + Binance). Monitoring + alerting. Rate limiting. Graceful degradation. Daily P&L emails. Security audit. Multi-user prep.

---

## 7. Key Decisions Log

| Decision | Choice | Why |
|----------|--------|-----|
| Frontend framework | React+Vite (not Next.js) | Consistent with all projects, SPA on Apache FTP |
| Backend | FastAPI (not Supabase Edge Functions) | Python trading libraries required |
| Database | Single PG+TimescaleDB (not separate instances) | Simpler, less Docker overhead |
| Theme | User-toggleable, dark default | Kraken-style, trader preference |
| Users | Single-user now, multi-tenant architecture | Future SaaS potential |
| Deploy FE | Predivo FTP (GitHub Actions) | Standard deploy pattern |
| Deploy BE | VPS Docker Compose | Colocated services, low latency |
| AI (journal) | Claude Haiku | Consistent with SignalScore |
| Email | Resend | Simple, cheap |
| Timeline | No time-boxing | Build fast, ship incrementally |
