# SignalForge

Multi-layer automated trading platform with confluence scoring.

## Project Structure
- `/backend` — Python 3.12 + FastAPI + SQLAlchemy 2.0
- `/frontend` — React 18 + Vite + TypeScript + Tailwind 4
- `/docs` — Design docs, plans, reference materials

## Commands
- Backend: `cd backend && docker compose up -d` (starts all services)
- Backend tests: `cd backend && pytest -v`
- Backend lint: `cd backend && ruff check app/`
- Frontend dev: `cd frontend && npm run dev` (port 5173)
- Frontend tests: `cd frontend && npx vitest run`
- Frontend build: `cd frontend && npm run build`
- Backtest CLI: `cd backend && python -m app.cli backtest --symbol BTC/USDT --timeframe 1h --days 30`

## Rules
- NO hardcoded hex values in frontend components — use theme tokens from `lib/colors.ts`
- NO magic px values — use Tailwind classes
- All components must support dark/light theme via CSS variables
- Backend: TDD — write failing test first, then implement
- Backend: All API endpoints need integration tests
- Frontend: Vitest with `globals: true` — do NOT import from 'vitest' in test files
- Commit frequently, one logical change per commit
- Always check existing code before modifying — read first

## Design Reference
- **Inspiration**: Kraken Pro trading UI (screenshots in `kraken-reference/`)
- **Design doc**: `docs/plans/2026-02-28-signalforge-design.md`
- **Phase 1 plan**: `docs/plans/2026-02-28-phase1-foundation.md`
- **Theme**: Dark default (user-toggleable), purple accent `#7B61FF`
- **Typography**: Inter (UI), JetBrains Mono (prices/numbers)

## Pipeline Checkpoint Rule
Before declaring any phase/step complete, re-read the plan to verify ALL deliverables are done. If anything is missing, continue working — do not skip ahead.
