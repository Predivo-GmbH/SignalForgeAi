# SignalForge

Multi-layer automated trading platform with AI-powered confluence scoring and adaptive risk management.

## Status

**Phases 1–7 complete.** All committed and pushed. **AI self-learning loop active.**

- 107+ commits on `main`
- Backend: 12 API routers (journal removed), ~40 endpoints, 3 WebSocket routes, 6-layer signal pipeline, AI advisor module, 13 Celery Beat tasks, 11 DB models
- Frontend: 8 pages, 16 hooks, ~21 components, dark/light theme
- Phase 7 added: AI Advisor (autonomous planner, signal quality, risk tuner, feedback loop), 8 configurable risk management features, portfolio backtester, frontend restructure
- Self-learning loop: FeedbackFilter wired → AI reject in live mode → Pattern Analysis → Risk Tuner → Feedback Synthesis (all daily, automated)
- AI cost tracking: Local token-based cost computation, Anthropic Admin API integration (dormant until admin key available)

## Project Structure
- `/backend` — Python 3.12 + FastAPI + SQLAlchemy 2.0 (~100 source files, ~50 test files)
- `/frontend` — React 19 + Vite 7 + TypeScript + Tailwind 4
- `/docs/PROJECT-STATUS.md` — **Full project documentation (read this first)**
- `/docs/SESSION-CHANGELOG-2026-03-02.md` — Detailed session changelog
- `/docs/plans/` — Implementation plans

## Commands
```bash
# Development (Docker — starts all 5 services: db, redis, api, worker, beat)
cd backend && docker.exe compose up -d
cd backend && docker.exe compose logs worker --tail=30  # Check pipeline/ingestion
cd backend && docker.exe compose restart worker beat     # After code changes

# Testing & Linting
cd backend && .venv/Scripts/python.exe -m pytest -q
cd backend && .venv/Scripts/python.exe -m ruff check .

# Frontend
cd frontend && npm run dev       # Dev server :5173 (password: signalforge)
cd frontend && npx vitest run
cd frontend && npm run lint
cd frontend && npm run build

# Production Docker
docker compose -f docker-compose.prod.yml up -d
```

> **Note:** Use `docker.exe` (not `docker`) on WSL2 with Docker Desktop for Windows.

## Rules
- NO hardcoded hex values in frontend components — use CSS custom property tokens (e.g. `bg-(--color-accent)`)
- NO magic px values — use Tailwind classes
- All components must support dark/light theme via CSS variables in `index.css`
- Backend: TDD — write failing test first, then implement
- Backend: All API endpoints need integration tests
- Frontend: Vitest with `globals: true` — do NOT import from 'vitest' in test files
- Commit frequently, one logical change per commit
- Always check existing code before modifying — read first
- **Questions → TEXT ONLY, NO TOOLS.** When the user's message is a question (contains "?", starts with "is/has/does/what/how/why/are" etc.), respond with TEXT ONLY. NEVER call Edit, Write, Bash, Agent, or any action tools. Reading files to inform the answer is OK, but do NOT modify anything. Describe what you'd do and wait for explicit action instructions.
  - TRAP: "is everything documented?" = ANSWER with findings, NOT "go fix the docs". "has the workflow been followed?" = ANSWER yes/no. Only imperative sentences ("update the docs", "fix the tests") are action requests.

### Strategy Parameter Integrity (CORE PRINCIPLE)
The AI Advisor chose the strategy parameters for a reason. If the market doesn't match, zero trades is the correct outcome — not a problem to "fix" by loosening things. Specifically:
- **Never** auto-override, auto-loosen, or "fall back" to weaker parameters just because zero signals/trades are generated.
- **Pipeline sensitivity params** (`min_trigger_count`, `trigger_lookback_candles`, `ema_slope_threshold`) are strategy identity — set by the AI Advisor at creation, never modified afterward.
- **RiskTuner** only adjusts risk management params (`min_confluence`, `max_risk_per_trade`, `max_daily_loss`, `atr_sl_multiplier`, `min_risk_reward`) based on actual trade results with 5+ closed trades.
- No system component should treat "no trades" as a problem to solve. The strategy is working correctly by staying out when conditions don't match.

