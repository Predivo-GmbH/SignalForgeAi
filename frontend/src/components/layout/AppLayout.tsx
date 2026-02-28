import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { useSidebar } from "@/lib/sidebar";

export function AppLayout() {
  const collapsed = useSidebar((s) => s.collapsed);

  return (
    <div className="flex h-screen overflow-hidden bg-(--color-bg-base)">
      <Sidebar />
      <div
        className={`flex flex-1 flex-col transition-all duration-200 ${collapsed ? "ml-16" : "ml-60"}`}
      >
        <Topbar />
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
