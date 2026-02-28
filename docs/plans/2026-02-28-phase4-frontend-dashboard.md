# Phase 4 — Frontend Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the complete SignalForge frontend — auth flow, layout shell, 7 pages (Dashboard, Signals, Trades, Backtest Lab, Strategy Config, API Keys, Trade Journal), WebSocket integration, and API client layer.

**Architecture:** React 19 SPA with TanStack Query for server state, Zustand for client state, react-router-dom for routing, lightweight-charts for TradingView-style candlestick charts, and native WebSocket for real-time price/signal streams. Kraken Pro-inspired dark-first design using the existing CSS custom property token system.

**Tech Stack:** React 19.2, TypeScript 5.9, Vite 7.3, Tailwind 4.2, TanStack Query 5, Zustand 5, react-router-dom 7, lightweight-charts 4, lucide-react icons, existing shadcn/ui primitives.

---

## Existing Code Inventory

### Frontend (7 files)
- `src/App.tsx` — PasswordGate wrapping LoginPage, theme toggle on mount
- `src/main.tsx` — React root with StrictMode
- `src/index.css` — Full dark/light CSS custom property token system
- `src/lib/cn.ts` — clsx + twMerge utility
- `src/lib/colors.ts` — Runtime color constants (accent, positive, negative, warning)
- `src/lib/theme.ts` — Zustand theme store with localStorage persist (`sf-theme`)
- `src/components/PasswordGate.tsx` — Password gate (`signalforge2026`, sessionStorage)
- `src/pages/Login.tsx` — Placeholder stub

### Backend API Endpoints (all require Bearer JWT except auth)
- `POST /api/auth/register` → `{ access_token, refresh_token }`
- `POST /api/auth/login` → `{ access_token, refresh_token }`
- `POST /api/auth/refresh` → `{ access_token, refresh_token }`
- `GET /api/signals` → `{ signals[], total, limit, offset }`
- `GET /api/signals/{id}` → `SignalResponse`
- `POST /api/signals/generate` → `GenerateSignalResponse`
- `GET /api/trades` → `{ trades[], total, limit, offset }`
- `GET /api/trades/{id}` → `TradeResponse`
- `GET /api/trades/stats` → `{ total_trades, win_rate, profit_factor, total_pnl, avg_pnl, best_trade, worst_trade }`
- `GET /api/strategies` → `{ strategies[], total }`
- `POST /api/strategies` → `StrategyResponse` (201)
- `GET /api/strategies/{id}` → `StrategyResponse`
- `PUT /api/strategies/{id}` → `StrategyResponse`
- `POST /api/strategies/{id}/activate` → `StrategyResponse` (toggles is_active)
- `DELETE /api/strategies/{id}` → 204
- `GET /api/market/symbols` → `string[]` (9 symbols)
- `GET /api/market/candles/{symbol}/{timeframe}` → `{ symbol, timeframe, candles[], count }`
- `GET /api/engine/status` → `{ active, layers[], supported_symbols[], supported_timeframes[] }`
- `POST /api/backtests` → backtest result JSON
- `GET /api/backtests` → `[]` (stub)
- `GET /api/positions` → `Position[]`
- `GET /api/positions/account` → `{ equity, daily_pnl, open_positions, max_positions }`
- `POST /api/positions/{id}/close` → `Position`
- `WS /ws/signals` — Real-time signal stream (JWT via query param)
- `WS /ws/prices` — Real-time price stream

### Config
- `vite.config.ts` — Path alias `@/` → `./src/`, port 5173, jsdom test env
- `tsconfig.app.json` — Strict, `@/*` paths, ES2022 target, `verbatimModuleSyntax: true`

---

## Task 1: Install Dependencies

**Files:**
- Modify: `frontend/package.json`

**Step 1: Install runtime dependencies**

Run:
```bash
cd frontend && npm install react-router-dom @tanstack/react-query lightweight-charts
```

**Step 2: Install type definitions**

Run:
```bash
cd frontend && npm install -D @types/react-router-dom
```

Note: `@tanstack/react-query` and `lightweight-charts` ship their own types.

**Step 3: Verify build still passes**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors.

**Step 4: Commit**

```bash
cd frontend && git add package.json package-lock.json
git commit -m "feat(frontend): install router, query, and chart dependencies"
```

---

## Task 2: API Client + Auth Store

**Files:**
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/auth.ts`
- Create: `frontend/src/lib/query.ts`
- Test: `frontend/src/lib/__tests__/auth.test.ts`

**Step 1: Write the auth store test**

```typescript
// frontend/src/lib/__tests__/auth.test.ts
import { useAuth } from "../auth";

