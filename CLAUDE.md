# SignalForgeAI

Multi-layer automated trading platform with AI-powered confluence scoring and adaptive risk management.

## MANDATORY DELIVERY GATE — BEFORE EVERY DELIVERY

**This is not optional. Skipping this = wasting Roger's time.**

Before delivering ANY change (code, UI, bug fix, feature, refactor):

1. **DESIGN FIRST** — Read all relevant files. Plan the full architecture BEFORE coding. For UI: know the DOM structure, coordinate systems, positioning. Write the verification test FIRST.
2. **BUILD COMPLETELY** — Implement the complete solution in one pass. Not incremental patches. `npm run build` must pass.
3. **TEST THOROUGHLY** — Kill and restart dev server. If UI change: run Puppeteer at 1920x1080 (standard) AND deviceScaleFactor=2 (retina). Measure alignment programmatically — don't eyeball. ALL tests must pass.
4. **DELIVER WITH EVIDENCE** — Show test output proving it works. 1 feature = 1 commit. Tell user to hard-refresh.

**If ANY gate fails: STOP. Fix. Re-test. Do NOT deliver.**

### Communication Rules
- **Results, not explanations.** Fix it and show it works.
- **Evidence, not promises.** Show test output, not "it should work now."
- **No "probably" or "should be"** — either verified or not delivered.

---

## Stack

- **Frontend**: React 19 + Vite 7 + TypeScript + Tailwind CSS 4, deployed to Metanet via FTP
- **Backend**: Supabase (PostgreSQL + Edge Functions + Auth + Realtime + Vault)
- **State**: Zustand + TanStack React Query
- **Auth**: Supabase Email OTP (6-digit, 600s expiry)
- **Realtime**: Supabase Realtime (postgres_changes + broadcast)
- **Cron**: pg_cron + pg_net invoking Edge Functions
- **AI**: Claude API via `npm:@anthropic-ai/sdk`
- **Exchange**: CCXT via `npm:ccxt`
- **Indicators**: `npm:technicalindicators` + custom VWAP/Fibonacci
- **CI/CD**: GitHub Actions → lint → test → build → FTP deploy

## Project Structure
- `/frontend` — React 19 + Vite 7 + TypeScript + Tailwind 4
- `/supabase/migrations/` — 8 SQL migration files (schema, RLS, pg_cron, RPCs)
- `/supabase/functions/` — 19 Edge Functions + `_shared/` utilities
- `/supabase/functions/_shared/engine/` — 6-layer signal pipeline (9 TypeScript modules)
- `/supabase/functions/_shared/advisor/` — AI advisor system (9 TypeScript modules)
- `/supabase/config.toml` — Supabase project configuration
- `/.github/workflows/deploy.yml` — CI/CD pipeline

## Commands
```bash
# Frontend development
cd frontend && npm run dev       # Dev server :5173
cd frontend && npm run build     # Production build
cd frontend && npm run lint      # ESLint
cd frontend && npm test          # Vitest

# Supabase (requires supabase CLI)
supabase db push                 # Apply migrations
supabase functions deploy --all  # Deploy all Edge Functions
supabase functions serve         # Local Edge Function dev server
```

## Rules
- NO hardcoded hex values in frontend components — use CSS custom property tokens (e.g. `bg-(--color-accent)`)
- NO magic px values — use Tailwind classes
- All components must support dark/light theme via CSS variables in `index.css`
- Frontend: Vitest with `globals: true` — do NOT import from 'vitest' in test files
- Commit frequently, one logical change per commit
- Always check existing code before modifying — read first
- **Questions → TEXT ONLY, NO TOOLS.** When the user's message is a question (contains "?"), respond with TEXT ONLY. NEVER call Edit, Write, Bash, Agent, or any action tools. Reading files to inform the answer is OK, but do NOT modify anything.

### Strategy Parameter Integrity (CORE PRINCIPLE)
The AI Advisor chose the strategy parameters for a reason. If the market doesn't match, zero trades is the correct outcome — not a problem to "fix" by loosening things. Specifically:
- **Never** auto-override, auto-loosen, or "fall back" to weaker parameters just because zero signals/trades are generated.
- **Pipeline sensitivity params** (`min_trigger_count`, `trigger_lookback_candles`, `ema_slope_threshold`) are strategy identity — set by the AI Advisor at creation, never modified afterward.
- **RiskTuner** only adjusts risk management params based on actual trade results with 5+ closed trades.
- No system component should treat "no trades" as a problem to solve. The strategy is working correctly by staying out when conditions don't match.

### No AI, No Trading (CORE PRINCIPLE)
When Claude is unavailable, the system does NOT trade, guess, or fabricate analysis. Every AI-dependent component must abort or reject — never fall back to algorithmic approximations.

## Architecture

### Edge Functions (19 total)
**CRUD (14):** signals, trades, strategies, broker, market, positions, holdings, analytics, backtests, regime, simulation, ai-usage, engine-monitor, system-status

**Cron (4):**
- `engine-cron` — every 1min: candle ingestion → signal pipeline → order execution → position management
- `daily-maintenance` — 02:00 UTC: risk tuning, feedback synthesis, pattern analysis, cleanup
- `simulation-snapshot` — hourly: B&H vs paper portfolio snapshots
- `universe-expansion` — every 6h: discover new symbols, backfill candles

**SSE (1):** advisor — scan → plan → deploy with streaming progress

### Signal Pipeline (6 layers)
```
Candles → L0: Regime (ADX+ATR) → L1: Trend (EMA alignment)
       → L2: Zones (Fibonacci+S/R) → L3: Confluence (14-factor scorer)
       → L4: Triggers (5 types) → L5: Risk (ATR stops + sizing)
       → Feedback Filter → Output: BUY/SELL/NO_TRADE
```

### Database (16 tables)
profiles, strategies, signals, trades, orders, positions, broker_connections, candles, pipeline_logs, ai_insights, feedback_rules, paper_simulations, simulation_snapshots, backtest_results, manual_holdings, cost_basis_overrides

### Frontend Pages
Sidebar order: Dashboard → AI Advisor → Strategies → Trades → Analytics → Settings

| Route | Page | Key Feature |
|-------|------|-------------|
| `/` | Dashboard | PriceChart (6 TFs), StatsCards, PositionsTable |
| `/advisor` | AI Advisor | 3-step: Scan → Plan → Deploy with scan history |
| `/strategies` | Strategies | List deployed strategies with P&L, win rate, Sharpe |
| `/strategies/:id` | Strategy Detail | Signals tab + Validation/backtest tab |
| `/backtest` | Backtest | Standalone strategy validation tool |
| `/trades` | Trades | Execution log + performance metrics |
| `/analytics` | Analytics | Equity curve, metrics grid, correlation matrix |
| `/risk` | Risk Management | Drawdown tracking |
| `/engine` | Signal Engine | Pipeline monitoring |
| `/settings` | Settings | Connections (broker keys), Alerts (email), AI Usage (cost tracking) |

## Design Reference
- **Theme**: Dark default (user-toggleable), purple accent `#7B61FF`
- **Typography**: Inter (UI), JetBrains Mono (prices/numbers)
- **CSS tokens**: Defined in `frontend/src/index.css` (:root and .dark)

## Config
- Frontend uses `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`
- Edge Functions use env vars: `ANTHROPIC_API_KEY`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`
- AI feature flags: all enabled by default
- Supabase Vault stores broker API credentials (not in DB columns)

## Pipeline Checkpoint Rule
Before declaring any phase/step complete, re-read the plan to verify ALL deliverables are done. If anything is missing, continue working — do not skip ahead.
