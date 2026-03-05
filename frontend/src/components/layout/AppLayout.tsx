import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { useSidebar } from "@/lib/sidebar";
import { cn } from "@/lib/cn";

export function AppLayout() {
  const collapsed = useSidebar((s) => s.collapsed);

  return (
    <div className="flex h-screen overflow-hidden bg-(--color-bg-base)">
      <Sidebar />
      <div
        className={cn(
          "flex flex-1 flex-col transition-all duration-200",
          // No margin on mobile (sidebar is overlay), margin on desktop
          collapsed ? "lg:ml-16" : "lg:ml-60",
        )}
      >
        <Topbar />
        <main className="flex-1 overflow-auto" role="main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
