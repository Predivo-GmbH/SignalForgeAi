import { useEffect } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  Activity,
  Briefcase,
  ArrowUpDown,
  BarChart2,
  Shield,
  Sparkles,
  Target,
  Settings,
  PanelLeftClose,
  PanelLeftOpen,
  X,
} from "lucide-react";
import { useSidebar } from "@/lib/sidebar";
import { cn } from "@/lib/cn";

const navItems = [
  { to: "/", icon: Briefcase, label: "Portfolio" },
  { to: "/advisor", icon: Sparkles, label: "AI Advisor" },
  { to: "/strategies", icon: Target, label: "Strategies" },
  { to: "/trades", icon: ArrowUpDown, label: "Trades" },
  { to: "/analytics", icon: BarChart2, label: "Analytics" },
  { to: "/risk", icon: Shield, label: "Risk" },
  { to: "/engine", icon: Activity, label: "Engine" },
  { to: "/settings", icon: Settings, label: "Settings" },
] as const;

export function Sidebar() {
  const collapsed = useSidebar((s) => s.collapsed);
  const mobileOpen = useSidebar((s) => s.mobileOpen);
  const toggle = useSidebar((s) => s.toggle);
  const setMobileOpen = useSidebar((s) => s.setMobileOpen);
  const location = useLocation();

  // Close mobile sidebar on navigation
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname, setMobileOpen]);

  return (
    <>
      {/* Mobile backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside
        className={cn(
          "fixed left-0 top-0 z-50 flex h-screen flex-col border-r border-(--color-border) bg-(--color-bg-surface) transition-all duration-200",
          // Mobile: off-screen by default, slide in when open
          mobileOpen ? "translate-x-0" : "-translate-x-full",
          "lg:translate-x-0", // Desktop: always visible
          collapsed ? "w-60 lg:w-16" : "w-60",
        )}
      >
        {/* Logo */}
        <div className="flex h-14 items-center justify-between border-b border-(--color-border) px-4">
          <div className="flex items-center">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-(--color-accent) text-sm font-bold text-white">
              SF
            </div>
            <span className={cn("ml-3 text-sm font-semibold text-(--color-text-primary)", collapsed && "lg:hidden")}>
              SignalForge
            </span>
          </div>
          {/* Mobile close button */}
          <button
            onClick={() => setMobileOpen(false)}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-(--color-text-secondary) hover:bg-(--color-bg-elevated) lg:hidden"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-2 py-3">
          <ul className="space-y-1">
            {navItems.map(({ to, icon: Icon, label }) => (
              <li key={to}>
                <NavLink
                  to={to}
                  end={to === "/"}
                  className={({ isActive }) => {
                    const active =
                      isActive ||
                      (to === "/strategies" &&
                        location.pathname.startsWith("/strategies/"));
                    return cn(
                      "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                      collapsed && "lg:justify-center lg:px-0",
                      active
                        ? "bg-(--color-accent-soft) text-(--color-accent)"
                        : "text-(--color-text-secondary) hover:bg-(--color-bg-elevated) hover:text-(--color-text-primary)"
                    );
                  }}
                  title={collapsed ? label : undefined}
                >
                  <Icon className="h-5 w-5 shrink-0" />
                  <span className={cn(collapsed && "lg:hidden")}>{label}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        {/* Collapse toggle — desktop only */}
        <div className="border-t border-(--color-border) p-2 hidden lg:block">
          <button
            onClick={toggle}
            className={cn(
              "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-(--color-text-secondary) transition-colors hover:bg-(--color-bg-elevated) hover:text-(--color-text-primary)",
              collapsed && "justify-center px-0"
            )}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? (
              <PanelLeftOpen className="h-5 w-5 shrink-0" />
            ) : (
              <>
                <PanelLeftClose className="h-5 w-5 shrink-0" />
                <span>Collapse</span>
              </>
            )}
          </button>
        </div>
      </aside>
    </>
  );
}
