import { useLocation } from "react-router-dom";
import { Sun, Moon, LogOut } from "lucide-react";
import { useTheme } from "@/lib/theme";
import { useAuth } from "@/lib/auth";

const pageTitles: Record<string, string> = {
  "/": "Dashboard",
  "/signals": "Signals",
  "/trades": "Trades",
  "/backtest": "Backtest Lab",
  "/journal": "Trade Journal",
  "/config": "Strategy Config",
  "/keys": "API Keys",
};

export function Topbar() {
  const location = useLocation();
  const { theme, toggle: toggleTheme } = useTheme();
  const logout = useAuth((s) => s.logout);

  const pageTitle = pageTitles[location.pathname] || "SignalForge";

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-(--color-border) bg-(--color-bg-surface) px-6">
      {/* Page title */}
      <h2 className="text-sm font-semibold text-(--color-text-primary)">
        {pageTitle}
      </h2>

      {/* Actions */}
      <div className="flex items-center gap-1">
        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          className="flex h-9 w-9 items-center justify-center rounded-lg text-(--color-text-secondary) transition-colors hover:bg-(--color-bg-elevated) hover:text-(--color-text-primary)"
          title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        >
          {theme === "dark" ? (
            <Sun className="h-4.5 w-4.5" />
          ) : (
            <Moon className="h-4.5 w-4.5" />
          )}
        </button>

        {/* Logout */}
        <button
          onClick={logout}
          className="flex h-9 w-9 items-center justify-center rounded-lg text-(--color-text-secondary) transition-colors hover:bg-(--color-bg-elevated) hover:text-(--color-negative)"
          title="Sign out"
        >
          <LogOut className="h-4.5 w-4.5" />
        </button>
      </div>
    </header>
  );
}