### No AI, No Trading (CORE PRINCIPLE)
When Claude is unavailable, the system does NOT trade, guess, or fabricate analysis. Every AI-dependent component must abort or reject — never fall back to algorithmic approximations. Specifically:
- **Planner** returns `None` → API returns HTTP 503.
- **Signal Quality Evaluator** returns `recommendation="reject"` → signal is blocked.
- **Multi-Timeframe Analyzer** returns `recommendation="reject"` → signal is blocked.
- **Risk Tuner** returns empty adjustments → strategy config unchanged.
- **Feedback Synthesizer** returns empty rules → no rules created.
- **Pattern Analyzer** returns empty result → nothing stored.
- **Pipeline AI enrichment** failure → signal is rejected (not let through).
- No `_algorithmic_fallback()` methods exist anywhere in the advisor module.

## Frontend Pages & Navigation
Sidebar order: Dashboard → AI Advisor → Strategies → Trades → Analytics → Settings

| Route | Page | Key Feature |
|-------|------|-------------|
| `/` | Dashboard | PriceChart (6 TFs), StatsCards, PositionsTable |
| `/advisor` | AI Advisor | 3-step: Scan → Plan → Deploy. Master-detail with scan history sidebar |
| `/strategies` | Strategies | List deployed strategies with P&L, win rate, Sharpe |
| `/strategies/:id` | Strategy Detail | Signals tab + Validation/backtest tab |
| `/backtest` | Backtest | Standalone strategy validation tool |
| `/trades` | Trades | Execution log + performance metrics |
| `/analytics` | Analytics | Equity curve, metrics grid, correlation matrix |
| `/settings` | Settings | Connections (broker keys), Alerts (email), AI Usage (cost tracking) |

## Design Reference
- **Inspiration**: Kraken Pro trading UI (screenshots in `kraken-reference/`)
- **Theme**: Dark default (user-toggleable), purple accent `#7B61FF`
- **Typography**: Inter (UI), JetBrains Mono (prices/numbers)
- **CSS tokens**: Defined in `frontend/src/index.css` (:root and .dark)

## Config
- All backend env vars use `SF_` prefix (e.g. `SF_DATABASE_URL`, `SF_JWT_SECRET`)
- Frontend uses `VITE_API_URL` (defaults to `http://localhost:8000/api`)
- AI feature flags: all True — `ai_signal_quality_enabled`, `ai_risk_tuning_enabled`, `ai_feedback_loop_enabled`, etc.
- `SF_ANTHROPIC_API_KEY` — required for Claude calls (set in `backend/.env`)
- `SF_ANTHROPIC_ADMIN_API_KEY` — optional, for Anthropic Admin API cost reports (not available on individual plans)
- See `docs/PROJECT-STATUS.md` for full env var table

## Test Account
- Email: `roger@signalforge.dev` / Password: `SignalForge2026`
- Frontend password gate: `signalforge`

## Current System State (2026-03-03)
- 5 Docker services running (db, redis, api, worker, beat)
- 1 active strategy: "AI Advisor — Conservative Swing" (15 symbols, 4h, min_confluence: 70)
- All symbols currently blocked (chaotic_regime / no_trend / low_confluence)
- Candle data: 6 timeframes × 15+ symbols, ingested every 60s
- Broker connections stored but NOT wired to execution (PaperAdapter always used)
- `.gitattributes` enforces LF line endings (prevents WSL2/Windows CRLF ghost diffs)
- JWT token refresh on 401 responses (auto-retry before logout)
- WebSocket reconnect: exponential backoff (3s–30s cap), max 5 retries per channel

## Pipeline Checkpoint Rule
Before declaring any phase/step complete, re-read the plan to verify ALL deliverables are done. If anything is missing, continue working — do not skip ahead.
