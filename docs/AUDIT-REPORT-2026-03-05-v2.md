# SignalForgeAI Comprehensive Audit Report v2

**Date:** 2026-03-05
**Scope:** Full system — Backend, Frontend, Database, DevOps, Compliance, Documentation
**Context:** Third audit round. Previous rounds (v1) fixed 78 findings + 3 follow-ups. This audit found 46 net-new issues.

---

## Executive Summary

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High | 12 |
| Medium | 26 |
| Low | 8 |
| **Total** | **46** |

The platform is in strong shape after two prior audit rounds. No critical vulnerabilities remain. The high-severity findings cluster around three themes: **token lifecycle gaps** (refresh rotation, WebSocket blacklist, logout), **missing test coverage** for security-critical paths (GDPR, 2FA), and **DevOps hardening** for production readiness (CI scan enforcement, zero-downtime deploy, Redis auth). Medium findings are primarily missing indexes, input validation tightening, code organization, and documentation completeness.

---

## HIGH (12)

### SEC-H1: `POST /api/system/restart` lacks admin authorization
- **File:** `backend/app/api/system_status.py:187-204`
- **Description:** Any authenticated user can restart the Celery worker pool. No admin check like the one on `/ai-usage/credit`.
- **Fix:** Add admin guard: `if settings.admin_user_id and str(user_id) != settings.admin_user_id: raise HTTPException(403)`.

### SEC-H2: Refresh token not blacklisted on rotation
- **File:** `backend/app/auth/router.py:83-103`
- **Description:** `POST /auth/refresh` issues new tokens but the old refresh token remains valid for its full 7-day lifetime. A captured refresh token can be reused indefinitely.
- **Fix:** Add `jti` claim to refresh tokens; blacklist the old token when issuing a new pair.

### SEC-H3: WebSocket authentication skips token blacklist check
- **File:** `backend/app/ws/hub.py:76-87`
- **Description:** `_authenticate_ws()` validates the JWT but does not call `are_user_tokens_invalid()`. A user who changes their password can still receive data via an old WebSocket token.
- **Fix:** Add blacklist check in `_authenticate_ws()` (requires making it async).

### SEC-H4: CSP allows `unsafe-eval` unconditionally
- **File:** `backend/app/main.py:130-137`
- **Description:** `script-src 'self' 'unsafe-inline' 'unsafe-eval'` defeats XSS protection. `unsafe-eval` allows `eval()` and `Function()`.
- **Fix:** Gate on debug mode: `"'unsafe-eval'" if settings.debug else ""`.

### SEC-H5: 4 auth endpoints missing rate limits
- **File:** `backend/app/auth/router.py` — lines 106, 128, 156, 352
- **Description:** `GET /auth/me`, `PUT /auth/password`, `PUT /auth/email`, and `POST /auth/2fa/validate` lack `@limiter.limit()`. The 2FA validate endpoint is especially critical — TOTP codes have only ~1M possibilities per 30s window.
- **Fix:** Add `@limiter.limit("60/minute")` to `/me`, `@limiter.limit("5/minute")` to password/email change, `@limiter.limit("10/minute")` to 2FA validate. Add `request: Request` parameter to each.

### SEC-H6: `deploy_plan` bypasses validation on failure
- **File:** `backend/app/api/advisor.py:236-240`
- **Description:** When `StrategyConfig(**config)` validation fails, the raw unvalidated config is used anyway. An AI-generated plan with out-of-bounds risk parameters (e.g., `max_risk_per_trade: 0.99`) would be deployed without safety bounds.
- **Fix:** Remove the try/except fallback. Let validation errors return HTTP 422.

### DB-H7: TimescaleDB enabled but no hypertables created
- **File:** `backend/scripts/init-db.sql`
- **Description:** The `timescaledb` extension is loaded and the `timescale/timescaledb` Docker image is used, but `create_hypertable()` was never called on the `candles` table. No time-based partitioning, no compression, no chunk exclusion — all candle queries do full table scans.
- **Fix:** Add `SELECT create_hypertable('candles', 'time', if_not_exists => TRUE);` to init-db.sql. Optionally add compression policy for candles older than 7 days.

