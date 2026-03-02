import { Component, type ReactNode } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { PasswordGate } from "./components/PasswordGate";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AppLayout } from "./components/layout/AppLayout";
import { LoginPage } from "./pages/Login";
import { RegisterPage } from "./pages/Register";
import { DashboardPage } from "./pages/Dashboard";
import { TradesPage } from "./pages/Trades";
import { AnalyticsPage } from "./pages/Analytics";
import { AdvisorPage } from "./pages/Advisor";
import { StrategiesPage } from "./pages/Strategies";
import { StrategyDetailPage } from "./pages/StrategyDetail";
import { BacktestPage } from "./pages/Backtest";
import { SettingsPage } from "./pages/Settings";
import { queryClient } from "./lib/query";

/* ---------- Error Boundary ---------- */

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    console.error("[ErrorBoundary] Uncaught error:", error, info.componentStack);
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-(--color-bg-base) p-6">
          <div className="max-w-md w-full bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-8 text-center space-y-4">
            <div className="w-12 h-12 rounded-full bg-(--color-negative)/10 flex items-center justify-center mx-auto">
              <svg
                className="w-6 h-6 text-(--color-negative)"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <h2 className="text-lg font-semibold text-(--color-text-primary)">
              Something went wrong
            </h2>
            <p className="text-sm text-(--color-text-secondary)">
              An unexpected error occurred. Please try again.
            </p>
            {this.state.error && (
              <p className="text-xs text-(--color-text-secondary)/60 font-mono break-all">
                {this.state.error.message}
              </p>
            )}
            <button
              onClick={this.handleRetry}
              className="inline-flex items-center gap-2 bg-(--color-accent) hover:bg-(--color-accent)/90 text-white font-semibold py-2 px-5 rounded-lg text-sm transition-colors"
            >
              Try Again
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/* ---------- App ---------- */

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <PasswordGate>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route element={<ProtectedRoute />}>
              <Route element={<AppLayout />}>
                <Route index element={<DashboardPage />} />
                <Route path="advisor" element={<AdvisorPage />} />
                <Route path="strategies" element={<StrategiesPage />} />
                <Route path="strategies/:id" element={<StrategyDetailPage />} />
                <Route path="backtest" element={<BacktestPage />} />
                <Route path="trades" element={<TradesPage />} />
                <Route path="analytics" element={<AnalyticsPage />} />
                <Route path="settings" element={<SettingsPage />} />
                {/* Redirects for old routes */}
                <Route path="config" element={<Navigate to="/strategies" replace />} />
                <Route path="signals" element={<Navigate to="/strategies" replace />} />
                <Route path="journal" element={<Navigate to="/trades" replace />} />
                <Route path="keys" element={<Navigate to="/settings" replace />} />
                <Route path="guide" element={<Navigate to="/" replace />} />
              </Route>
            </Route>
          </Routes>
        </PasswordGate>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