describe("auth store", () => {
  beforeEach(() => {
    localStorage.clear();
    useAuth.setState({
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
    });
  });

  test("login sets tokens and isAuthenticated", () => {
    useAuth.getState().setTokens("access-123", "refresh-456");
    const state = useAuth.getState();
    expect(state.accessToken).toBe("access-123");
    expect(state.refreshToken).toBe("refresh-456");
    expect(state.isAuthenticated).toBe(true);
  });

  test("logout clears tokens", () => {
    useAuth.getState().setTokens("a", "r");
    useAuth.getState().logout();
    const state = useAuth.getState();
    expect(state.accessToken).toBeNull();
    expect(state.isAuthenticated).toBe(false);
  });

  test("persists to localStorage", () => {
    useAuth.getState().setTokens("a", "r");
    // Zustand persist writes to localStorage under the key "sf-auth"
    const stored = JSON.parse(localStorage.getItem("sf-auth") || "{}");
    expect(stored.state?.accessToken).toBe("a");
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/lib/__tests__/auth.test.ts`
Expected: FAIL — module `../auth` not found.

**Step 3: Implement auth store**

```typescript
// frontend/src/lib/auth.ts
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthStore {
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  setTokens: (access: string, refresh: string) => void;
  logout: () => void;
}

export const useAuth = create<AuthStore>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      setTokens: (access, refresh) =>
        set({ accessToken: access, refreshToken: refresh, isAuthenticated: true }),
      logout: () =>
        set({ accessToken: null, refreshToken: null, isAuthenticated: false }),
    }),
    { name: "sf-auth" }
  )
);
```

**Step 4: Implement API client**

```typescript
// frontend/src/lib/api.ts
import { useAuth } from "./auth";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const { accessToken } = useAuth.getState();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    useAuth.getState().logout();
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
```

**Step 5: Create query client provider**

```typescript
// frontend/src/lib/query.ts
import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});
```

**Step 6: Run tests**

Run: `cd frontend && npx vitest run src/lib/__tests__/auth.test.ts`
Expected: 3 tests PASS.

**Step 7: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

**Step 8: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/lib/auth.ts frontend/src/lib/query.ts frontend/src/lib/__tests__/auth.test.ts
git commit -m "feat(frontend): add API client, auth store, and query client"
```

---

## Task 3: Router + Auth Pages

**Files:**
- Create: `frontend/src/pages/Register.tsx`
- Modify: `frontend/src/pages/Login.tsx` — Replace placeholder with real form
- Create: `frontend/src/components/ProtectedRoute.tsx`
- Modify: `frontend/src/App.tsx` — Add router, QueryClientProvider
- Modify: `frontend/src/main.tsx` — Wrap with BrowserRouter
- Test: `frontend/src/pages/__tests__/Login.test.tsx`

**Step 1: Write Login page test**

```typescript
// frontend/src/pages/__tests__/Login.test.tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { LoginPage } from "../Login";

describe("LoginPage", () => {
  test("renders email and password fields", () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );
    expect(screen.getByPlaceholderText("Email")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });

  test("has link to register page", () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );
    expect(screen.getByText(/create account/i)).toBeInTheDocument();
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/pages/__tests__/Login.test.tsx`
Expected: FAIL — placeholder "Email" not found (current Login.tsx is just a stub).

**Step 3: Implement Login page**

Replace `frontend/src/pages/Login.tsx` with a full login form:
- Email + password inputs
- Submit handler calling `api.post("/auth/login", { email, password })`
- On success: `useAuth.getState().setTokens(data.access_token, data.refresh_token)` → navigate to `/`
- Error state display
- Link to `/register`
- Uses existing theme tokens (`--color-bg-base`, `--color-bg-surface`, `--color-border`, etc.)

**Step 4: Implement Register page**

`frontend/src/pages/Register.tsx` — same layout as Login:
- Email + password + confirm password inputs
- Submit → `api.post("/auth/register", { email, password })`
- On success: setTokens → navigate to `/`
- Link to `/login`

**Step 5: Implement ProtectedRoute**

```typescript
// frontend/src/components/ProtectedRoute.tsx
import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@/lib/auth";

export function ProtectedRoute() {
  const isAuthenticated = useAuth((s) => s.isAuthenticated);
  return isAuthenticated ? <Outlet /> : <Navigate to="/login" replace />;
}
```

**Step 6: Update App.tsx with router**

Replace `frontend/src/App.tsx`:
- Wrap everything in `QueryClientProvider` + `Routes`
- Public routes: `/login`, `/register`
- Protected routes (wrapped in `<ProtectedRoute>`): `/`, `/signals`, `/trades`, `/backtest`, `/config`, `/keys`, `/journal`
- Protected routes render inside `<AppLayout>` (Task 4)
- Keep `PasswordGate` wrapping everything
- Keep theme effect

**Step 7: Update main.tsx**

Wrap `<App />` with `<BrowserRouter>`.

**Step 8: Run tests**

Run: `cd frontend && npx vitest run`
Expected: All tests pass.

**Step 9: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

**Step 10: Commit**

```bash
git add frontend/src/pages/Login.tsx frontend/src/pages/Register.tsx \
  frontend/src/components/ProtectedRoute.tsx frontend/src/App.tsx \
  frontend/src/main.tsx frontend/src/pages/__tests__/Login.test.tsx
git commit -m "feat(frontend): add auth pages, router, and protected routes"
```