### TEST-H8: Zero test coverage for GDPR endpoints
- **File:** `backend/tests/test_auth.py`
- **Description:** `DELETE /auth/user` (account deletion with cascade) and `GET /auth/user/export` (data portability) have no tests. These are legally mandated functions. The SQLite test database doesn't enforce FK cascades by default (`PRAGMA foreign_keys` not set), so cascade deletion would silently fail in tests even if added.
- **Fix:** Add test cases for both endpoints. Add `PRAGMA foreign_keys=ON` event listener in conftest.py.

### LEGAL-H9: Terms of Service has placeholder jurisdiction
- **File:** `docs/TERMS-OF-SERVICE.md` Section 13
- **Description:** Contains `[Jurisdiction]` and `[Arbitration Body]` placeholders. The dispute resolution clause is unenforceable.
- **Fix:** Replace with actual jurisdiction (e.g., "Canton of Zurich, Switzerland").

### LEGAL-H10: MIT License contradicts proprietary ToS
- **File:** `LICENSE` vs `docs/TERMS-OF-SERVICE.md` Section 7-8
- **Description:** MIT License grants rights to "use, copy, modify, distribute, sublicense, and sell." The ToS prohibits "reverse engineering" and "redistribution." These directly contradict. Anyone with source access could invoke the MIT License to override ToS restrictions.
- **Fix:** Replace MIT with a proprietary license (e.g., "All Rights Reserved" or BSL) since this is a private repo.

### OPS-H11: CI security scans silently swallowed with `|| true`
- **File:** `.github/workflows/ci.yml:30,48`
- **Description:** Both `bandit` and `npm audit` always pass regardless of findings. Critical security vulnerabilities would not block merges.
- **Fix:** Remove `|| true`. Use `.bandit` config for known false positives. Use `--audit-level=critical` for npm.

### OPS-H12: Deploy script is NOT zero-downtime despite claiming so
- **File:** `deploy/deploy.sh:188-197`
- **Description:** Comment says "zero-downtime rolling restart" but `docker compose up -d` stops and recreates all containers simultaneously. Migrations run AFTER containers start, so new code briefly runs against old schema.
- **Fix:** Run migrations before restart. Restart services sequentially with `--no-deps`. Remove misleading comment until properly implemented.

---

## MEDIUM (26)

### SEC-M1: System status endpoint leaks internal error details
- **File:** `backend/app/api/system_status.py:55,66,87,137,204`
- **Fix:** Return generic "Connection failed" messages; log actual errors server-side only.

### SEC-M2: No logout / token revocation endpoint
- **File:** `backend/app/auth/router.py`
- **Fix:** Add `POST /auth/logout` that calls `blacklist_all_user_tokens()`.

### SEC-M3: Password complexity not enforced (only min 8 chars)
- **File:** `backend/app/auth/schemas.py:6`
- **Fix:** Add Pydantic field validator requiring uppercase + digit.

### SEC-M4: Market candle symbol/timeframe parameters not validated
- **File:** `backend/app/api/market.py:39-90`
- **Fix:** Validate symbol with regex and timeframe against `SUPPORTED_TIMEFRAMES`.

### SEC-M5: Strategy presets endpoint has no auth check
- **File:** `backend/app/api/strategies.py:271-275`
- **Fix:** Add `Depends(get_current_user)`.

### API-M6: `DeployRequest.plan` typed as bare `dict` with no validation
- **File:** `backend/app/api/advisor.py:37-38`
- **Fix:** Create a typed `PlanSchema` Pydantic model.

### API-M7: Data export endpoint loads ALL user data unbounded
- **File:** `backend/app/auth/router.py:432-436`
- **Fix:** Add `.limit(10000)` caps on each query, or stream as JSON lines.

