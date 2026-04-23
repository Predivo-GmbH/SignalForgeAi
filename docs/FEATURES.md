# SignalForgeAI — Feature Registry

> Auto-generated feature list based on codebase analysis.
> Every feature must have at least one unit test before release.

---

### F-001: Authentication (Email OTP + Password)
- **Route:** `/login`, `/signup`, `/forgot-password`, `/reset-password`, `/auth/verify`, `/auth/callback`
- **Components:** `AuthContext`, `LoginPage`, `SignUpPage`, `ForgotPasswordPage`, `ResetPasswordPage`, `AuthVerifyPage`, `AuthCallbackPage`, `AuthLayout`, `OtpInput`, `PasswordStrength`, `ResendTimer`
- **Hooks:** `useAuth`
- **Edge Functions:** `send-auth-email`
- **DB Tables:** `profiles`
- **Critical Assertions:** OTP send/verify flow, password sign-in, password reset, profile upsert on sign-in, sign-out clears session, delete account
- **Status:** tested
- **Test Files:**
  - Unit: `frontend/src/lib/__tests__/auth.test.ts`
  - Unit: `frontend/src/pages/__tests__/Login.test.tsx`
  - Unit: `frontend/src/components/auth/__tests__/password-utils.test.ts`

---

### F-002: Password Gate (Private Beta)
- **Route:** All routes (wraps entire app)
- **Components:** `PasswordGate`
- **Critical Assertions:** Blocks access without correct code, SHA-256 hash comparison, sessionStorage persistence, unlock reveals children
- **Status:** tested
- **Test Files:**
  - Unit: `frontend/src/components/shared/__tests__/PasswordGate.test.tsx`

---

### F-003: Protected Routes
- **Route:** All authenticated routes
- **Components:** `ProtectedRoute`
- **Critical Assertions:** Redirects to /login when unauthenticated, shows loading state, renders Outlet when authenticated
- **Status:** tested
- **Test Files:**
  - Unit: `frontend/src/components/__tests__/ProtectedRoute.test.tsx`

---

### F-004: Dashboard / Portfolio
- **Route:** `/`
- **Components:** `PortfolioPage`, `AccountHero`, `ActiveStrategyCard`, `HoldingsCard`, `HoldingRow`, `HoldingFormModal`, `AssetDetailModal`, `CoinIcon`, `DonutChart`, `PerformanceSummary`, `PortfolioEquitySection`, `SymbolAutocomplete`, `SimulationCard`, `SimulationPortfolio`, `StatsCards`, `SystemHealthBanner`, `UsdtReserveWidget`, `WatchlistTab`, `RegimeWidget`, `SignalFeed`, `PriceChart`, `PositionsTable`
- **Hooks:** `usePositions`, `useSimulation`, `useDashboardSnapshot`, `useHoldings`, `useWatchlist`, `useRegimeStatus`, `useTradeStream`, `usePriceStream`
- **Edge Functions:** `simulation`, `market`, `regime`, `positions`
- **DB Tables:** `positions`, `manual_holdings`, `paper_simulations`, `simulation_snapshots`
- **Critical Assertions:** Stats cards render values, loading states, simulation card shows data
- **Status:** tested
- **Test Files:**
  - Unit: `frontend/src/components/dashboard/__tests__/StatsCards.test.tsx`

---

### F-005: AI Advisor (Scan → Plan → Deploy)
- **Route:** `/advisor`
- **Components:** `AdvisorPage`
- **Hooks:** `useAdvisor` (useGeneratePlan, useDeployPlan)
- **Store:** `advisorStore`
- **Edge Functions:** `advisor`
- **DB Tables:** `strategies`, `ai_insights`
- **Critical Assertions:** Scan starts/completes/fails, plan generation, deploy creates strategy, scan history persistence, cancel scan
- **Status:** tested
- **Test Files:**
  - Unit: `frontend/src/stores/__tests__/advisorStore.test.ts`
  - Unit: `frontend/src/hooks/__tests__/useAdvisor.test.ts`

---

### F-006: Strategies Management
- **Route:** `/strategies`
- **Components:** `StrategiesPage`
- **Hooks:** `useStrategies`, `useCreateStrategy`, `useUpdateStrategy`, `useToggleStrategy`, `useDeleteStrategy`, `useStrategyPresets`, `useExchangeAvailability`
- **Edge Functions:** `strategies`
- **DB Tables:** `strategies`
- **Critical Assertions:** List renders, create/toggle/delete, presets load, exchange availability check
- **Status:** tested
- **Test Files:**
  - Unit: `frontend/src/pages/__tests__/Strategies.test.tsx`
  - Unit: `frontend/src/hooks/__tests__/useStrategies.test.ts`

---