---

## Task 4: Layout Shell

**Files:**
- Create: `frontend/src/components/layout/AppLayout.tsx`
- Create: `frontend/src/components/layout/Sidebar.tsx`
- Create: `frontend/src/components/layout/Topbar.tsx`
- Create: `frontend/src/lib/sidebar.ts` (Zustand collapsed state)
- Test: `frontend/src/components/layout/__tests__/Sidebar.test.tsx`

**Step 1: Write Sidebar test**

```typescript
// frontend/src/components/layout/__tests__/Sidebar.test.tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Sidebar } from "../Sidebar";

describe("Sidebar", () => {
  test("renders navigation links", () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Signals")).toBeInTheDocument();
    expect(screen.getByText("Trades")).toBeInTheDocument();
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/layout/__tests__/Sidebar.test.tsx`
Expected: FAIL — module not found.

**Step 3: Implement sidebar state store**

```typescript
// frontend/src/lib/sidebar.ts
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface SidebarStore {
  collapsed: boolean;
  toggle: () => void;
}

export const useSidebar = create<SidebarStore>()(
  persist(
    (set) => ({
      collapsed: false,
      toggle: () => set((s) => ({ collapsed: !s.collapsed })),
    }),
    { name: "sf-sidebar" }
  )
);
```

**Step 4: Implement Sidebar**

`frontend/src/components/layout/Sidebar.tsx`:
- Left sidebar, fixed height `h-screen`, `w-60` expanded / `w-16` collapsed
- Transition on width change (`transition-all duration-200`)
- Logo at top: "SF" when collapsed, "SignalForge" when expanded
- Navigation items with lucide-react icons:
  - Dashboard (`LayoutDashboard`, `/`)
  - Signals (`Zap`, `/signals`)
  - Trades (`ArrowUpDown`, `/trades`)
  - Backtest Lab (`FlaskConical`, `/backtest`)
  - Journal (`BookOpen`, `/journal`)
  - Strategy (`Settings`, `/config`)
  - API Keys (`Key`, `/keys`)
- Active item highlighted with `bg-(--color-accent-soft) text-(--color-accent)`
- Uses `NavLink` from react-router-dom for active state
- Collapse toggle button at bottom (lucide `PanelLeftClose` / `PanelLeftOpen`)
- Colors: `bg-(--color-bg-surface)` background, `border-r border-(--color-border)`

**Step 5: Implement Topbar**

`frontend/src/components/layout/Topbar.tsx`:
- Sticky top bar, `h-14`
- Left: breadcrumb showing current page name (derive from route)
- Right: theme toggle (Sun/Moon icons), user avatar/logout button
- Background: `bg-(--color-bg-surface) border-b border-(--color-border)`

**Step 6: Implement AppLayout**

```typescript
// frontend/src/components/layout/AppLayout.tsx
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { useSidebar } from "@/lib/sidebar";

export function AppLayout() {
  const collapsed = useSidebar((s) => s.collapsed);
  return (
    <div className="flex h-screen overflow-hidden bg-(--color-bg-base)">
      <Sidebar />
      <div className={`flex flex-1 flex-col ${collapsed ? "ml-16" : "ml-60"} transition-all duration-200`}>
        <Topbar />
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
```

**Step 7: Wire layout into App.tsx**

Update `App.tsx` to render `<AppLayout>` as the layout element for protected routes:
```tsx
<Route element={<ProtectedRoute />}>
  <Route element={<AppLayout />}>
    <Route index element={<DashboardPage />} />
    {/* ... other routes */}
  </Route>
</Route>
```

**Step 8: Run tests**

Run: `cd frontend && npx vitest run`
Expected: All tests pass.

**Step 9: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

**Step 10: Commit**

```bash
git add frontend/src/components/layout/ frontend/src/lib/sidebar.ts frontend/src/App.tsx
git commit -m "feat(frontend): add layout shell with collapsible sidebar and topbar"
```

---

## Task 5: Dashboard Page

**Files:**
- Create: `frontend/src/pages/Dashboard.tsx`
- Create: `frontend/src/components/dashboard/PriceChart.tsx`
- Create: `frontend/src/components/dashboard/StatsCards.tsx`
- Create: `frontend/src/components/dashboard/SignalFeed.tsx`
- Create: `frontend/src/components/dashboard/PositionsTable.tsx`
- Create: `frontend/src/components/dashboard/RegimeWidget.tsx`
- Create: `frontend/src/hooks/useSignals.ts`
- Create: `frontend/src/hooks/usePositions.ts`
- Create: `frontend/src/hooks/useTrades.ts`
- Test: `frontend/src/components/dashboard/__tests__/StatsCards.test.tsx`

**Step 1: Write StatsCards test**