### API-M8: N+1 query in `compare_strategies`
- **File:** `backend/app/api/analytics.py:193-200`
- **Fix:** Replace per-strategy loop with a single aggregated query using `strategy_id IN(...)`.

### API-M9: N+1 query in `bulk_import_cost_basis`
- **File:** `backend/app/api/holdings.py:727-748`
- **Fix:** Batch SELECT with `WHERE symbol IN (...)`.

### TASK-M10: `run_signal_pipeline` has no task lock
- **File:** `backend/app/tasks/run_pipeline.py:13-22`
- **Fix:** Add `with task_lock("run_signal_pipeline", timeout=3600)`.

### TASK-M11: `poll_orders.py` has silent `except Exception: pass`
- **File:** `backend/app/tasks/poll_orders.py:42-43`
- **Fix:** Replace `pass` with `logger.warning("Failed to release lock", exc_info=True)`.

### TASK-M12: `analyzer.py` has 5 silent `except Exception: pass` blocks
- **File:** `backend/app/advisor/analyzer.py:124,148,164,179,193`
- **Fix:** Replace with `logger.debug("Indicator %s failed", name, exc_info=True)`.

### TASK-M13: Redis connection leaks in `claude_client.py` sync methods
- **File:** `backend/app/advisor/claude_client.py:127-158,241-273`
- **Fix:** Add `r.close()` in `finally` blocks.

### TASK-M14: Position open race between `execute_signals` and `poll_orders`
- **File:** `backend/app/tasks/execute_signals.py:237-279`, `poll_orders.py:72-108`
- **Fix:** Add unique constraint on `Position.order_id` or use `SELECT FOR UPDATE`.

### DB-M15: Missing index on `Order.signal_id`
- **File:** `backend/app/models/order.py:18`
- **Fix:** Add `index=True`.

### DB-M16: Missing index on `Position.strategy_id`
- **File:** `backend/app/models/position.py:24`
- **Fix:** Add `index=True`.

### DB-M17: Missing index on `Trade.signal_id`
- **File:** `backend/app/models/trade.py:21`
- **Fix:** Add `index=True`.

### DB-M18: Model-defined indexes missing from migrations
- **File:** `backend/alembic/versions/`
- **Description:** `ix_trades_symbol`, `ix_trades_user_exit`, and `ix_signals_dedup` are in model `__table_args__` but absent from any migration file.
- **Fix:** Create a migration adding all three.

### DB-M19: Missing composite index on `SimulationSnapshot(simulation_id, timestamp)`
- **File:** `backend/app/models/simulation.py:38`
- **Fix:** Add to `__table_args__`.

### FE-M20: Missing aria-labels on Topbar icon buttons
- **File:** `frontend/src/components/layout/Topbar.tsx:37,51,60,73`
- **Fix:** Add `aria-label` to hamburger, help, theme toggle, and logout buttons.

### FE-M21: Missing focus trap in Modal component
- **File:** `frontend/src/components/ui/Modal.tsx`
- **Fix:** Implement Tab/Shift+Tab focus cycling and focus restore on close.

### FE-M22: HoldingsCard.tsx is 2006 lines — should be split
- **File:** `frontend/src/components/portfolio/HoldingsCard.tsx`
- **Fix:** Extract CoinIcon, DonutChart, SymbolAutocomplete, HoldingFormModal, HoldingRow into separate files.

### LEGAL-M23: Privacy Policy has placeholder contact email
- **File:** `docs/PRIVACY-POLICY.md` Sections 1, 14
- **Fix:** Replace `[owner@signalforge.dev]` with actual email.

### LEGAL-M24: Privacy Policy data retention periods are vague
- **File:** `docs/PRIVACY-POLICY.md` Section 7
- **Fix:** Add concrete periods (e.g., "Backups: 14 days. Auth logs: 90 days.").

### LEGAL-M25: Data export missing 7 data categories
- **File:** `backend/app/auth/router.py:411-495`
- **Description:** Missing: BrokerConnection, ManualHolding, CostBasisOverride, AIInsight, FeedbackRule, PaperSimulation, BacktestResult.
- **Fix:** Add all missing models to the export query.

