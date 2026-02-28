# SignalForge — Phase 1 Agent Team Handoff

## Team Overview

5-agent team building Phase 1 (Foundation) of SignalForge.

| Agent | Role | Tasks | Dependencies |
|-------|------|-------|-------------|
| `@infra-engineer` | Docker Compose, Dockerfile, Nginx, CI | 3, 13 | None (goes first) |
| `@backend-core` | FastAPI skeleton, JWT auth, SQLAlchemy models, Alembic | 2, 4, 5 | @infra-engineer (needs Docker DB) |
| `@signal-engine` | Indicator library, Layer 1 (Trend), Layer 2 (Zones), Backtest + CLI | 6, 7, 8, 10 | @backend-core (needs app scaffold) |
| `@data-engineer` | CCXT ingestion, candle storage, TimescaleDB helpers | 9 | @backend-core (needs models) |
| `@frontend` | Vite scaffold, Tailwind 4, theme tokens, password gate, auth pages | 11, 12 | None (independent) |

## Pipeline

```
Phase 1: @infra-engineer + @frontend (parallel)
Phase 2: @backend-core (after infra)
Phase 3: @signal-engine + @data-engineer (parallel, after backend-core)
Phase 4: Integration review
```

## Shared References

- **Design doc**: `docs/plans/2026-02-28-signalforge-design.md`
- **Phase 1 plan**: `docs/plans/2026-02-28-phase1-foundation.md` (detailed TDD steps per task)
- **CLAUDE.md**: Project rules and commands
- **Kraken reference**: `kraken-reference/` (284 screenshots — design inspiration)

## Conventions

- Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, pytest
- React 18, Vite, TypeScript, Tailwind 4, shadcn/ui, Vitest
- TDD: write failing test → implement → verify pass → commit
- One logical change per commit
- Commit message format: `feat(scope): description` or `fix(scope):` or `chore:`

## Key Config Values

- DB: `postgresql+asyncpg://signalforge:signalforge@localhost:5432/signalforge`
- Redis: `redis://localhost:6379/0`
- Env prefix: `SF_` (e.g., `SF_DATABASE_URL`, `SF_JWT_SECRET`)
- Frontend dev port: 5173
- Backend API port: 8000
- Password gate: `signalforge2026`