```typescript
// frontend/src/components/dashboard/__tests__/StatsCards.test.tsx
import { render, screen } from "@testing-library/react";
import { StatsCards } from "../StatsCards";

describe("StatsCards", () => {
  test("renders stat cards with values", () => {
    render(
      <StatsCards
        stats={{
          total_trades: 42,
          win_rate: 65.5,
          profit_factor: 1.85,
          total_pnl: 2340.50,
          avg_pnl: 55.73,
          best_trade: 450.00,
          worst_trade: -180.00,
        }}
      />
    );
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("65.5%")).toBeInTheDocument();
    expect(screen.getByText("1.85")).toBeInTheDocument();
  });

  test("renders loading state", () => {
    render(<StatsCards stats={null} />);
    // Should show skeleton/placeholder
    expect(screen.getAllByTestId("stat-skeleton")).toHaveLength(4);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/dashboard/__tests__/StatsCards.test.tsx`
Expected: FAIL — module not found.

**Step 3: Create TanStack Query hooks**

```typescript
// frontend/src/hooks/useSignals.ts
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface SignalListResponse {
  signals: Signal[];
  total: number;
  limit: number;
  offset: number;
}

export interface Signal {
  id: string;
  symbol: string;
  timeframe: string;
  direction: string;
  entry_price: number;
  stop_loss: number;
  take_profit_1: number;
  take_profit_2: number | null;
  confluence_score: number;
  regime: string;
  triggers: Record<string, unknown> | null;
  status: string;
  created_at: string;
}

export function useSignals(limit = 20, offset = 0) {
  return useQuery({
    queryKey: ["signals", limit, offset],
    queryFn: () => api.get<SignalListResponse>(`/signals?limit=${limit}&offset=${offset}`),
  });
}

export function useSignal(id: string) {
  return useQuery({
    queryKey: ["signal", id],
    queryFn: () => api.get<Signal>(`/signals/${id}`),
    enabled: !!id,
  });
}
```

```typescript
// frontend/src/hooks/useTrades.ts
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface Trade {
  id: string;
  signal_id: string | null;
  user_id: string;
  symbol: string;
  direction: string;
  entry_price: number;
  exit_price: number | null;
  position_size: number;
  stop_loss: number;
  take_profit: number;
  pnl: number | null;
  pnl_pct: number | null;
  risk_reward: number | null;
  confluence_score: number;
  entry_time: string | null;
  exit_time: string | null;
  exit_reason: string | null;
  broker_order_id: string | null;
  metadata_json: Record<string, unknown> | null;
  created_at: string;
}

export interface TradeStats {
  total_trades: number;
  win_rate: number;
  profit_factor: number;
  total_pnl: number;
  avg_pnl: number;
  best_trade: number;
  worst_trade: number;
}

export function useTrades(limit = 20, offset = 0) {
  return useQuery({
    queryKey: ["trades", limit, offset],
    queryFn: () =>
      api.get<{ trades: Trade[]; total: number }>(`/trades?limit=${limit}&offset=${offset}`),
  });
}

export function useTradeStats() {
  return useQuery({
    queryKey: ["trades", "stats"],
    queryFn: () => api.get<TradeStats>("/trades/stats"),
  });
}
```

```typescript
// frontend/src/hooks/usePositions.ts
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface Position {
  id: string;
  symbol: string;
  direction: string;
  entry_price: number;
  quantity: number;
  stop_loss: number;
  take_profit: number;
  is_open: boolean;
  pnl: number | null;
  exit_price: number | null;
  exit_reason: string | null;
  order_id: string;
}

export interface AccountState {
  equity: number;
  daily_pnl: number;
  open_positions: number;
  max_positions: number;
}

export function usePositions() {
  return useQuery({
    queryKey: ["positions"],
    queryFn: () => api.get<Position[]>("/positions"),
  });
}

export function useAccountState() {
  return useQuery({
    queryKey: ["positions", "account"],
    queryFn: () => api.get<AccountState>("/positions/account"),
  });
}
```

**Step 4: Implement StatsCards**

`frontend/src/components/dashboard/StatsCards.tsx`:
- 4-card grid: Total P&L, Win Rate, Profit Factor, Total Trades
- Each card: icon, label, value (JetBrains Mono for numbers)
- P&L colored positive/negative
- Skeleton loading state with `data-testid="stat-skeleton"`
- Background: `bg-(--color-bg-surface)`, rounded-xl, border

**Step 5: Implement PriceChart**

`frontend/src/components/dashboard/PriceChart.tsx`:
- Uses `lightweight-charts` `createChart()` + `addCandlestickSeries()`
- Chart container fills available width/height
- Dark/light theme via chart options matching CSS tokens
- Symbol selector dropdown in header
- Timeframe tabs: 1m, 5m, 15m, 1h, 4h, 1D
- Currently renders with empty data (real data comes from data ingestion service)
- Candlestick colors: positive (green), negative (red)

**Step 6: Implement SignalFeed**

`frontend/src/components/dashboard/SignalFeed.tsx`:
- Compact vertical list of latest 10 signals
- Each: symbol badge, direction arrow (up green / down red), confluence score bar, time ago
- Clicking navigates to `/signals/{id}` detail

