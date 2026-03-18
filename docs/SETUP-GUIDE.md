# SignalForgeAI — Local Setup Guide

> Goal: Get the app running locally so you can use the Backtest Lab in the browser.

## Prerequisites

- **Docker Desktop** installed on Windows with WSL2 integration enabled
- **Node.js** (already installed — frontend `node_modules` exist)
- **Python 3.12+** (already installed — backend `.venv` exists)

---

## Step 1: Enable Docker in WSL2

1. Open **Docker Desktop** on Windows
2. Go to **Settings → Resources → WSL Integration**
3. Enable integration for your WSL2 distro
4. Click **Apply & Restart**
5. Verify in WSL2 terminal:
   ```bash
   docker --version
   ```

---

## Step 2: Create Backend `.env` File

```bash
cd "/mnt/c/Business/Internal Projects/SignalForgeAI/backend"
cp .env.example .env
```

The defaults are fine for local dev:
```
SF_DATABASE_URL=postgresql+asyncpg://signalforge:signalforge@localhost:5432/signalforge
SF_REDIS_URL=redis://localhost:6379/0
SF_JWT_SECRET=change-me-in-production
SF_DEBUG=true
SF_CORS_ORIGINS=["http://localhost:5173"]
```

---

## Step 3: Start TimescaleDB + Redis

```bash
cd "/mnt/c/Business/Internal Projects/SignalForgeAI/backend"
docker compose up -d
```

Wait for healthy status:
```bash
docker compose ps
```

Both `db` and `redis` should show "healthy".

---

## Step 4: Run Database Migrations

```bash
cd "/mnt/c/Business/Internal Projects/SignalForgeAI/backend"
.venv/Scripts/python.exe -m alembic upgrade head
```

If this fails with connection errors, wait a few seconds for PostgreSQL to finish starting, then retry.

---

## Step 5: Start the Backend Server

```bash
cd "/mnt/c/Business/Internal Projects/SignalForgeAI/backend"
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify: open http://localhost:8000/health in a browser — should return `{"status": "healthy", ...}`.

Leave this terminal running.

---

## Step 6: Start the Frontend Dev Server

In a **new terminal**:

```bash
cd "/mnt/c/Business/Internal Projects/SignalForgeAI/frontend"
npm run dev
```

Open http://localhost:5173 in your browser.

---

## Step 7: Access the App

1. **Password gate**: enter `signalforge`
2. **Register** a new account (or use test account: `roger@signalforge.dev` / `SignalForge2026`)
3. Navigate to **Backtest Lab** in the sidebar
4. Fill in Symbol (e.g. `BTC/USDT`), Timeframe (`1h`), Days (`30`)
5. Click **Run Backtest**

---

## Current Limitation

The backtest engine uses **synthetic (randomly generated) price data**, not real market data. This means:
- The signal pipeline runs correctly through all 6 layers
- Metrics (win rate, Sharpe ratio, drawdown, etc.) are calculated properly
- But the results don't reflect actual market conditions

Next step after verifying everything works: wire up real historical candle data from CCXT/Binance into the backtest engine.

---

## Quick Reference — All Commands

```bash
# Terminal 1: Docker services
cd "/mnt/c/Business/Internal Projects/SignalForgeAI/backend"
docker compose up -d

# Terminal 1: Migrations (one-time)
.venv/Scripts/python.exe -m alembic upgrade head

# Terminal 1: Backend server
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend server
cd "/mnt/c/Business/Internal Projects/SignalForgeAI/frontend"
npm run dev
```

## Ports

| Service       | Port  |
|---------------|-------|
| TimescaleDB   | 5432  |
| Redis         | 6379  |
| Backend API   | 8000  |
| Frontend      | 5173  |
