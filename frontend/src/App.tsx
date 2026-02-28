import { useEffect } from "react";
import { Routes, Route } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { PasswordGate } from "./components/PasswordGate";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AppLayout } from "./components/layout/AppLayout";
import { LoginPage } from "./pages/Login";
import { RegisterPage } from "./pages/Register";
import { DashboardPage } from "./pages/Dashboard";
import { SignalsPage } from "./pages/Signals";
import { TradesPage } from "./pages/Trades";
import { BacktestPage } from "./pages/Backtest";
import { JournalPage } from "./pages/Journal";
import { StrategyConfigPage } from "./pages/StrategyConfig";
import { ApiKeysPage } from "./pages/ApiKeys";
import { AnalyticsPage } from "./pages/Analytics";
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
              <Route path="signals" element={<SignalsPage />} />
              <Route path="trades" element={<TradesPage />} />
              <Route path="backtest" element={<BacktestPage />} />
              <Route path="journal" element={<JournalPage />} />
              <Route path="analytics" element={<AnalyticsPage />} />
              <Route path="config" element={<StrategyConfigPage />} />
              <Route path="keys" element={<ApiKeysPage />} />
            </Route>
          </Route>
        </Routes>
      </PasswordGate>
    </QueryClientProvider>
  );
}

export default App;