### OPS-M26: Redis has no authentication in production
- **File:** `docker-compose.prod.yml:28`
- **Fix:** Add `--requirepass ${SF_REDIS_PASSWORD}` and update all Redis URLs.

---

## LOW (8 — selected most impactful)

| ID | Area | Description | File |
|----|------|-------------|------|
| L1 | Security | No `Permissions-Policy` header | `main.py` |
| L2 | API | `ClosePositionRequest.exit_price` allows negative/zero | `positions.py:25` |
| L3 | Task | `snapshot_simulation` and `send_daily_summary` lack task locks | `simulation_snapshot.py`, `send_alerts.py` |
| L4 | DB | Float used for all financial columns (should be Numeric) | All models |
| L5 | Frontend | Duplicate TRIGGER_LABELS in Trades.tsx and StrategyDetail.tsx | 2 files |
| L6 | Compliance | PII (email) logged in plaintext in `send_alerts.py` | `send_alerts.py:84-91` |
| L7 | DevOps | No Docker log rotation in production | `docker-compose.prod.yml` |
| L8 | DevOps | `.env.prod.template` missing 7+ config keys | `deploy/.env.prod.template` |

*Additional 35 low/info findings documented in individual agent reports — omitted here for brevity. Full details in agent transcripts.*

---

## Comparison with Previous Audit

| Metric | Audit v1 (Round 1) | Audit v2 (This Round) |
|--------|--------------------|-----------------------|
| Critical | 3 | 0 |
| High | 7 | 12 |
| Medium | 32 | 26 |
| Low | 22 | 8 (selected) |
| Info | 14 | — |
| **Total** | **78** | **46** |

**Key differences:**
- All 78 v1 findings were fixed or documented — none recurred
- v2 High findings are primarily **deeper issues** not visible in a first pass: token lifecycle (refresh rotation, WS blacklist), race conditions, missing test coverage
- v2 found **new categories**: TimescaleDB misconfiguration, license contradiction, GDPR test gaps, deployment zero-downtime gap
- Code quality, rate limiting, and error handling are now solid — v2 found only edge cases

---

## Recommended Fix Priority

### Phase 1 — Security (Before any public access)
1. SEC-H1: Admin guard on system restart
2. SEC-H2: Refresh token blacklisting
3. SEC-H3: WebSocket blacklist check
4. SEC-H4: CSP unsafe-eval gating
5. SEC-H5: Rate limits on 4 auth endpoints
6. SEC-H6: Remove deploy validation bypass

### Phase 2 — Data Integrity & Performance
7. DB-H7: Create candles hypertable
8. DB-M15/M16/M17: Add missing FK indexes
9. DB-M18: Add missing migration indexes
10. TASK-M10: Pipeline task lock
11. TASK-M13: Redis connection leak fix
12. API-M8/M9: Fix N+1 queries

### Phase 3 — Legal & Compliance (Before production launch)
13. LEGAL-H9: Fill ToS jurisdiction placeholder
14. LEGAL-H10: Replace MIT License
15. LEGAL-M23/M24: Fix Privacy Policy placeholders/retention
16. LEGAL-M25: Complete data export
17. TEST-H8: Add GDPR endpoint tests + SQLite FK fix

### Phase 4 — DevOps Hardening (Before production)
18. OPS-H11: Remove `|| true` from CI scans
19. OPS-H12: Fix deployment ordering (migrations before restart)
20. OPS-M26: Redis authentication
21. Add Docker log rotation, image cleanup, branch protection

### Phase 5 — Frontend & UX Polish
22. FE-M20/M21: Accessibility improvements
23. FE-M22: Split large component files
24. SEC-M2: Add logout endpoint
25. SEC-M3: Password complexity

---

*Report generated by 7 parallel audit agents. Full individual agent reports available in task transcripts.*
