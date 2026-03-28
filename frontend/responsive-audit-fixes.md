# SignalForgeAI — Mobile Responsive Audit: Fixes Applied

**Date:** 2026-03-28
**Phase:** 1 (Code-Level Analysis + Fixes) + Phase 2 (Visual Verification)
**Build Status:** PASS (0 errors)
**Total Findings:** 110 (1 Critical, 21 High, 66 Medium, 22 Low)
**Total Fixes Applied:** 110/110 (100%)

---

## Summary of Changes by Category

| Category | Fixes | Files |
|----------|-------|-------|
| Responsive padding (p-5/p-6 → responsive) | 35 | 22 |
| Touch targets (min-h-[44px]) | 20 | 15 |
| Scroll affordance (fade gradients) | 12 | 11 |
| Layout overflow prevention | 10 | 8 |
| Touch device support (tap interactions) | 5 | 5 |
| Tab bar improvements | 3 | 3 |
| Mobile column hiding for tables | 2 | 2 |
| Misc (cleanup, truncation, viewport clamping) | 23 | 14 |

---

## Files Modified (44 total)

### Shared UI Components (5 files)

**`src/components/ui/DataTable.tsx`**
- Wrapped `overflow-x-auto` in `relative` container with right-edge fade gradient
- Changed cell padding from `px-4 py-3` to `px-2 sm:px-4 py-2 sm:py-3`

**`src/components/ui/Pagination.tsx`**
- Changed to `flex flex-col sm:flex-row` for mobile stacking
- Hidden "Previous"/"Next" text on mobile (icon-only)

**`src/components/ui/RiskDisclaimer.tsx`**
- `p-4` → `p-3 sm:p-4`

**`src/components/ui/Tooltip.tsx`**
- Already had tap-to-toggle (no changes needed)

**`src/components/layout/RouteAnnouncer.tsx`**
- Deleted (duplicate of `shared/RouteAnnouncer.tsx`); `App.tsx` import updated

---

### Auth Pages (9 files)

**`src/pages/auth/LoginPage.tsx`**
- Added `min-h-[44px]` to tab buttons (Password / Email Code)
- Added `min-h-[44px]` to "Use a different email" button
- Changed forgot password link from `text-xs` to `text-sm`

**`src/pages/auth/SignUpPage.tsx`**
- Added `min-h-[44px]` to "Use a different email" button
- Changed Terms/Privacy from `text-xs` to `text-sm` with `py-1 inline-block`

**`src/pages/auth/ForgotPasswordPage.tsx`**
- Added `min-h-[44px] inline-flex items-center` to "try again" button and "Back to sign in" link

**`src/pages/auth/ResetPasswordPage.tsx`**
- Added `min-h-[44px] inline-flex items-center` to "Sign in" link

**`src/pages/auth/AuthVerifyPage.tsx`**
- Added `min-h-[44px] inline-flex items-center` to error state links

**`src/components/auth/ResendTimer.tsx`**
- Added `min-h-[44px] py-2.5 px-4` to "Resend code" button

**`src/components/auth/AuthLayout.tsx`**
- Header: `px-6` → `px-4 sm:px-6`
- Logo link: added `min-h-[44px] flex items-center`

**`src/components/shared/PasswordGate.tsx`**
- `p-8` → `p-5 sm:p-8`

**`src/components/auth/OtpInput.tsx`**
- `w-12` → `w-10 sm:w-12`, `h-14` → `h-12 sm:h-14`

---

### Dashboard (11 files)

**`src/pages/Dashboard.tsx`**
- Tab bar: added `snap-x snap-mandatory`, `snap-start` on tabs, active underline `border-b-2`, right-edge fade gradient, labels visible on mobile
- ComparisonBar: `flex-col sm:flex-row`, badge gets `min-w-0 truncate`
- SimulationChart: added `onTouchMove`/`onTouchEnd` handlers; Y-axis width `w-10 sm:w-[52px]`
- Removed unused `Y_LABEL_W` constant

**`src/components/dashboard/StatsCards.tsx`**
- All `p-5` → `p-3 sm:p-5` (skeleton + real cards)

**`src/components/dashboard/SimulationPortfolio.tsx`**
- Added `hidden sm:table-cell` on Quantity, Price, 24h Change columns
- Added scroll affordance gradient

**`src/components/dashboard/PriceChart.tsx`**
- Added `flex-wrap` to header
- `px-4` → `px-3 sm:px-4`

**`src/components/dashboard/UsdtReserveWidget.tsx`**
- `p-4` → `p-3 sm:p-4`
- Grid: `grid-cols-3` → `grid-cols-2 sm:grid-cols-3`
- Added `min-h-[44px]` to "Apply" and "Set manually" buttons

**`src/components/dashboard/SignalFeed.tsx`**
- All `px-4` → `px-3 sm:px-4`

