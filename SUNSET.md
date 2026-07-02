# SignalForgeAI — SUNSET (2026-07-02)

**Status:** Decommissioned. This is an archived project, not an active one.

## Why
The AI crypto-trading product was retired without a successor. It was never publicly launched (password gate active, Stripe never integrated). Decision by Roger, 2026-07-02.

## What was deleted
- Subdomain + web space `signalforgeai.predivo.ch` (Metanet/Plesk)
- Supabase project `xioqgsybkhjijkciinmu` (account `supabase@signalforgeai.predivo.ch`)
- All monitoring: production-monitor (commit `5a9306b`), keep-alive pings
- predivo.ch marketing surface: product page (predivo commit `bc1823f`) — URL returns 404 intentionally, no redirect
- BackOffice references: `list-project-users` edge function, API-management inventory (migration 069)
- codebase-memory index entry

## What was archived (before deletion)
- `docs\db-final-schema-2026-07-02.sql` — full schema dump (42 KB)
- `docs\db-final-data-2026-07-02.sql` — full data dump (3.4 MB)
- `docs\db-final-auth-data-2026-07-02.sql` — auth users
- No storage buckets existed (verified via Storage API)
- `C:\Business\Archive\SignalForgeAI-git-history-2026-07-02.bundle` — complete git history (verified)
- `C:\Business\Archive\SignalForgeAI-final-2026-07-02.zip` — full project folder incl. `.git` (verified, no node_modules)

## GitHub
Repo `Arivioo/SignalForgeAi` is **archived** (read-only), not deleted.

## Credentials
DB password, keys, CLI token: see `docs\Credentials.txt` and memory `reference_supabase_accounts.md`. All invalid once the Supabase project is deleted.
