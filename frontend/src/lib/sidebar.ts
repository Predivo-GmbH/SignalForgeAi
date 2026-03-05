import { create } from "zustand";
import { persist } from "zustand/middleware";

interface SidebarStore {
  collapsed: boolean;
  mobileOpen: boolean;
  toggle: () => void;
  setMobileOpen: (open: boolean) => void;
}

export const useSidebar = create<SidebarStore>()(
  persist(
    (set) => ({
      collapsed: false,
      mobileOpen: false,
      toggle: () => set((s) => ({ collapsed: !s.collapsed })),
      setMobileOpen: (open: boolean) => set({ mobileOpen: open }),
    }),
    { name: "sf-sidebar", partialize: (s) => ({ collapsed: s.collapsed }) }
  )
);