**`src/components/dashboard/RegimeWidget.tsx`**
- All `p-4` → `p-3 sm:p-4`

**`src/components/dashboard/PositionsTable.tsx`**
- Added scroll affordance gradient

**`src/components/dashboard/WatchlistTab.tsx`**
- Chip remove buttons: `p-0.5` → `p-2`
- Accordion buttons: added `min-h-[44px]`

**`src/components/dashboard/SimulationCard.tsx`**
- Loading state `p-5` → `p-4 sm:p-5`

---

### Strategies + Backtest + Advisor (5 files)

**`src/pages/Strategies.tsx`**
- StrategyCard: `p-5` → `p-3 sm:p-5`
- Actions container: added `flex-wrap`
- Empty state button: `py-2.5` → `py-3`

**`src/pages/StrategyDetail.tsx`**
- Header: added `flex-col sm:flex-row`, removed `shrink-0` from buttons, `p-5` → `p-3 sm:p-5`
- Signals table: added scroll affordance gradient
- Filter selects: added `w-full sm:w-auto`
- Back button: added `min-h-[44px]`
- Tab bar: added `overflow-x-auto snap-x snap-mandatory` + `snap-start`
- SignalStatusWithTooltip: added `onClick` toggle for touch
- Sort headers: added `min-h-[44px]`

**`src/components/backtest/StrategyBacktestForm.tsx`**
- `p-6` → `p-4 sm:p-6`
- Config grid: `gap-x-4` → `gap-x-3 sm:gap-x-4`

**`src/components/backtest/StrategyBacktestResults.tsx`**
- All `p-6` → `p-4 sm:p-6`
- MetricCard: `p-4` → `p-3 sm:p-4`
- Per-symbol table: added scroll affordance gradient
- Sort headers: added `min-h-[44px]`

**`src/pages/Advisor.tsx`**
- Plan header buttons: `flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3`
- All `p-5`/`px-5` → responsive variants
- Investment input: `w-48` → `w-full sm:w-48`
- Scan sidebar delete: `opacity-0 group-hover:opacity-100` → `sm:opacity-0 sm:group-hover:opacity-100`
- StepIndicator: added `aria-label` per step
- Deploy buttons: `gap-3` → `gap-2 sm:gap-3`
- Sidebar: `max-h-48` → `max-h-64 sm:max-h-72`
- Scan results table: added scroll affordance gradient
- Retry + Clear All buttons: added `min-h-[44px]`

---

### Trades + Analytics + Risk + Engine (5 files)

**`src/pages/Trades.tsx`**
- Table: added scroll affordance gradient
- Rows: `py-2.5` → `py-3`
- ReasoningTooltip: added `onClick` toggle for touch

**`src/pages/Analytics.tsx`**
- All `p-6` → `p-4 sm:p-6` (7 instances)
- Strategy table: added scroll affordance gradient
- Table headers: `py-2.5` → `py-3`

**`src/components/analytics/EquityCurve.tsx`**
- Empty state: `p-6` → `p-4 sm:p-6`
- Chart height: `h-[350px]` → `h-[250px] sm:h-[350px]`

**`src/pages/Risk.tsx`**
- DrawdownCard + AccountCard: `p-5` → `p-4 sm:p-5`
- Equity values: added `truncate`

**`src/pages/Engine.tsx`**
- All `p-5`/`px-5` → responsive (12 instances)
- Main grid: `gap-6` → `gap-4 sm:gap-6`
- Pipeline detail table: added scroll affordance gradient, `py-2` → `py-3`
- Pipeline run button: added `min-h-[44px]`
- Clear filters button: added `min-h-[44px] py-2`
- FilterDropdown options: `py-1.5` → `py-2.5`
- FilterDropdown: added viewport clamping (`maxWidth`, `left` clamp)
- Simulation stat grid: `grid-cols-2` → `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4`
- StatBox values: added `truncate`

---

### Portfolio + Settings (10 files)

**`src/pages/Settings.tsx`**
- Tab bar: added `snap-x snap-mandatory`, `snap-start`, right-edge fade gradient
- ConnectForm: added `border-t` visual separation
- ExchangeRoutingTab: pair rows stack on mobile (`flex-col sm:flex-row`), removed fixed min-widths on mobile, hidden header labels on mobile, warning `ml-[136px]` → `ml-0 sm:ml-[136px]`
- All card `p-5` → `p-3 sm:p-5` (5 instances)

**`src/components/settings/AiUsageTab.tsx`**
- Header: `flex-col sm:flex-row sm:items-center sm:justify-between`
- All `p-5` → `p-3 sm:p-5` (5 instances)
- Update button: added `min-h-[44px] flex items-center`
- API Calls table: added scroll affordance gradient

