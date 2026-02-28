# Phase 6: Live Trading & Hardening — Design Document

> **Approved:** 2026-02-28
> **Approach:** Monolithic Scheduler (Celery Beat + existing FastAPI backend)
> **Brokers:** Alpaca (stocks) + CCXT/Binance (crypto)
> **Encryption:** Fernet symmetric (SF_ENCRYPTION_KEY)

---

## 1. Broker Adapter Layer

Abstract `BrokerAdapter` interface with three implementations:

```
BrokerAdapter (ABC)
├── AlpacaAdapter   — alpaca-py SDK, paper + live via URL switch
├── CCXTAdapter     — CCXT library, Binance testnet + live
└── PaperAdapter    — Simulation with slippage model + fill latency
```

**Interface methods:** `connect()`, `place_order()`, `cancel_order()`, `get_order_status()`, `get_positions()`, `get_account_balance()`

**BrokerRouter:** Routes orders by symbol — stocks → Alpaca, crypto → CCXT, unknown → reject.

**Credential storage:** `BrokerConnection` model (already exists) + Fernet encryption. New `/api/broker` CRUD endpoints. Keys masked in API responses (`****last4`).

---

## 2. DB-Backed Positions & Orders

### New Models

**Order:**
- `broker_order_id`, `symbol`, `direction`, `order_type` (limit/market/stop)
- `quantity`, `filled_quantity`, `average_fill_price`
- `status` (pending/filled/partial/cancelled/rejected)
- `broker` (alpaca/ccxt/paper), `user_id` FK, timestamps

**Position (replaces in-memory):**
- `user_id` FK, `symbol`, `direction`, `quantity`
- `entry_price`, `current_price`, `stop_loss`, `take_profit`
- `unrealized_pnl`, `broker`, `broker_position_id`
- `is_open`, `opened_at`, `closed_at`

**BacktestResult:**
- `user_id` FK, `strategy_id` FK (nullable)
- `symbol`, `timeframe`, `start_date`, `end_date`
- `metrics` (JSON), `equity_curve` (JSON), `trade_count`, `created_at`

### Data Flow

```
Signal → Order placed → Order table (status: pending)
       → Broker poll  → Order table (status: filled)
       → Position opened → Position table (is_open: true)
       → SL/TP hit → Position closed → Position table + Trade table
```

**State recovery:** On worker startup, query broker for open positions/orders and reconcile with DB.

---

## 3. Celery Beat Scheduled Tasks

| Task | Frequency | Description |
|------|-----------|-------------|
| `ingest_candles` | Every 1 min | Fetch candles for active symbols via CCXT/Alpaca → Candle table → PricePublisher |
| `run_signal_pipeline` | Every 5 min | Run 6-layer pipeline per active strategy → Signal table → SignalPublisher |
| `execute_pending_signals` | Every 30 sec | Pre-trade risk checks → place orders via BrokerRouter → Order table |
| `poll_order_status` | Every 15 sec | Query broker APIs → update Order table → open Position on fill |
| `manage_positions` | Every 1 min | Trail stops, check SL/TP → close via broker → Trade table |
| `send_daily_summary` | Daily 17:00 UTC | Aggregate trades → email via Resend |
| `retrain_hmm` | Weekly Sun 02:00 UTC | Retrain HMM on real candles → Redis cache |
| `reconcile_broker_state` | Every 5 min | Sync Order/Position tables with broker state |

**Design rules:**
- All tasks idempotent — safe to run twice
- Redis distributed lock per task (TTL = 2x interval)
- 3 retries with exponential backoff, then log to `task_errors` Redis stream
- `ingest_candles` tracks high-water mark per symbol/timeframe

**Wire existing unused code:**
- `PubSub` publishers (`core/pubsub.py`) → called by ingestion + pipeline tasks
- `build_signal_email()` / `build_daily_summary_email()` → called by alert/summary tasks
- Alert config → persisted as JSON column on User model (replaces in-memory dict)

---

## 4. WebSocket + Real-Time Data Flow

```
Celery Tasks ──► Redis PubSub channels
                    │
              Redis Listener (FastAPI startup background task)
                    │
              ConnectionManager.broadcast()
                    │
              WebSocket clients
              ├── /ws/signals  (signal pipeline output)
              ├── /ws/prices   (candle ingestion output)
              └── /ws/trades   (order fills, position updates)
```

- **RedisSubscriber** background task: spawns on FastAPI startup, subscribes to `signalforge:signals`, `signalforge:prices:*`, `signalforge:trades`
- **New channel `/ws/trades`**: order fills, position opens/closes, PnL updates
- **New `TradePublisher`** in `core/pubsub.py`
- **Frontend**: existing `useSignalStream` and `usePriceStream` hooks receive real data with zero changes. New `useTradeStream` hook for trades channel.

---

## 5. Error Handling, Circuit Breakers & Rate Limiting

### API Rate Limiting
- `slowapi` middleware: 60 req/min standard, 10 req/min expensive (backtest/signal/journal), 5 req/min auth
- Broker APIs: CCXT built-in `enableRateLimit` + Alpaca token bucket (200 req/min)

### Circuit Breaker (per broker)
```
CLOSED ──(5 failures in 60s)──► OPEN ──(30s cooldown)──► HALF_OPEN
  ▲                                                          │
  └──────────(1 success)─────────────────────────────────────┘
```
- State in Redis (survives restart). Alert email on circuit open.
- OPEN: orders rejected immediately, no API calls. Existing SL orders remain at broker.

### Graceful Degradation
- Alpaca down → crypto continues, stock signals queued
- Redis down → REST from PostgreSQL still works, WebSocket/Celery degraded
- Exchange down → that exchange marked unavailable, others unaffected

### Structured Logging
- `structlog` JSON output: `task_name`, `symbol`, `broker`, `order_id`, `user_id`
- Request ID middleware (UUID per request)
- Trade-critical actions at WARNING level (never filtered)

### Health Check
- `GET /health` returns: `{ db, redis, celery, brokers: { alpaca, binance } }`

---

## 6. Production Docker & Security

### docker-compose.prod.yml
```
timescaledb  — PostgreSQL 16, persistent volume, health check
redis        — Redis 7, persistent volume, maxmemory policy
api          — FastAPI, 4 uvicorn workers, depends_on db+redis
worker       — Celery worker, concurrency=4, depends_on db+redis
beat         — Celery beat, single instance, depends_on worker
```
- `restart: unless-stopped` + health checks on all services
- Env from `.env.prod` (not committed)
- Multi-stage Dockerfile (slim Python 3.12)

### Security
- Fernet encryption for broker keys (SF_ENCRYPTION_KEY)
- Startup check: refuse to start if JWT secret is still default
- CORS locked to configured origins
- Broker credentials scoped to user, masked in responses
- Auth rate limiting (5 req/min login/register)

### Alembic Migration
- New `Order`, `Position`, `BacktestResult` models
- `alert_config` JSON column on User model

### Frontend (minimal wiring)
- API Keys page → wire to `/api/broker` CRUD
- Dashboard → DB-backed positions (already wired, gets real data)
- New `useTradeStream` hook
- Correlation → real candle data instead of synthetic
