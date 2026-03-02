import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Zap,
  ArrowUpDown,
  FlaskConical,
  BookOpen,
  BarChart2,
  Settings,
  Key,
  Sparkles,
  HelpCircle,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { useSidebar } from "@/lib/sidebar";
import { cn } from "@/lib/cn";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/advisor", icon: Sparkles, label: "AI Advisor" },
  { to: "/signals", icon: Zap, label: "Signals" },
  { to: "/trades", icon: ArrowUpDown, label: "Trades" },
  { to: "/backtest", icon: FlaskConical, label: "Backtest Lab" },
  { to: "/journal", icon: BookOpen, label: "Journal" },
  { to: "/analytics", icon: BarChart2, label: "Analytics" },
  { to: "/config", icon: Settings, label: "Strategies" },
  { to: "/keys", icon: Key, label: "API Keys" },
  { to: "/guide", icon: HelpCircle, label: "User Guide" },
] as const;

export function Sidebar() {
  const collapsed = useSidebar((s) => s.collapsed);
  const toggle = useSidebar((s) => s.toggle);

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-30 flex h-screen flex-col border-r border-(--color-border) bg-(--color-bg-surface) transition-all duration-200",
        collapsed ? "w-16" : "w-60"
      )}
    >
      {/* Logo */}
      <div className="flex h-14 items-center border-b border-(--color-border) px-4">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-(--color-accent) text-sm font-bold text-white">
          SF
        </div>
        {!collapsed && (
          <span className="ml-3 text-sm font-semibold text-(--color-text-primary)">
            SignalForge
          </span>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-2 py-3">
        <ul className="space-y-1">
          {navItems.map(({ to, icon: Icon, label }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                    collapsed && "justify-center px-0",
                    isActive
                      ? "bg-(--color-accent-soft) text-(--color-accent)"
                      : "text-(--color-text-secondary) hover:bg-(--color-bg-elevated) hover:text-(--color-text-primary)"
                  )
                }
                title={collapsed ? label : undefined}
              >
                <Icon className="h-5 w-5 shrink-0" />
                {!collapsed && <span>{label}</span>}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* Collapse toggle */}
      <div className="border-t border-(--color-border) p-2">
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
  );
}
