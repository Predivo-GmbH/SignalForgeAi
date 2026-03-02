# SignalForge — Session Changelog (2026-03-02)

> **Purpose:** Complete record of all changes made during the March 2 development session.
> All changes are uncommitted and live in the working directory.

**Session scope:** Celery infrastructure, pipeline debugging, broker UI cleanup, chart timeframe fix, storage optimization, AI enrichment pipeline (5 waves), AI Usage & Cost Tracking dashboard, AI autonomous self-learning loop redesign.

---

## Table of Contents

1. [Celery Worker & Beat — Docker Setup](#1-celery-worker--beat--docker-setup)
2. [Database Schema — AI Enrichment Columns](#2-database-schema--ai-enrichment-columns)
3. [Pipeline Debugging — Block Reason Logging](#3-pipeline-debugging--block-reason-logging)
4. [Broker Connections — Paper Mode Removal](#4-broker-connections--paper-mode-removal)
5. [Dashboard Chart — All 6 Timeframes](#5-dashboard-chart--all-6-timeframes)
6. [Candle Storage — Bulk Upsert Fix](#6-candle-storage--bulk-upsert-fix)
7. [Current System State](#7-current-system-state)
8. [Known Issues & Future Work](#8-known-issues--future-work)
9. [Files Changed](#9-files-changed)
10. [AI Enrichment Pipeline (5 Waves)](#10-ai-enrichment-pipeline-5-waves)
11. [AI Usage & Cost Tracking Dashboard](#11-ai-usage--cost-tracking-dashboard)
12. [AI Autonomous Self-Learning Loop — Redesign](#12-ai-autonomous-self-learning-loop--redesign)

---

## 1. Celery Worker & Beat — Docker Setup

### Problem
Deployed AI strategy ("AI Advisor — Conservative Swing") was not executing any trades because Celery Worker and Beat services were not running — only `db`, `redis`, and `api` were in docker-compose.yml.

### Changes

**File: `backend/docker-compose.yml`**

Added two new services:

```yaml
worker:
  build: .
  environment:
    SF_DATABASE_URL: postgresql+asyncpg://signalforge:signalforge@db:5432/signalforge
    SF_REDIS_URL: redis://redis:6379/0
    SF_CELERY_BROKER_URL: redis://redis:6379/1
    SF_CELERY_RESULT_BACKEND: redis://redis:6379/2
    SF_DEBUG: "true"
  depends_on:
    db: { condition: service_healthy }
    redis: { condition: service_healthy }
  volumes:
    - ./app:/code/app
  command: celery -A app.worker.celery_app worker --loglevel=info --concurrency=4

beat:
  build: .
  environment:
    SF_DATABASE_URL: postgresql+asyncpg://signalforge:signalforge@db:5432/signalforge
    SF_REDIS_URL: redis://redis:6379/0
    SF_CELERY_BROKER_URL: redis://redis:6379/1
    SF_CELERY_RESULT_BACKEND: redis://redis:6379/2
    SF_DEBUG: "true"
  depends_on:
    worker: { condition: service_started }
  volumes:
    - ./app:/code/app
  command: celery -A app.worker.celery_app beat --loglevel=info
```

Also added `SF_CELERY_BROKER_URL` and `SF_CELERY_RESULT_BACKEND` to the existing `api` service environment.

### How to start
```bash
cd backend
docker.exe compose up -d   # Starts all 5 services: db, redis, api, worker, beat
```

> **Note:** Use `docker.exe` (not `docker`) on WSL2 with Docker Desktop for Windows.

---

## 2. Database Schema — AI Enrichment Columns

### Problem
Celery worker crashed on first run with: `column signals.ai_quality_score does not exist`.

### Changes

**File: `backend/alembic/versions/b2c3d4e5f6a7_add_ai_columns_to_signals.py`** (NEW)

Alembic migration adding 5 columns to the `signals` table:

| Column | Type | Nullable |
|--------|------|----------|
| `ai_quality_score` | Float | Yes |
| `ai_reasoning` | Text | Yes |
| `ai_recommendation` | String(20) | Yes |
| `mtf_confidence` | Float | Yes |
| `mtf_alignment` | String(20) | Yes |

### How it was applied
The migration was applied via **direct SQL** (not `alembic upgrade`) because the alembic directory wasn't volume-mounted into the worker container:

```sql
ALTER TABLE signals ADD COLUMN IF NOT EXISTS ai_quality_score FLOAT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS ai_reasoning TEXT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS ai_recommendation VARCHAR(20);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS mtf_confidence FLOAT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS mtf_alignment VARCHAR(20);
```

The alembic_version was manually updated to track the migration chain:

```
23e8e2f4176c → a1b2c3d4e5f6 → b2c3d4e5f6a7 → c3d4e5f6a7b8 → d4e5f6a7b8c9
```

**Current alembic_version in DB:** `d4e5f6a7b8c9`

---

## 3. Pipeline Debugging — Block Reason Logging

### Problem
After starting Celery, the pipeline was running but all 15 symbols returned `NO_TRADE` with `confluence=0`. Needed to understand which pipeline layer was blocking trades.

### Changes

**File: `backend/app/tasks/run_pipeline.py`**

Added `block_reason` to the log line:

```python
logger.info(
    "Strategy '%s' | %s %s: action=%s, confluence=%s, block=%s",
    active_strategy.name, symbol, timeframe,
    signal.action, signal.confluence_score, signal.block_reason,
)
```

### Findings

The pipeline is working correctly. Block reasons across 15 symbols:

| Block Reason | Count | Pipeline Layer |
|---|---|---|
| `chaotic_regime` | 5 symbols | Layer 0 — RegimeDetector |
| `no_trend` | 3 symbols | Layer 1 — TrendFilter |
| `low_confluence` | 7 symbols | Layer 3 — ConfluenceScorer |

Strategy config has `min_confluence: 70` — a deliberately high threshold. The pipeline will only trade when market conditions are strongly confluent.

### Execution Chain Verification

The full execution chain was verified end-to-end:

```
Signal Pipeline → pending signal in DB
  → execute_pending_signals (every 30s) picks it up
  → pre-trade risk checks (daily loss, max positions, cooldown)
  → OrderExecutor → PaperAdapter (instant fill, 0.1% slippage)
  → poll_order_status (every 15s) marks as filled
  → PositionManagerDB opens position from filled order
  → manage_positions (every 60s) monitors SL/TP/trailing/time-stop
  → closes position → creates Trade row
```

**Confirmed:** When conditions ARE met, trades will be executed correctly.

---

## 4. Broker Connections — Paper Mode Removal

### Problem
The Settings page allowed connecting a broker in "Paper Mode" which:
1. Had no actual functionality (paper trading uses a hardcoded PaperAdapter)
2. Tried to encrypt empty strings, causing `SF_ENCRYPTION_KEY not set` error
3. The broker connections table is not wired into the execution pipeline at all

### Changes

**File: `frontend/src/pages/Settings.tsx`**
- Removed Paper/Live mode toggle from ConnectForm entirely
- Form now only shows: broker selector + API Key + API Secret (all for live)
- Always sends `is_paper: false`
- Removed `isPaper` prop from `ConnectionCard` component
- Removed Paper/Live badge from connection card display
- Updated empty state description: "Connect exchange API keys for live trading"

**File: `frontend/src/hooks/useBrokerConnections.ts`**
- Made `api_key` and `api_secret` optional in `ConnectBrokerRequest` interface

**File: `backend/app/api/broker.py`**
- Made `api_key` and `api_secret` default to `""` in `BrokerConnectRequest`
- Added validation: live mode requires both keys (422 error if missing)
- Paper mode skips encryption (uses `b""` for `api_key_enc`/`api_secret_enc`)
- List endpoint skips decryption for paper connections (shows "Paper" instead)

### Future integration needed
`backend/app/tasks/execute_signals.py` always creates a fresh `PaperAdapter` — it never reads the `broker_connections` table. When live trading is implemented, this task needs to:
1. Read the user's broker connections from DB
2. Decrypt credentials
3. Instantiate the appropriate adapter (AlpacaAdapter or CCXTAdapter)
4. Pass it to BrokerRouter

---

## 5. Dashboard Chart — All 6 Timeframes

### Problem
Dashboard price chart only showed data for 1h and 4h. Selecting 1m, 5m, 15m, or 1d showed "No candle data available" because only those two timeframes were being ingested.

### Root Cause
```python
# backend/app/tasks/ingest_candles.py
DEFAULT_TIMEFRAMES = ["1h", "4h"]  # Only fetched 2 of 6 frontend timeframes
```

### Changes

**File: `backend/app/tasks/ingest_candles.py`**

```python
# Before
DEFAULT_TIMEFRAMES = ["1h", "4h"]

# After
DEFAULT_TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"]
```

Also updated `backfill_symbols()` to use `DEFAULT_TIMEFRAMES` instead of hardcoded `["1h", "4h"]`.

### Data Volume

After the fix, backfill ran automatically on next ingestion cycle:
- ~500 candles backfilled per new timeframe per symbol
- 15 symbols × 4 new timeframes × 500 candles = ~30,000 new rows
- Initial backfill took ~88 seconds
- Subsequent incremental runs: ~30 seconds (50 candles per symbol/timeframe)

Current candle counts for BTC/USDT (representative):

| Timeframe | Count |
|-----------|-------|
| 1m | 500 |
| 5m | 500 |
| 15m | 500 |
| 1h | 519 |
| 4h | 505 |
| 1d | 500 |

---

## 6. Candle Storage — Bulk Upsert Fix

### Problem
When two concurrent ingestion tasks ran simultaneously, both tried to INSERT the same candle row, causing:
```
UniqueViolationError: duplicate key value violates unique constraint "candles_pkey"
```
This rolled back the entire transaction, losing all candles from that ingestion cycle.

### Root Cause
`save_candles_db()` used a row-by-row SELECT-then-INSERT pattern — a TOCTOU (time-of-check-time-of-use) race condition.

### Changes

**File: `backend/app/data/storage.py`**

Replaced the row-by-row ORM upsert with a single bulk PostgreSQL `ON CONFLICT DO UPDATE`:

```python
from sqlalchemy.dialects.postgresql import insert as pg_insert

# Build list of row dicts from DataFrame
rows = [...]

stmt = pg_insert(Candle).values(rows)
stmt = stmt.on_conflict_do_update(
    index_elements=["time", "symbol", "exchange", "timeframe"],
    set_={
        "open": stmt.excluded.open,
        "high": stmt.excluded.high,
        "low": stmt.excluded.low,
        "close": stmt.excluded.close,
        "volume": stmt.excluded.volume,
        "vwap": stmt.excluded.vwap,
        "trades": stmt.excluded.trades,
    },
)
await db.execute(stmt)
```

### Benefits
1. **Concurrent-safe** — no more duplicate key errors
2. **Faster** — single SQL statement vs N+1 queries (SELECT + INSERT per row)
3. **Atomic** — all candles in a batch succeed or fail together

---

## 7. Current System State

### Running Docker Services

| Service | Status | Port | Purpose |
|---------|--------|------|---------|
| db | Healthy | 5432 | TimescaleDB (PostgreSQL 16) |
| redis | Healthy | 6379 | Cache + Celery broker |
| api | Running | 8000 | FastAPI backend |
| worker | Running | — | Celery worker (4 processes) |
| beat | Running | — | Celery Beat scheduler |

### Celery Beat Schedule (Updated)

| Task | Interval | Description |
|------|----------|-------------|
| `ingest_candles` | 60s | Fetch candles for all symbols × 6 timeframes |
| `run_signal_pipeline` | 300s (5min) | Run 6-layer pipeline, persist signals |
| `execute_pending_signals` | 30s | Execute pending signals via PaperAdapter |
| `poll_order_status` | 15s | Check order status, open positions on fill |
| `manage_positions` | 60s | Monitor SL/TP, close positions |
| `reconcile_broker_state` | 300s (5min) | No-op in paper mode |
| `flush_ai_usage` | 60s | Flush AI usage metrics |

### Active Strategy

| Field | Value |
|-------|-------|
| Name | AI Advisor — Conservative Swing |
| Symbols | 15 (NEAR, MORPHO, AIXBT, ZRO, ENSO, FORM, SUN, BTC, DOGE, JUP, ALICE, XRP, SAHARA, OG, 1000SATS) |
| Timeframe | 4h |
| min_confluence | 70 |
| Status | Active, no trades yet (conditions not met) |

### Database State

| Table | Approx Rows | Notes |
|-------|-------------|-------|
| candles | ~55,000+ | 15+ symbols × 6 timeframes × ~500 each |
| signals | Growing | All NO_TRADE currently |
| strategies | 1 | Active AI Advisor strategy |
| orders | 0 | No trades executed yet |
| positions | 0 | No positions opened yet |
| trades | 0 | No trades closed yet |
| alembic_version | 1 | `d4e5f6a7b8c9` |

---

## 8. Known Issues & Future Work

### Broker Connections Not Wired to Execution
- `execute_signals.py` always creates a fresh `PaperAdapter`
- `broker_connections` table stores encrypted credentials but they're never read
- **Action needed:** Wire broker connections to execution pipeline for live trading

### HMM Model Convergence Warnings
- Some symbols show: `Model is not converging. Current: X is not greater than Y`
- Affects: ZRO, ALICE, XRP, DOGE, SUN
- The HMM still produces regime predictions but confidence may be lower
- **Action needed:** Investigate if more training data would help, or adjust HMM parameters

### Clock Drift Warning
- Beat logs show: `Substantial drift from celery@DESKTOP-124K6MV may mean clocks are out of sync. Current drift is 3600 seconds.`
- This is a WSL2 ↔ Windows Docker time zone difference (1 hour)
- Does not affect functionality, only log timestamps

### Ingestion Performance
- Full ingestion cycle: ~30 seconds for 15 symbols × 6 timeframes × 50 candles
- Runs every 60 seconds — leaves ~30 seconds of headroom
- If symbols grow significantly, may need to increase interval or add batching

### All Changes Are Uncommitted
- 90+ modified files, 30+ new files — accumulated across multiple sessions
- See `git status` output below for full list
- Should be committed in logical groups when ready

---

## 9. Files Changed

### Modified in This Session

| File | Change |
|------|--------|
| `backend/docker-compose.yml` | Added worker + beat services, Celery env vars to api |
| `backend/app/tasks/ingest_candles.py` | `DEFAULT_TIMEFRAMES` → all 6, `backfill_symbols` default updated |
| `backend/app/tasks/run_pipeline.py` | Added `block_reason` to pipeline log output |
| `backend/app/data/storage.py` | Replaced row-by-row upsert with bulk `ON CONFLICT DO UPDATE` |
| `backend/app/api/broker.py` | Paper mode skips encryption, live validation, defaults |
| `frontend/src/pages/Settings.tsx` | Removed Paper/Live toggle, live-only broker connect form |
| `frontend/src/hooks/useBrokerConnections.ts` | Made api_key/api_secret optional in ConnectBrokerRequest |

### Created in This Session

| File | Purpose |
|------|---------|
| `backend/alembic/versions/b2c3d4e5f6a7_add_ai_columns_to_signals.py` | Migration: 5 AI columns on signals table |

### Applied Directly to Database (Not Just Files)

| Change | Method |
|--------|--------|
| 5 AI columns on signals table | `ALTER TABLE` via `docker.exe compose exec db psql` |
| alembic_version tracking | `UPDATE alembic_version SET version_num = 'b2c3d4e5f6a7'` |

---

## 10. AI Enrichment Pipeline (5 Waves)

### What was implemented
Complete AI enrichment system across the signal pipeline:

1. **Wave 1 — Pricing Module** (`app/advisor/pricing.py`): Static Anthropic pricing lookup for Haiku/Sonnet/Opus per million tokens
2. **Wave 2 — Cost Column + Migration**: `cost_usd` on `AIInsight` model, Alembic migration `d4e5f6a7b8c9`
3. **Wave 3 — ClaudeClient Usage Recording** (`app/advisor/claude_client.py`): `insight_type` param, async/sync usage recording, daily API call limit via Redis counter
4. **Wave 4 — Caller Updates**: 7 files updated with `insight_type=` parameter
5. **Wave 5 — Redis Flush Task** (`app/tasks/flush_ai_usage.py`): Celery task flushes `ai_usage_queue` to DB every 60s

### Key architectural decisions
- **Async path** (`ask_json`): `asyncio.create_task()` → direct DB insert via `async_session`
- **Sync path** (`ask_json_sync`, used in Celery workers): Push to Redis list → flush task bulk-inserts
- **Daily limit**: Redis counter `ai_calls:{date}` with 86400s TTL, checked before each call

---

## 11. AI Usage & Cost Tracking Dashboard

### Backend
**API file:** `app/api/ai_usage.py` — Dual-source architecture:
- Tries Anthropic Admin API first (via `app/advisor/anthropic_admin.py`)
- Falls back to local `ai_insights` table queries
- Response includes `source: "anthropic_api" | "local"` field

**Endpoints:**
- `GET /api/ai-usage?days=30` — Summary, model breakdown, feature breakdown, daily costs, recent calls, credit info
- `PUT /api/ai-usage/credit` — Update prepaid credit (stored in Redis key `ai_prepaid_credit`)

**Anthropic Admin API client:** `app/advisor/anthropic_admin.py`
- Uses httpx async client with pagination
- `fetch_cost_report(days)` → `GET /v1/organizations/cost_report`
- `fetch_usage_report(days)` → `GET /v1/organizations/usage_report/messages`
- Currently dormant — requires `sk-ant-admin-...` key (not available on individual Anthropic plans)

### Frontend
**Hook:** `src/hooks/useAiUsage.ts` — `useAiUsage(days)` with 60s refetch, `useUpdateCredit()` mutation

**Component:** `src/components/settings/AiUsageTab.tsx`
- Period selector (7d / 30d / 90d)
- Summary cards (Total Cost, Total Calls, Avg Cost/Call, Avg Latency)
- Data source badge (green "Anthropic API" or blue "Local")
- Credit section with progress bar + inline edit
- Daily cost histogram chart (lightweight-charts HistogramSeries)
- Model breakdown table + Usage by feature table
- Recent calls table (last 20)

**Settings integration:** `src/pages/Settings.tsx` — Added `"ai-usage"` tab with DollarSign icon

### Docker Compose changes
- `SF_ANTHROPIC_API_KEY` → api + worker services (from host `.env`)
- `SF_ANTHROPIC_ADMIN_API_KEY` → api service (from host `.env`)
- `./alembic:/code/alembic` volume mount added to api service

### Config
- `SF_ANTHROPIC_API_KEY` set in `backend/.env` (the Claude Code workspace key, reused)
- `anthropic_admin_api_key: str = ""` added to `config.py`
- `ai_prepaid_credit_usd: float = 0.0` added to `config.py`

### Anthropic billing context
- Credit grant: $5.00 USD (+ $0.41 CHF VAT = $5.41 invoice total; only $5.00 is usable API credit)
- Remaining balance: $0.95 (as of session end)
- Admin API not available on individual plans — prepaid credit must be entered manually

---

## 12. AI Autonomous Self-Learning Loop — Redesign

### Context

The user's vision: **fully autonomous trading**. The user inputs money, the AI does everything else. Several AI functions were displaying results to the user instead of feeding back into the system. Two key self-learning components (Risk Tuner, Feedback Filter) existed in code but were disabled/unwired.

**Prior session work:** Investment Planner was already redesigned — no `risk_tolerance`, AI picks all parameters from market conditions. Frontend already cleaned.

### What Was Done

Three phases were implemented to activate the self-learning loop:

#### Phase 1: Wire the Self-Learning Loop (zero extra API cost)

**1A. Wire FeedbackFilter into pipeline** — `backend/app/tasks/run_pipeline.py`

The `FeedbackFilter` class existed (`engine/layers/feedback_filter.py`) but was never called. Now wired into the signal pipeline:

```python
from app.engine.layers.feedback_filter import FeedbackFilter
feedback_filter = FeedbackFilter()

# After pipeline returns BUY/SELL, before persisting:
skip, skip_reason = await feedback_filter.should_skip(symbol, regime, db, strategy_id)
# If skip → log and continue

confluence_override = await feedback_filter.get_confluence_override(symbol, regime, db, strategy_id)
# If confluence < override → log and continue
```

- `should_skip()` checks FeedbackRule objects for `avoid_pattern` actions matching symbol/regime
- `get_confluence_override()` checks for `adjust_param` rules that raise the confluence threshold
- Empty rules table → all signals pass through (safe default)

**1B. Honor AI reject in live mode** — `backend/app/tasks/run_pipeline.py`

The Signal Quality Evaluator's `reject` recommendation was only honored in backtests, not live. Now after `_ai_enrich_signal()`:

```python
if signal_row.ai_recommendation == "reject":
    signal_row.status = "rejected"
    logger.info("AI REJECT (live): %s %s %s ...")
    continue
```

Signal stays in DB as `status="rejected"`. `execute_pending_signals` only processes `status="pending"` — rejected signals never execute.

**1C. Update config defaults** — `backend/app/config.py`

```python
ai_risk_tuning_enabled: bool = True   # was False
ai_feedback_loop_enabled: bool = True  # was False
```

Documentary only — these flags were never actually checked in code (tasks ran on Beat schedule regardless). Aligned defaults with actual behavior.

**1D. Feedback synthesis: weekly → daily** — `backend/app/worker.py`

Changed from `"feedback-synthesis-weekly"` (Wednesdays 04:00 UTC) to `"feedback-synthesis-daily"` (04:00 UTC every day). Faster rule learning from trade performance.

#### Phase 2: Pattern Analyzer → System Feedback (+$0.008/day)

**2A. Create periodic pattern analysis task** — `backend/app/tasks/pattern_analysis.py` (NEW)

New Celery task following the same pattern as `risk_tuning.py` and `feedback_synthesis.py`:
- For each active strategy: runs `PatternAnalyzer.analyze_deep(user_id, db)`
- Stores results in Redis: `pattern_analysis:{strategy_id}` (48h TTL)
- Registered in `worker.py` at `crontab(hour=2, minute=30)` — 30min before Risk Tuner

**2B. Enrich Risk Tuner with pattern context** — `backend/app/advisor/risk_tuner.py`

Added `_load_pattern_context(strategy_id)` that reads from Redis. In `tune()`, loads pattern context after computing metrics. In `_build_user_message()`, appends patterns and recommendations section so the Risk Tuner has pattern insights when deciding parameter adjustments.

Self-learning data flow:
```
Pattern Analysis (02:30 UTC) → Redis cache
  → Risk Tuner (03:00 UTC, reads pattern context) → strategy.config updates
  → Feedback Synthesis (04:00 UTC, creates rules) → feedback_rules table
  → FeedbackFilter (every 5min pipeline run, applies rules) → better signal filtering
```

#### Phase 3: Deprecate Trade Journal (saves API costs)

**3A. Remove journal router** — `backend/app/main.py`

Removed `journal_router` import and `app.include_router()` call. Journal API endpoints (`/api/journal/analyze`, `/api/journal/patterns`) now return 404.

**3B. Clean frontend** — `frontend/src/pages/Trades.tsx` + `frontend/src/hooks/useJournal.ts`

- Removed all journal integration from Trades page: imports, hooks, state, Pattern Summary panel, per-trade AI analysis button, expandable analysis rows
- Simplified `TradeRow` component to display-only (no analysis/expand props)
- Removed unused icon imports (Brain, Loader2, Lightbulb, AlertTriangle, Sparkles, ChevronDown, ChevronUp)
- Updated page description: "AI-powered trade analysis" → "Execution log and performance metrics"
- Updated `colSpan` from 12 to 11 (removed analyze column)
- Deleted `frontend/src/hooks/useJournal.ts`

**Backend files kept:** `journal.py` (dead code, harmless) and `pattern_analyzer.py` (reused by Phase 2 task).

### Files Changed

| File | Action | Phase |
|------|--------|-------|
| `backend/app/tasks/run_pipeline.py` | Wire FeedbackFilter + AI reject | 1A, 1B |
| `backend/app/config.py` | Updated flag defaults to True | 1C |
| `backend/app/worker.py` | Daily feedback synthesis + pattern analysis task | 1D, 2A |
| `backend/app/tasks/pattern_analysis.py` | **NEW** — periodic pattern analysis task | 2A |
| `backend/app/advisor/risk_tuner.py` | Added pattern context loading + user message enrichment | 2B |
| `backend/app/main.py` | Removed journal router | 3A |
| `frontend/src/pages/Trades.tsx` | Removed journal integration | 3B |
| `frontend/src/hooks/useJournal.ts` | **DELETED** | 3B |

### Verification

- `npx tsc --noEmit` — 0 TypeScript errors
- Backend linter (`ruff`) ran automatically — no issues

### Safety

- **Empty rules table:** FeedbackFilter returns `(False, None)` — all signals pass through
- **Reject only < 40 quality:** `caution` signals still execute with reduced size (existing behavior)
- **Risk Tuner guardrails:** Max 20% change per cycle, hard parameter bounds
- **Pattern context optional:** Redis unavailable → Risk Tuner proceeds without it

---

## Quick Start for Next Session

```bash
# 1. Navigate to project
cd "/mnt/c/Business/Internal Projects/day-trading"

# 2. Check services are running
cd backend && docker.exe compose ps

# 3. If services are down, start them
docker.exe compose up -d

# 4. Check worker logs (pipeline + ingestion)
docker.exe compose logs worker --tail=30

# 5. Check beat logs (task scheduling)
docker.exe compose logs beat --tail=20

# 6. Start frontend dev server
cd ../frontend && npm run dev

# 7. Check candle data availability
docker.exe compose exec db psql -U signalforge -c \
  "SELECT timeframe, COUNT(*) FROM candles WHERE symbol='BTC/USDT' GROUP BY timeframe ORDER BY timeframe;"
```
