# SignalForgeAI

AI-powered cryptocurrency trading platform with automated signal generation, portfolio management, and risk analysis.

## Features

- **AI Advisor** -- Claude-powered market analysis and strategy recommendations
- **Signal Engine** -- 6-layer technical analysis pipeline (regime, trend, zones, confluence, triggers, risk)
- **Portfolio Management** -- Real-time holdings tracking with exchange integrations
- **Backtesting** -- Historical strategy validation with detailed performance metrics
- **Risk Management** -- ATR-based stops, position sizing, drawdown monitoring
- **Paper Trading** -- Simulated trading with buy-and-hold comparison
- **Live Trading** -- Automated order execution via CCXT (Binance, KuCoin, Kraken, MEXC)

## Tech Stack

- **Frontend:** React 19, TypeScript, Vite 7, Tailwind CSS 4, Zustand, TanStack Query
- **Backend:** Supabase (PostgreSQL, Edge Functions, Auth, Realtime, Vault)
- **AI:** Anthropic Claude API (Haiku/Sonnet/Opus tiers)
- **Exchange:** CCXT (TypeScript)
- **Indicators:** technicalindicators + custom VWAP/Fibonacci
- **Deploy:** GitHub Actions CI/CD → Metanet FTP

## Quick Start

### Prerequisites
- Node.js 22+
- Supabase CLI (`npm i -g supabase`)

### Development Setup

1. **Clone and configure:**
   ```bash
   git clone https://github.com/Arivioo/SignalForgeAI.git
   cd SignalForgeAI
   ```

2. **Set up Supabase:**
   ```bash
   supabase init
   supabase db push          # Apply migrations
   supabase functions serve  # Start local Edge Functions
   ```

3. **Start frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

4. **Access the app:** http://localhost:5173

## Architecture

```
frontend/
  src/
    pages/        # 11 pages (Dashboard, Advisor, Strategies, etc.)
    components/   # Reusable UI components
    hooks/        # 22 custom React hooks (Supabase queries)
    contexts/     # AuthContext (Supabase OTP)
    lib/          # Supabase client, API helpers, Realtime
supabase/
  migrations/     # 8 SQL migrations (schema, RLS, pg_cron, RPCs)
  functions/
    _shared/      # 25 shared TypeScript modules
      engine/     # 6-layer signal pipeline (9 modules)
      advisor/    # AI advisor system (9 modules)
    19 Edge Functions (CRUD, cron, SSE)
```

### Signal Pipeline

```
Candles → Regime (ADX+ATR) → Trend (EMA alignment)
       → Zones (Fibonacci+S/R) → Confluence (14-factor scorer)
       → Triggers (5 types) → Risk (ATR stops + sizing)
       → Feedback Filter → Output: BUY/SELL/NO_TRADE
```

### Edge Functions

| Function | Schedule | Purpose |
|----------|----------|---------|
| `engine-cron` | Every 1min | Candle ingestion → pipeline → execution → position management |
| `daily-maintenance` | 02:00 UTC | Risk tuning, feedback synthesis, pattern analysis, cleanup |
| `simulation-snapshot` | Hourly | B&H vs paper portfolio snapshots |
| `universe-expansion` | Every 6h | Discover new symbols, backfill candles |

## Testing

```bash
cd frontend && npm test      # Vitest
cd frontend && npm run lint  # ESLint
cd frontend && npm run build # Production build
```

## License

See [LICENSE](LICENSE) for details.
