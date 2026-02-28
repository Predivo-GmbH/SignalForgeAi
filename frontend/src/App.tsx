import { useEffect } from "react";
import { Routes, Route } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { PasswordGate } from "./components/PasswordGate";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AppLayout } from "./components/layout/AppLayout";
import { LoginPage } from "./pages/Login";
import { RegisterPage } from "./pages/Register";
import { useTheme } from "./lib/theme";
import { queryClient } from "./lib/query";

function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-(--color-text-primary) mb-2">
          {title}
        </h1>
        <p className="text-(--color-text-secondary)">Coming soon...</p>
      </div>
    </div>
  );
}

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
              <Route index element={<PlaceholderPage title="Dashboard" />} />
              <Route
                path="signals"
                element={<PlaceholderPage title="Signals" />}
              />
              <Route
                path="trades"
                element={<PlaceholderPage title="Trades" />}
              />
              <Route
                path="backtest"
                element={<PlaceholderPage title="Backtest Lab" />}
              />
              <Route
                path="journal"
                element={<PlaceholderPage title="Trade Journal" />}
              />
              <Route
                path="config"
                element={<PlaceholderPage title="Strategy Config" />}
              />
              <Route
                path="keys"
                element={<PlaceholderPage title="API Keys" />}
              />
            </Route>
          </Route>
        </Routes>
      </PasswordGate>
    </QueryClientProvider>
  );
}

export default App;