### F-007: Strategy Detail
- **Route:** `/strategies/:id`
- **Components:** `StrategyDetailPage`
- **Hooks:** `useStrategy`, `useSignals`, `useTradeStats`, `useRunStrategyBacktest`
- **Edge Functions:** `strategies`, `signals`, `backtests`
- **DB Tables:** `strategies`, `signals`, `trades`
- **Critical Assertions:** Detail renders, not-found state, signals tab, backtest tab
- **Status:** tested
- **Test Files:**
  - Unit: `frontend/src/pages/__tests__/StrategyDetail.test.tsx`

---

### F-008: Backtest / Strategy Validation
- **Route:** `/backtest`
- **Components:** `BacktestPage`, `StrategyBacktestForm`, `StrategyBacktestResults`
- **Hooks:** `useRunStrategyBacktest`, `useRunWalkForward`
- **Edge Functions:** `backtests`
- **DB Tables:** `backtest_results`
- **Critical Assertions:** Form renders, run backtest mutation, results display, walk-forward optimization
- **Status:** tested
- **Test Files:**
  - Unit: `frontend/src/pages/__tests__/Backtest.test.tsx`

---

### F-009: Trades Log
- **Route:** `/trades`
- **Components:** `TradesPage`
- **Hooks:** `useTrades`, `useTradeStats`
- **Edge Functions:** `trades`, `analytics`
- **DB Tables:** `trades`
- **Critical Assertions:** Table headers render, pagination, trade stats display
- **Status:** tested
- **Test Files:**
  - Unit: `frontend/src/pages/__tests__/Trades.test.tsx`

---

### F-010: Analytics
- **Route:** `/analytics`
- **Components:** `AnalyticsPage`, `EquityCurve`, `MetricsGrid`
- **Hooks:** `useEquityHistory`, `useCorrelation`, `useStrategyComparison`
- **Edge Functions:** `analytics`
- **DB Tables:** `trades`, `signals`
- **Critical Assertions:** Page renders, equity curve loads, strategy comparison, correlation matrix
- **Status:** tested
- **Test Files:**
  - Unit: `frontend/src/pages/__tests__/Analytics.test.tsx`

---

### F-011: Risk Management
- **Route:** `/risk`
- **Components:** `RiskPage`
- **Hooks:** `useDrawdownState`, `usePositions`
- **Edge Functions:** `simulation`
- **DB Tables:** `positions`
- **Critical Assertions:** Drawdown tracking renders, risk levels display
- **Status:** tested
- **Test Files:**
  - Unit: `frontend/src/pages/__tests__/Risk.test.tsx`

---

### F-012: Signal Engine Monitor
- **Route:** `/engine`
- **Components:** `EnginePage`
- **Hooks:** `useEngineStatus`, `usePipelineLog`, `usePipelineSummary`, `usePipelineRuns`
- **Edge Functions:** `engine-monitor`
- **DB Tables:** `pipeline_logs`
- **Critical Assertions:** Engine status renders, pipeline log table, run history
- **Status:** tested
- **Test Files:**
  - Unit: `frontend/src/pages/__tests__/Engine.test.tsx`

---

### F-013: Settings (Broker + Alerts + AI Usage)
- **Route:** `/settings`
- **Components:** `SettingsPage`, `AiUsageTab`, `TwoFactorSetup`
- **Hooks:** `useBrokerConnections`, `useConnectBroker`, `useDisconnectBroker`, `useBrokerHealth`, `useAiUsage`, `useUpdateCredit`, `useProfile`, `useChangeEmail`
- **Edge Functions:** `broker`, `ai-usage`
- **DB Tables:** `broker_connections`, `ai_insights`, `profiles`
- **Critical Assertions:** Tab navigation, broker list/connect/disconnect, AI usage summary, credit update
- **Status:** tested
- **Test Files:**
  - Unit: `frontend/src/pages/__tests__/Settings.test.tsx`
  - Unit: `frontend/src/tests/useBrokerConnections.test.ts`
  - Unit: `frontend/src/hooks/__tests__/useAiUsage.test.ts`

---

### F-014: Layout (Sidebar + Topbar + AppLayout)
- **Route:** All authenticated routes
- **Components:** `AppLayout`, `Sidebar`, `Topbar`, `HelpDrawer`
- **Stores:** `useSidebar`
- **Critical Assertions:** Sidebar renders nav links, logo, collapse toggle, mobile overlay, topbar renders
- **Status:** tested
- **Test Files:**
  - Unit: `frontend/src/components/layout/__tests__/Sidebar.test.tsx`
  - Unit: `frontend/src/stores/__tests__/sidebar.test.ts`

---

### F-015: Theme (Dark/Light Toggle)
- **Components:** (integrated in Topbar)
- **Store:** `useTheme`
- **Critical Assertions:** Default dark theme, toggle switches class on documentElement, persists to localStorage
- **Status:** tested
- **Test Files:**
  - Unit: `frontend/src/stores/__tests__/theme.test.ts`