**`src/components/portfolio/HoldingsCard.tsx`**
- Table: `table-fixed sm:table-auto` → `table-auto`
- Table + SourceBreakdown: added scroll affordance gradients
- PortfolioLoader: `p-6` → `p-4 sm:p-6`
- Period buttons: increased touch targets with `min-h-[44px]`
- Sort headers: added `min-h-[44px]`
- Empty state button: added `min-h-[44px]`

**`src/components/portfolio/DonutChart.tsx`**
- Added `onClick` toggle for tap-to-see slice info

**`src/components/portfolio/AssetDetailModal.tsx`**
- Removed inner `max-h-[75vh]` (double-scroll fix)
- Source table: added scroll affordance gradient

**`src/components/portfolio/SymbolAutocomplete.tsx`**
- Added viewport-aware positioning: flips dropdown above input when near bottom

**`src/components/portfolio/PerformanceSummary.tsx`**
- 5th stat card: `col-span-2 sm:col-span-1` to prevent orphaned card

**`src/components/portfolio/ActiveStrategyCard.tsx`**
- All `p-5` → `p-3 sm:p-5` (3 instances)

**`src/components/portfolio/PortfolioEquitySection.tsx`**
- Metric values: added `truncate`

**`src/components/portfolio/HoldingRow.tsx`**
- Clickable `<tr>`: added `min-h-[44px]`

---

## Phase 2: Visual Verification (Playwright)

**Viewport:** 430x932px (iPhone 14 Pro Max equivalent), dark mode
**Screenshots:** 18 pages captured, all reviewed

### Results: ALL PAGES PASS

| # | Page | Status | Notes |
|---|------|--------|-------|
| 01 | Login | PASS | Tabs, inputs, buttons properly sized. Risk disclaimer visible. |
| 02 | Sign Up | PASS | Step indicators, form inputs, Terms/Privacy links all fit. |
| 03 | Forgot Password | PASS | Clean single-column layout, "Back to sign in" link visible. |
| 04 | Reset Password | PASS | Two inputs + button, proper spacing. |
| 05 | Dashboard (top) | PASS | Hamburger menu, topbar icons fit. Tab bar has underline indicator. Holdings empty state centered. |
| 06 | Dashboard (bottom) | PASS | No scroll overflow. Empty state page fits viewport. |
| 07 | AI Advisor | PASS | "New Scan" button full width. Empty states well-centered. |
| 08 | Strategies | PASS | Empty state card with "Go to AI Advisor" button properly sized. |
| 09 | Backtest | PASS | Form inputs, source tabs, slider, toggle all fit 430px. |
| 10 | Trades (top) | PASS | Stat cards stack single-column. Table headers (TIME, SYMBOL, SIDE, P&L) fit. |
| 11 | Trades (bottom) | PASS | Empty state centered. |
| 12 | Analytics (top) | PASS | Error states (no backend) display cleanly. "Paper Test" card well-formatted. |
| 13 | Analytics (bottom) | PASS | 2-column skeleton grid at bottom looks balanced. |
| 14 | Risk | PASS | Account Overview stacked cards. Drawdown with progress bar. 2-col equity grid fits. |
| 15 | Engine (top) | PASS | All cards stack single-column. Pipeline Summary 2x2 grid fits 430px. |
| 16 | Engine (bottom) | PASS | Pipeline Run History section visible. |
| 17 | Settings (top) | PASS | Tab bar scrollable with fade gradient. Profile cards clean. OTP badge fits. |
| 18 | Settings (bottom) | PASS | "Log out" card visible. |

### Observations

- All pages render without horizontal overflow at 430px
- No overlapping elements detected
- Card padding is appropriately tighter on mobile (responsive `p-3 sm:p-5` working)
- Tab bars show underline indicators and scroll affordance gradients
- Touch targets appear properly sized on all visible buttons/links
- Empty states are well-centered with appropriate spacing
- Error states (no backend) display cleanly without layout issues

### Limitation

Screenshots show **empty/error states only** (no live Supabase connection during audit). Pages with real data (tables with rows, charts with data, portfolio with holdings) were audited code-level in Phase 1 but cannot be visually verified without mock data. The Phase 1 code analysis covers these scenarios with pixel-level layout math.

---

## Cleanup

- `screenshot-audit.mjs` left in project root for future use
- `.env.local` with `VITE_SCREENSHOT_MODE=true` was created temporarily and deleted after screenshots
- `VITE_SCREENSHOT_MODE` bypass code was added to AuthContext and PasswordGate temporarily and reverted after screenshots
- `test-screenshots/` directory contains all 18 PNG screenshots for reference

---

## Final Status

| Metric | Value |
|--------|-------|
| Phase 1 findings | 110 |
| Phase 1 fixes applied | 110/110 (100%) |
| Phase 2 screenshots | 18/18 pass |
| Phase 2 new findings | 0 |
| Build status | PASS (0 errors) |
| Files modified | 44 |
