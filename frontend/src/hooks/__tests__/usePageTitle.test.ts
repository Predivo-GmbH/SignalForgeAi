import { renderHook } from "@testing-library/react";
import { usePageTitle } from "../usePageTitle";

describe("usePageTitle", () => {
  const originalTitle = document.title;

  afterEach(() => {
    document.title = originalTitle;
  });

  it("sets document title with suffix", () => {
    renderHook(() => usePageTitle("Dashboard"));
    expect(document.title).toBe("Dashboard | SignalForgeAI");
  });

  it("sets only app name for null title", () => {
    renderHook(() => usePageTitle(null));
    expect(document.title).toBe("SignalForgeAI");
  });

  it("updates title when changed", () => {
    const { rerender } = renderHook(({ title }) => usePageTitle(title), {
      initialProps: { title: "Trades" as string | null },
    });
    expect(document.title).toBe("Trades | SignalForgeAI");

    rerender({ title: "Analytics" });
    expect(document.title).toBe("Analytics | SignalForgeAI");
  });
});
