# Phase 6 Handoff Prompt

Copy everything below the line into a new Claude Code window.

---

## SignalForge — Phase 6: Live Trading & Hardening (IMPLEMENTATION)

Project root: `C:\Business\Internal Projects\day-trading`

Read these files first (in this order):
1. `CLAUDE.md`
2. `docs/PROJECT-STATUS.md`
3. `docs/plans/2026-02-28-phase6-implementation.md` (THE PLAN — this is what you're building)
4. `docs/plans/2026-02-28-phase6-live-trading-design.md` (design context)

### What's already done
- Phases 1-5 COMPLETE (50 commits, 197 backend tests, 37 frontend tests, 0 lint errors)
- Phase 6 design APPROVED and implementation plan WRITTEN
- All documentation updated (`CLAUDE.md`, `PROJECT-STATUS.md`)

### What you need to do
Execute the Phase 6 implementation plan (`docs/plans/2026-02-28-phase6-implementation.md`). It has **13 tasks across 5 dependency-ordered waves**.

Dispatch **Cloud Agent Teams** — named agents with `isolation: "worktree"`, running in parallel within each wave. After each wave completes, merge all worktree branches to `main`, verify quality gates (tests + lint), then start the next wave.

### Wave structure
```
Wave 1 (parallel, no deps):         @db-models, @broker-adapters, @crypto-api
Wave 2 (parallel, needs Wave 1):    @position-manager, @order-executor, @candle-storage
Wave 3 (parallel, needs Wave 2):    @ingestion-tasks, @execution-tasks, @alert-tasks
Wave 4 (parallel, needs Wave 3):    @realtime, @hardening
Wave 5 (parallel, needs Wave 4):    @docker-prod, @frontend-wiring
```

### Quality gates (run after EVERY wave merge)
```bash
cd backend && .venv/Scripts/python.exe -m pytest -q
cd backend && .venv/Scripts/python.exe -m ruff check .
cd frontend && npx vitest run
cd frontend && npm run lint
cd frontend && npm run build
```

### Key commands
```bash
# Backend tests
cd backend && .venv/Scripts/python.exe -m pytest -q

# Backend lint
cd backend && .venv/Scripts/python.exe -m ruff check .

# Frontend tests
cd frontend && npx vitest run

# Frontend lint + build
cd frontend && npm run lint && npm run build

# Install new deps (Wave 1 needs these)
cd backend && .venv/Scripts/pip.exe install alpaca-py structlog slowapi cryptography
```

### Rules
- Each agent gets ONE task from the plan — give it the full task description from the plan file
- Agents run with `isolation: "worktree"` so they work in parallel without conflicts
- After all agents in a wave complete, merge each worktree branch to main
- Run quality gates after merge — fix any failures before starting next wave
- TDD: write failing test → implement → test passes → commit
- Follow CLAUDE.md rules (no hardcoded hex, use CSS tokens, Vitest globals:true, etc.)

Build fast, no time-boxing. Start with Wave 1 — dispatch all 3 agents in parallel.
