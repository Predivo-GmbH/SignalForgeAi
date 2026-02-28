# SignalForge

Multi-layer automated trading platform with confluence scoring.

## Status

**Phases 1–6 complete.**

- 89 commits on `main`, 296 backend tests, 41 frontend tests, 0 lint errors
- Backend: 11 API routers, 33 endpoints, 3 WebSocket routes, 6-layer signal pipeline, HMM regime, AI journal, WFO
- Frontend: 9 pages, 14 hooks, 14 components, WebSocket integration, dark/light theme
- Phase 6 added: broker adapters (Alpaca/CCXT/Paper), DB-backed execution, Celery Beat (8 tasks), circuit breakers, rate limiting, structured logging, production Docker

## Project Structure
- `/backend` — Python 3.12 + FastAPI + SQLAlchemy 2.0 (83 source files, 45 test files)
- `/frontend` — React 19 + Vite 7 + TypeScript + Tailwind 4
- `/docs/PROJECT-STATUS.md` — **Full project documentation (read this first)**
- `/docs/plans/` — Implementation plans for all 6 phases

## Commands
```bash
# Backend (use venv Python on Windows)
cd backend && docker compose up -d                     # Start TimescaleDB + Redis
cd backend && .venv/Scripts/python.exe -m pytest -q     # 296 tests
cd backend && .venv/Scripts/python.exe -m ruff check .  # Lint
cd backend && .venv/Scripts/python.exe -m uvicorn app.main:app --reload  # Dev server :8000

# Celery (Phase 6)
cd backend && celery -A app.worker worker --loglevel=info   # Worker
cd backend && celery -A app.worker beat --loglevel=info      # Beat scheduler

# Frontend
cd frontend && npm run dev       # Dev server :5173 (password: signalforge)
cd frontend && npx vitest run    # 41 tests
cd frontend && npm run lint      # ESLint
cd frontend && npm run build     # Production build (558KB JS)

# Production Docker
docker compose -f docker-compose.prod.yml up -d  # All 5 services
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
- `SF_ENCRYPTION_KEY` — Fernet key for broker credential encryption
- See `docs/PROJECT-STATUS.md` for full env var table

## Test Account
- Email: `roger@signalforge.dev` / Password: `SignalForge2026`
- Frontend password gate: `signalforge`

## Agent Team Pattern
Each phase uses **Cloud Agent Teams** — named agents dispatched via Task tool with `isolation: "worktree"`, working in dependency-ordered waves. Merge to main after each wave passes all quality gates.

## Pipeline Checkpoint Rule
Before declaring any phase/step complete, re-read the plan to verify ALL deliverables are done. If anything is missing, continue working — do not skip ahead.
