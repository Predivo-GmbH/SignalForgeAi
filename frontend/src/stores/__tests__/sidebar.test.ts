import { useSidebar } from "@/lib/sidebar";

describe("useSidebar store", () => {
  beforeEach(() => {
    useSidebar.setState({ collapsed: false, mobileOpen: false });
  });

  it("defaults to expanded", () => {
    expect(useSidebar.getState().collapsed).toBe(false);
  });

  it("defaults to mobile closed", () => {
    expect(useSidebar.getState().mobileOpen).toBe(false);
  });

  it("toggle collapses sidebar", () => {
    useSidebar.getState().toggle();
    expect(useSidebar.getState().collapsed).toBe(true);
  });

  it("toggle expands when already collapsed", () => {
    useSidebar.getState().toggle(); // expand -> collapse
    useSidebar.getState().toggle(); // collapse -> expand
    expect(useSidebar.getState().collapsed).toBe(false);
  });

  it("setMobileOpen opens mobile menu", () => {
    useSidebar.getState().setMobileOpen(true);
    expect(useSidebar.getState().mobileOpen).toBe(true);
  });

  it("setMobileOpen closes mobile menu", () => {
    useSidebar.getState().setMobileOpen(true);
    useSidebar.getState().setMobileOpen(false);
    expect(useSidebar.getState().mobileOpen).toBe(false);
  });
});