---

### F-016: Realtime (WebSocket / Supabase Realtime)
- **Components:** (consumed by dashboard widgets)
- **Lib:** `ws.ts`
- **Hooks:** `useSignalStream`, `usePriceStream`, `useTradeStream`, `useWebSocket`
- **Critical Assertions:** Exports subscribeTable/subscribeBroadcast/disconnectAll, disconnectAll runs without error
- **Status:** tested
- **Test Files:**
  - Unit: `frontend/src/lib/__tests__/ws.test.ts`

---

### F-017: API Layer
- **Lib:** `api.ts`
- **Critical Assertions:** ApiError class, invokeFunction wraps supabase.functions.invoke, queryTable builds query with filters/order/limit, insertRow/updateRow/deleteRow
- **Status:** tested
- **Test Files:**
  - Unit: `frontend/src/lib/__tests__/api.test.ts`

---

### F-018: Formatting Utilities
- **Lib:** `format.ts`
- **Critical Assertions:** pnlColor returns correct classes, formatPrice handles different magnitudes, fmtUsd with nulls, formatPnl signed prefix, formatPnlPercent
- **Status:** tested
- **Test Files:**
  - Unit: `frontend/src/lib/__tests__/format.test.ts`

---

### F-019: Utility Functions
- **Lib:** `cn.ts`, `colors.ts`, `utils.ts`, `constants.ts`, `cryptoSymbols.ts`
- **Critical Assertions:** cn merges classes, cssVar reads custom properties, friendlyAuthError maps errors, TRIGGER_LABELS has entries, CRYPTO_LIST is populated
- **Status:** tested
- **Test Files:**
  - Unit: `frontend/src/lib/__tests__/utils.test.ts`

---

### F-020: UI Components (Badge, DataTable, Modal, Pagination, Tooltip, RiskDisclaimer)
- **Components:** `Badge`, `DataTable`, `Modal`, `Pagination`, `Tooltip`, `RiskDisclaimer`
- **Critical Assertions:** Badge renders variants, DataTable renders headers/rows/empty/loading, Pagination shows range, Modal focus trap
- **Status:** tested
- **Test Files:**
  - Unit: `frontend/src/components/ui/__tests__/Badge.test.tsx`
  - Unit: `frontend/src/components/ui/__tests__/DataTable.test.tsx`
  - Unit: `frontend/src/components/ui/__tests__/Pagination.test.tsx`

---

### F-021: System Status & Health
- **Components:** `SystemHealthBanner` (in dashboard)
- **Hooks:** `useSystemStatus`, `useRestartWorker`
- **Edge Functions:** `system-status`
- **Critical Assertions:** Status query returns health info, rapid poll toggle, restart worker mutation
- **Status:** tested
- **Test Files:**
  - Unit: `frontend/src/hooks/__tests__/useSystemStatus.test.ts`

---

### F-022: Holdings Management
- **Components:** `HoldingFormModal`, `HoldingsCard`, `HoldingRow`
- **Hooks:** `useHoldings`, `useAddHolding`, `useUpdateHolding`, `useDeleteHolding`, `useBulkImportHoldings`
- **DB Tables:** `manual_holdings`
- **Critical Assertions:** CRUD operations, bulk import, value calculation
- **Status:** tested
- **Test Files:**
  - Unit: `frontend/src/hooks/__tests__/useHoldings.test.ts`

---

### F-023: Page Title & SEO
- **Hooks:** `usePageTitle`, `useNoIndex`
- **Components:** `RouteAnnouncer`
- **Critical Assertions:** Title set with suffix, noindex meta tag added/removed, route announcer for screen readers
- **Status:** tested
- **Test Files:**
  - Unit: `frontend/src/hooks/__tests__/usePageTitle.test.ts`

---

### F-024: Simulation (Paper Trading vs Buy & Hold)
- **Hooks:** `useSimulation`, `useStartSimulation`, `useStopSimulation`, `useCombinedPortfolio`, `useUpdateReserve`
- **Edge Functions:** `simulation`, `simulation-snapshot`
- **DB Tables:** `paper_simulations`, `simulation_snapshots`
- **Critical Assertions:** Start/stop simulation, portfolio fetch, reserve update
- **Status:** tested
- **Test Files:**
  - Unit: `frontend/src/hooks/__tests__/useSimulation.test.ts`

---

### F-025: Query Client Configuration
- **Lib:** `query.ts`
- **Critical Assertions:** QueryClient configured with staleTime, retry, refetchOnWindowFocus settings
- **Status:** tested
- **Test Files:**
  - Unit: `frontend/src/lib/__tests__/query.test.ts`

<!-- END FEATURES -->
