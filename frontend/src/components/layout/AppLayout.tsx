import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { RouteAnnouncer } from "@/components/shared/RouteAnnouncer";
import { useSidebar } from "@/lib/sidebar";
import { cn } from "@/lib/cn";

export function AppLayout() {
  const collapsed = useSidebar((s) => s.collapsed);

  return (
    <div className="flex h-screen overflow-hidden bg-(--color-bg-base)">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-(--color-accent) focus:text-white focus:px-4 focus:py-2 focus:rounded-md focus:m-2"
      >
        Skip to content
      </a>
      <RouteAnnouncer />
      <Sidebar />
      <div
        className={cn(
          "flex flex-1 flex-col min-w-0 transition-all duration-200",
          // No margin on mobile (sidebar is overlay), margin on desktop
          collapsed ? "lg:ml-16" : "lg:ml-60",
        )}
      >
        <Topbar />
        <main id="main-content" className="flex-1 min-w-0 overflow-auto" role="main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
