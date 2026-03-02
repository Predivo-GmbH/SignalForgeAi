import { useEffect } from "react";
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
import { useTheme } from "./lib/theme";
import { queryClient } from "./lib/query";

function App() {
  const { theme } = useTheme();

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  return (
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
  );
}

export default App;