**Step 7: Implement PositionsTable**

`frontend/src/components/dashboard/PositionsTable.tsx`:
- Compact table of open positions
- Columns: Symbol, Direction, Entry, Current, P&L, SL, TP
- P&L colored positive/negative
- Empty state: "No open positions"

**Step 8: Implement RegimeWidget**

`frontend/src/components/dashboard/RegimeWidget.tsx`:
- Small card showing current market regime
- Label (TRENDING, RANGING, etc.) with colored badge
- Mini ADX sparkline or numeric value

**Step 9: Assemble Dashboard page**

`frontend/src/pages/Dashboard.tsx`:
- Grid layout:
  - Top row: 4 StatsCards (responsive grid: 1→2→4 cols)
  - Main area: PriceChart (left, 65%) + sidebar column (right, 35%)
  - Sidebar: RegimeWidget + SignalFeed (stacked)
  - Bottom: PositionsTable (full width)

**Step 10: Run tests**

Run: `cd frontend && npx vitest run`
Expected: All tests pass.

**Step 11: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

**Step 12: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx frontend/src/components/dashboard/ \
  frontend/src/hooks/
git commit -m "feat(frontend): add Dashboard page with chart, stats, signals, and positions"
```

---

## Task 6: Signals Page

**Files:**
- Create: `frontend/src/pages/Signals.tsx`
- Create: `frontend/src/components/ui/DataTable.tsx` (reusable sortable table)
- Create: `frontend/src/components/ui/Badge.tsx` (status/direction badges)
- Create: `frontend/src/components/ui/Pagination.tsx`
- Test: `frontend/src/pages/__tests__/Signals.test.tsx`

**Step 1: Write Signals page test**

```typescript
// frontend/src/pages/__tests__/Signals.test.tsx
import { render, screen } from "@testing-library/react";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { SignalsPage } from "../Signals";

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter>{children}</MemoryRouter>
  </QueryClientProvider>
);

