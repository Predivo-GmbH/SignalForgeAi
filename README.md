# SignalForgeAI

AI-powered cryptocurrency trading platform with automated signal generation, portfolio management, and risk analysis.

## Features

- **AI Advisor** -- Claude-powered market analysis and strategy recommendations
- **Signal Engine** -- 6-layer technical analysis pipeline (trend, zones, triggers, confluence, regime, risk)
- **Portfolio Management** -- CoinGecko-style dashboard with real-time holdings tracking
- **Backtesting** -- Historical strategy validation with detailed performance metrics
- **Risk Management** -- Kelly Criterion, CPPI, HMM regime detection, correlation monitoring
- **Paper Trading** -- Simulated trading with buy-and-hold comparison
- **Live Trading** -- Automated order execution via Binance (with 2FA protection)

## Tech Stack

- **Backend:** Python 3.12, FastAPI, Celery, SQLAlchemy (async), TimescaleDB, Redis
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS, TanStack Query
- **AI:** Anthropic Claude API
- **Infrastructure:** Docker, GitHub Actions CI, Caddy reverse proxy

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 20+
- Python 3.12+

### Development Setup

1. **Clone and configure:**
   ```bash
   git clone https://github.com/Arivioo/SignalForgeAI.git
   cd SignalForgeAI
   cp backend/.env.example backend/.env
   # Edit backend/.env with your settings
   ```

2. **Start backend services:**
   ```bash
   cd backend
   docker compose up -d
   ```

3. **Start frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

4. **Access the app:**
   - Frontend: http://localhost:5173
   - API docs: http://localhost:8000/docs (debug mode)

## Documentation

- [Setup Guide](docs/SETUP-GUIDE.md)
- [User Guide](docs/USER-GUIDE.md)
- [Deployment Guide](docs/DEPLOYMENT-GUIDE.md)
- [Project Status](docs/PROJECT-STATUS.md)
- [Trading System Deep Dive](docs/TRADING-SYSTEM-DEEP-DIVE.md)
- [Privacy Policy](docs/PRIVACY-POLICY.md)
- [Terms of Service](docs/TERMS-OF-SERVICE.md)

## Architecture

```
backend/
  app/
    api/          # 18 FastAPI routers (66+ endpoints)
    auth/         # JWT + TOTP 2FA authentication
    advisor/      # AI-powered market analysis
    engine/       # 6-layer signal pipeline
    execution/    # Order execution & position management
    tasks/        # 14 Celery background tasks
    models/       # SQLAlchemy ORM models
    core/         # Database, Redis, encryption, logging
frontend/
  src/
    pages/        # 8 main pages + detail views
    components/   # Reusable UI components
    hooks/        # 29 custom React hooks
    lib/          # API client, auth, WebSocket, utilities
```

## Testing

```bash
# Backend tests (351 passing)
cd backend && pytest -v

# Frontend tests (34 passing)
cd frontend && npm test
```

## License

See [LICENSE](LICENSE) for details.
