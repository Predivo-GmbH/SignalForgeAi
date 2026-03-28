import { useState } from "react";
import { useLocation } from "react-router-dom";
import { Sun, Moon, LogOut, HelpCircle, Menu } from "lucide-react";
import { useTheme } from "@/lib/theme";
import { useAuth } from "@/contexts/AuthContext";
import { useSidebar } from "@/lib/sidebar";
import { HelpDrawer } from "./HelpDrawer";

const pageTitles: Record<string, string> = {
  "/": "Dashboard",
  "/advisor": "AI Advisor",
  "/strategies": "Strategies",
  "/backtest": "Strategy Validation",
  "/trades": "Trades",
  "/analytics": "Analytics",
  "/risk": "Risk Management",
  "/engine": "Signal Engine",
  "/settings": "Settings",
};

export function Topbar() {
  const location = useLocation();
  const { theme, toggle: toggleTheme } = useTheme();
  const { signOut } = useAuth();
  const setMobileOpen = useSidebar((s) => s.setMobileOpen);
  const [helpOpen, setHelpOpen] = useState(false);

  const pageTitle =
    pageTitles[location.pathname] ||
    (location.pathname.startsWith("/strategies/") ? "Strategy Detail" : "SignalForgeAI");

  return (
    <>
      <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-(--color-border) bg-(--color-bg-surface) px-4 sm:px-6">
        {/* Left: hamburger (mobile) + page title */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setMobileOpen(true)}
            className="flex h-11 w-11 min-h-[44px] min-w-[44px] items-center justify-center rounded-lg text-(--color-text-secondary) transition-colors hover:bg-(--color-bg-elevated) hover:text-(--color-text-primary) lg:hidden"
            title="Open menu"
            aria-label="Open menu"
            aria-expanded={false}
          >
            <Menu className="h-5 w-5" aria-hidden="true" />
          </button>
          <span className="text-sm font-semibold text-(--color-text-primary)" aria-hidden="true">
            {pageTitle}
          </span>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1">
          {/* Help */}
          <button
            onClick={() => setHelpOpen(true)}
            className="flex h-11 w-11 min-h-[44px] min-w-[44px] items-center justify-center rounded-lg text-(--color-text-secondary) transition-colors hover:bg-(--color-bg-elevated) hover:text-(--color-text-primary)"
            title="User Guide"
            aria-label="Open help"
          >
            <HelpCircle className="h-4.5 w-4.5" aria-hidden="true" />
          </button>

          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            className="flex h-11 w-11 min-h-[44px] min-w-[44px] items-center justify-center rounded-lg text-(--color-text-secondary) transition-colors hover:bg-(--color-bg-elevated) hover:text-(--color-text-primary)"
            title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            aria-label={theme === "dark" ? "Toggle theme to light mode" : "Toggle theme to dark mode"}
          >
            {theme === "dark" ? (
              <Sun className="h-4.5 w-4.5" aria-hidden="true" />
            ) : (
              <Moon className="h-4.5 w-4.5" aria-hidden="true" />
            )}
          </button>

          {/* Logout */}
          <button
            onClick={() => signOut()}
            className="flex h-11 w-11 min-h-[44px] min-w-[44px] items-center justify-center rounded-lg text-(--color-text-secondary) transition-colors hover:bg-(--color-bg-elevated) hover:text-(--color-negative)"
            title="Sign out"
            aria-label="Sign out"
          >
            <LogOut className="h-4.5 w-4.5" aria-hidden="true" />
          </button>
        </div>
      </header>

      <HelpDrawer open={helpOpen} onClose={() => setHelpOpen(false)} />
    </>
  );
}