describe("SignalsPage", () => {
  test("renders page heading", () => {
    render(<SignalsPage />, { wrapper });
    expect(screen.getByText("Signals")).toBeInTheDocument();
  });

  test("renders generate signal button", () => {
    render(<SignalsPage />, { wrapper });
    expect(screen.getByRole("button", { name: /generate/i })).toBeInTheDocument();
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/pages/__tests__/Signals.test.tsx`
Expected: FAIL.

**Step 3: Build reusable UI components**

`frontend/src/components/ui/DataTable.tsx`:
- Generic `<DataTable<T>>` component
- Props: `data: T[]`, `columns: Column<T>[]`, `onRowClick?`, `loading?: boolean`
- Column definition: `{ key, header, render?, sortable?, align? }`
- Sortable column headers (click to toggle asc/desc)
- Loading skeleton rows
- Empty state message
- Styled with theme tokens: `bg-(--color-bg-surface)`, striped rows via `odd:bg-(--color-bg-elevated)/30`

`frontend/src/components/ui/Badge.tsx`:
- Variants: `success`, `danger`, `warning`, `info`, `neutral`
- Compact rounded pill
- Used for signal direction, trade status, regime type

`frontend/src/components/ui/Pagination.tsx`:
- Previous/Next buttons + page info
- Props: `total`, `limit`, `offset`, `onChange(offset)`

**Step 4: Implement Signals page**

`frontend/src/pages/Signals.tsx`:
- Header: "Signals" title + "Generate Signal" button (calls `POST /api/signals/generate`)
- Filters row: symbol dropdown, timeframe dropdown, direction (long/short/all)
- DataTable with columns: Time, Symbol, Direction (badge), Entry, SL, TP1, Confluence (progress bar), Regime (badge), Status (badge)
- Confluence score: colored progress bar (0-30 red, 30-60 yellow, 60-100 green)
- Pagination at bottom
- Click row → navigates to signal detail (inline expandable or modal showing full breakdown)

**Step 5: Run tests**

Run: `cd frontend && npx vitest run`
Expected: All tests pass.

**Step 6: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

**Step 7: Commit**

```bash
git add frontend/src/pages/Signals.tsx frontend/src/components/ui/ \
  frontend/src/pages/__tests__/Signals.test.tsx
git commit -m "feat(frontend): add Signals page with data table and filters"
```

---

## Task 7: Trades Page

**Files:**
- Create: `frontend/src/pages/Trades.tsx`
- Test: `frontend/src/pages/__tests__/Trades.test.tsx`

**Step 1: Write Trades page test**

```typescript
// frontend/src/pages/__tests__/Trades.test.tsx
import { render, screen } from "@testing-library/react";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { TradesPage } from "../Trades";

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter>{children}</MemoryRouter>
  </QueryClientProvider>
);

describe("TradesPage", () => {
  test("renders page heading and stats section", () => {
    render(<TradesPage />, { wrapper });
    expect(screen.getByText("Trade History")).toBeInTheDocument();
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/pages/__tests__/Trades.test.tsx`
Expected: FAIL.

**Step 3: Implement Trades page**

`frontend/src/pages/Trades.tsx`:
- Stats summary row at top: Total Trades, Win Rate, Profit Factor, Total P&L (from `useTradeStats()`)
- DataTable with columns: Time, Symbol, Direction (badge), Entry, Exit, Size, P&L ($, colored), P&L (%, colored), R:R, Confluence, Exit Reason
- P&L values: positive green, negative red, JetBrains Mono font
- Filter bar: symbol, direction, date range
- Pagination
- Click row → detail view with metadata_json display

**Step 4: Run tests**

Run: `cd frontend && npx vitest run`
Expected: All tests pass.

**Step 5: Commit**

```bash
git add frontend/src/pages/Trades.tsx frontend/src/pages/__tests__/Trades.test.tsx
git commit -m "feat(frontend): add Trades page with stats summary and history table"
```

---

## Task 8: Backtest Lab Page

**Files:**
- Create: `frontend/src/pages/Backtest.tsx`
- Create: `frontend/src/components/backtest/BacktestForm.tsx`
- Create: `frontend/src/components/backtest/BacktestResults.tsx`
- Create: `frontend/src/hooks/useBacktest.ts`
- Test: `frontend/src/pages/__tests__/Backtest.test.tsx`

**Step 1: Write Backtest page test**

```typescript
// frontend/src/pages/__tests__/Backtest.test.tsx
import { render, screen } from "@testing-library/react";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { BacktestPage } from "../Backtest";

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter>{children}</MemoryRouter>
  </QueryClientProvider>
);

describe("BacktestPage", () => {
  test("renders configuration form", () => {
    render(<BacktestPage />, { wrapper });
    expect(screen.getByText("Backtest Lab")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /run backtest/i })).toBeInTheDocument();
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/pages/__tests__/Backtest.test.tsx`
Expected: FAIL.

**Step 3: Implement backtest hook**

```typescript
// frontend/src/hooks/useBacktest.ts
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface BacktestRequest {
  symbol: string;
  timeframe: string;
  days: number;
  params?: Record<string, unknown>;
}

export function useRunBacktest() {
  return useMutation({
    mutationFn: (req: BacktestRequest) => api.post<Record<string, unknown>>("/backtests", req),
  });
}
```

**Step 4: Implement BacktestForm**

`frontend/src/components/backtest/BacktestForm.tsx`:
- Symbol dropdown (9 supported symbols from `/api/market/symbols`)
- Timeframe selector (1m, 5m, 15m, 1h, 4h, 1D tabs)
- Days slider (1-365, default 30)
- Optional params section: min_confluence (0-100), risk_per_trade (0.01-0.05)
- "Run Backtest" button with loading spinner
- Uses `useRunBacktest()` mutation

**Step 5: Implement BacktestResults**

`frontend/src/components/backtest/BacktestResults.tsx`:
- Display after successful backtest run
- Metrics grid: Total Return, Win Rate, Profit Factor, Max Drawdown, Total Trades, Sharpe Ratio
- Equity curve chart using lightweight-charts (line series)
- Trade list table: date, direction, entry, exit, P&L

**Step 6: Assemble Backtest page**

`frontend/src/pages/Backtest.tsx`:
- Left panel: BacktestForm (sticky, 30% width)
- Right panel: BacktestResults (70% width, scrollable)
- Results show after form submission
- Loading state with spinner during backtest execution

**Step 7: Run tests**

Run: `cd frontend && npx vitest run`
Expected: All tests pass.

**Step 8: Commit**

```bash
git add frontend/src/pages/Backtest.tsx frontend/src/components/backtest/ \
  frontend/src/hooks/useBacktest.ts frontend/src/pages/__tests__/Backtest.test.tsx
git commit -m "feat(frontend): add Backtest Lab page with form and results display"
```

---

## Task 9: Strategy Config + API Keys Pages

**Files:**
- Create: `frontend/src/pages/StrategyConfig.tsx`
- Create: `frontend/src/pages/ApiKeys.tsx`
- Create: `frontend/src/hooks/useStrategies.ts`
- Test: `frontend/src/pages/__tests__/StrategyConfig.test.tsx`

**Step 1: Write StrategyConfig test**

```typescript
// frontend/src/pages/__tests__/StrategyConfig.test.tsx
import { render, screen } from "@testing-library/react";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { StrategyConfigPage } from "../StrategyConfig";

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter>{children}</MemoryRouter>
  </QueryClientProvider>
);

describe("StrategyConfigPage", () => {
  test("renders page heading and create button", () => {
    render(<StrategyConfigPage />, { wrapper });
    expect(screen.getByText("Strategies")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /new strategy/i })).toBeInTheDocument();
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/pages/__tests__/StrategyConfig.test.tsx`
Expected: FAIL.

**Step 3: Implement strategies hook**

```typescript
// frontend/src/hooks/useStrategies.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface Strategy {
  id: string;
  user_id: string;
  name: string;
  is_active: boolean;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export function useStrategies() {
  return useQuery({
    queryKey: ["strategies"],
    queryFn: () => api.get<{ strategies: Strategy[]; total: number }>("/strategies"),
  });
}

export function useCreateStrategy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string; config?: Record<string, unknown> }) =>
      api.post<Strategy>("/strategies", data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
}

export function useUpdateStrategy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string; name?: string; config?: Record<string, unknown> }) =>
      api.put<Strategy>(`/strategies/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
}

export function useToggleStrategy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post<Strategy>(`/strategies/${id}/activate`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
}

export function useDeleteStrategy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/strategies/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
}
```

**Step 4: Implement StrategyConfig page**

`frontend/src/pages/StrategyConfig.tsx`:
- Header: "Strategies" + "New Strategy" button
- Strategy list as cards (not table): name, active badge (green/gray toggle), created date
- Each card has: Edit, Activate/Deactivate, Delete buttons
- Create/Edit modal (or inline drawer): name input, JSON config editor
- Config editor: Layer parameter controls (min_confluence, risk_per_trade, atr_sl_mult, etc.)
- Active strategy highlighted with accent border

**Step 5: Implement ApiKeys page**

`frontend/src/pages/ApiKeys.tsx`:
- Header: "API Keys & Broker Connections"
- Cards for each broker: Alpaca, Binance
- Each card: API Key (masked), API Secret (masked), Paper/Live toggle
- Add new connection form
- Status indicator (connected/disconnected)
- Note: Backend broker_connections CRUD not yet built — show UI with local state for now, note "Backend integration coming in Phase 5"

**Step 6: Run tests**

Run: `cd frontend && npx vitest run`
Expected: All tests pass.

**Step 7: Commit**

```bash
git add frontend/src/pages/StrategyConfig.tsx frontend/src/pages/ApiKeys.tsx \
  frontend/src/hooks/useStrategies.ts frontend/src/pages/__tests__/StrategyConfig.test.tsx
git commit -m "feat(frontend): add Strategy Config and API Keys pages"
```

---

## Task 10: Trade Journal Page (Placeholder)

**Files:**
- Create: `frontend/src/pages/Journal.tsx`

**Step 1: Implement Journal placeholder**

`frontend/src/pages/Journal.tsx`:
- Header: "Trade Journal"
- Description: "AI-assisted trade review and pattern recognition"
- Placeholder card: "Journal features coming in Phase 5 — Claude Haiku AI analysis, pattern recognition, and trade annotations"
- Visual: Empty state illustration with BookOpen icon
- This is a stub — Phase 5 will add the AI-powered journal

**Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

**Step 3: Commit**

```bash
git add frontend/src/pages/Journal.tsx
git commit -m "feat(frontend): add Trade Journal placeholder page"
```

---

## Task 11: WebSocket Integration

**Files:**
- Create: `frontend/src/lib/ws.ts`
- Create: `frontend/src/hooks/useWebSocket.ts`
- Test: `frontend/src/lib/__tests__/ws.test.ts`

**Step 1: Write WebSocket manager test**

```typescript
// frontend/src/lib/__tests__/ws.test.ts
import { WebSocketManager } from "../ws";

describe("WebSocketManager", () => {
  test("constructs correct URL for signals channel", () => {
    const mgr = new WebSocketManager("ws://localhost:8000");
    expect(mgr.getUrl("signals")).toBe("ws://localhost:8000/ws/signals");
  });

  test("constructs correct URL for prices channel", () => {
    const mgr = new WebSocketManager("ws://localhost:8000");
    expect(mgr.getUrl("prices")).toBe("ws://localhost:8000/ws/prices");
  });

  test("appends token as query param for signals", () => {
    const mgr = new WebSocketManager("ws://localhost:8000");
    expect(mgr.getUrl("signals", "tok123")).toBe("ws://localhost:8000/ws/signals?token=tok123");
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/lib/__tests__/ws.test.ts`
Expected: FAIL.

**Step 3: Implement WebSocket manager**

```typescript
// frontend/src/lib/ws.ts
type MessageHandler = (data: unknown) => void;

export class WebSocketManager {
  private baseUrl: string;
  private connections = new Map<string, WebSocket>();
  private handlers = new Map<string, Set<MessageHandler>>();
  private reconnectTimers = new Map<string, ReturnType<typeof setTimeout>>();

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl || (import.meta.env.VITE_WS_URL || "ws://localhost:8000");
  }

  getUrl(channel: string, token?: string): string {
    const url = `${this.baseUrl}/ws/${channel}`;
    return token ? `${url}?token=${token}` : url;
  }

  connect(channel: string, token?: string): void {
    if (this.connections.has(channel)) return;
    const url = this.getUrl(channel, token);
    const ws = new WebSocket(url);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handlers.get(channel)?.forEach((fn) => fn(data));
    };

    ws.onclose = () => {
      this.connections.delete(channel);
      // Reconnect after 3s
      const timer = setTimeout(() => this.connect(channel, token), 3000);
      this.reconnectTimers.set(channel, timer);
    };

    this.connections.set(channel, ws);
  }

  subscribe(channel: string, handler: MessageHandler): () => void {
    if (!this.handlers.has(channel)) {
      this.handlers.set(channel, new Set());
    }
    this.handlers.get(channel)!.add(handler);
    return () => this.handlers.get(channel)?.delete(handler);
  }

  disconnect(channel: string): void {
    this.connections.get(channel)?.close();
    this.connections.delete(channel);
    const timer = this.reconnectTimers.get(channel);
    if (timer) clearTimeout(timer);
    this.reconnectTimers.delete(channel);
  }

  disconnectAll(): void {
    for (const channel of this.connections.keys()) {
      this.disconnect(channel);
    }
  }
}

export const wsManager = new WebSocketManager();
```

**Step 4: Implement useWebSocket hook**

```typescript
// frontend/src/hooks/useWebSocket.ts
import { useEffect, useRef, useCallback, useState } from "react";
import { wsManager } from "@/lib/ws";
import { useAuth } from "@/lib/auth";

export function useSignalStream(onSignal: (signal: unknown) => void) {
  const token = useAuth((s) => s.accessToken);
  const callbackRef = useRef(onSignal);
  callbackRef.current = onSignal;

  useEffect(() => {
    if (!token) return;
    wsManager.connect("signals", token);
    const unsub = wsManager.subscribe("signals", (data) => callbackRef.current(data));
    return () => {
      unsub();
      wsManager.disconnect("signals");
    };
  }, [token]);
}

export function usePriceStream() {
  const [prices, setPrices] = useState<Record<string, number>>({});

  useEffect(() => {
    wsManager.connect("prices");
    const unsub = wsManager.subscribe("prices", (data: unknown) => {
      const { symbol, price } = data as { symbol: string; price: number };
      setPrices((prev) => ({ ...prev, [symbol]: price }));
    });
    return () => {
      unsub();
      wsManager.disconnect("prices");
    };
  }, []);

  return prices;
}
```

**Step 5: Wire WebSocket into Dashboard**

Update `frontend/src/pages/Dashboard.tsx`:
- Use `useSignalStream` to append new signals to the SignalFeed in real time
- Use `usePriceStream` to update PositionsTable current prices

**Step 6: Run tests**

Run: `cd frontend && npx vitest run`
Expected: All tests pass.

**Step 7: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

**Step 8: Commit**

```bash
git add frontend/src/lib/ws.ts frontend/src/hooks/useWebSocket.ts \
  frontend/src/lib/__tests__/ws.test.ts frontend/src/pages/Dashboard.tsx
git commit -m "feat(frontend): add WebSocket manager and real-time signal/price streams"
```

---

## Task 12: Final Integration + Lint + Build

**Files:**
- Modify: `frontend/src/App.tsx` — Wire all routes to actual page components

**Step 1: Ensure all routes are wired**

Verify `App.tsx` imports and routes all 7 pages:
- `/` → `DashboardPage`
- `/signals` → `SignalsPage`
- `/trades` → `TradesPage`
- `/backtest` → `BacktestPage`
- `/journal` → `JournalPage`
- `/config` → `StrategyConfigPage`
- `/keys` → `ApiKeysPage`
- `/login` → `LoginPage`
- `/register` → `RegisterPage`

**Step 2: Run all tests**

Run: `cd frontend && npx vitest run`
Expected: All tests pass.

**Step 3: Run lint**

Run: `cd frontend && npm run lint`
Expected: 0 errors, 0 warnings.

**Step 4: Fix any lint issues**

Run: `cd frontend && npx eslint . --fix` if there are auto-fixable issues.

**Step 5: Production build**

Run: `cd frontend && npm run build`
Expected: Build succeeds, check bundle size.

**Step 6: Final commit**

```bash
git add -A frontend/
git commit -m "feat(frontend): Phase 4 complete — all pages wired, lint clean, build passing"
```

---

## Agent Team Structure

### Wave 1: Scaffold (sequential dependency for Wave 2)
- **@frontend-scaffold** (Tasks 1-4): Install deps, API client, auth store, router, auth pages, layout shell

### Wave 2: Pages (parallel, all depend on Wave 1 completion)
- **@page-builder-a** (Tasks 5-6): Dashboard page + Signals page
- **@page-builder-b** (Tasks 7-9): Trades page + Backtest Lab + Strategy Config + API Keys + Journal placeholder

### Wave 3: Integration (depends on Wave 2)
- **@ws-integrator** (Tasks 11-12): WebSocket manager, real-time hooks, final integration + lint + build

### Merge Order
1. Merge @frontend-scaffold → main
2. Merge @page-builder-a and @page-builder-b → main (resolve any conflicts in App.tsx routes)
3. Merge @ws-integrator → main
4. Final verification: all tests pass, lint clean, build succeeds
