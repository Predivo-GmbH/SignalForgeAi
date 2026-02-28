# SignalForge

Multi-layer automated trading platform with confluence scoring.

## Status

**Phases 1–5 complete. Phase 6 PLANNED — ready for implementation.**

- 50 commits on `main`, 197 backend tests, 37 frontend tests, 0 lint errors
- Backend: 10 API routers, 30 endpoints, 6-layer signal pipeline, HMM regime, AI journal, WFO
- Frontend: 9 pages, 12 hooks, 14 components, WebSocket integration, dark/light theme
- **Phase 6 design**: `docs/plans/2026-02-28-phase6-live-trading-design.md` (APPROVED)
- **Phase 6 plan**: `docs/plans/2026-02-28-phase6-implementation.md` (13 tasks, 5 waves)

## Project Structure
- `/backend` — Python 3.12 + FastAPI + SQLAlchemy 2.0 (62 source files, 33 test files)
- `/frontend` — React 19 + Vite 7 + TypeScript + Tailwind 4 (46 source files, 12 test files)
- `/docs` — Design docs, plans, reference materials
- `/docs/PROJECT-STATUS.md` — **Full project documentation (read this first)**
- `/docs/plans/` — Implementation plans for all 6 phases

## Commands
```bash
# Backend (use venv Python on Windows)
cd backend && docker compose up -d                     # Start TimescaleDB + Redis
cd backend && .venv/Scripts/python.exe -m pytest -q     # 197 tests
cd backend && .venv/Scripts/python.exe -m ruff check .  # Lint
cd backend && .venv/Scripts/python.exe -m uvicorn app.main:app --reload  # Dev server :8000

# Frontend
cd frontend && npm run dev       # Dev server :5173 (password: signalforge)
cd frontend && npx vitest run    # 37 tests
cd frontend && npm run lint      # ESLint
cd frontend && npm run build     # Production build (554KB JS)

# Backtest CLI
cd backend && python -m app.cli backtest --symbol BTC/USDT --timeframe 1h --days 30
```

## Rules
- NO hardcoded hex values in frontend components — use CSS custom property tokens (e.g. `bg-(--color-accent)`)
- NO magic px values — use Tailwind classes
- All components must support dark/light theme via CSS variables in `index.css`
- Backend: TDD — write failing test first, then implement
- Backend: All API endpoints need integration tests
- Frontend: Vitest with `globals: true` — do NOT import from 'vitest' in test files
- Commit frequently, one logical change per commit
- Always check existing code before modifying — read first

## Design Reference
- **Inspiration**: Kraken Pro trading UI (screenshots in `kraken-reference/`)
- **Design doc**: `docs/plans/2026-02-28-signalforge-design.md`
- **Theme**: Dark default (user-toggleable), purple accent `#7B61FF`
- **Typography**: Inter (UI), JetBrains Mono (prices/numbers)
- **CSS tokens**: Defined in `frontend/src/index.css` (:root and .dark)

## Config
- All backend env vars use `SF_` prefix (e.g. `SF_DATABASE_URL`, `SF_JWT_SECRET`)
- Frontend uses `VITE_API_URL` (defaults to `http://localhost:8000/api`)
- See `docs/PROJECT-STATUS.md` for full env var table

## Agent Team Pattern
Each phase uses **Cloud Agent Teams** — named agents dispatched via Task tool with `isolation: "worktree"`, working in dependency-ordered waves. Merge to main after each wave passes all quality gates.

## Pipeline Checkpoint Rule
Before declaring any phase/step complete, re-read the plan to verify ALL deliverables are done. If anything is missing, continue working — do not skip ahead.
