import { useTheme } from "@/lib/theme";

describe("useTheme store", () => {
  beforeEach(() => {
    useTheme.setState({ theme: "dark" });
  });

  it("defaults to dark theme", () => {
    expect(useTheme.getState().theme).toBe("dark");
  });

  it("toggles from dark to light", () => {
    useTheme.getState().toggle();
    expect(useTheme.getState().theme).toBe("light");
  });

  it("toggles back to dark", () => {
    useTheme.getState().toggle(); // dark -> light
    useTheme.getState().toggle(); // light -> dark
    expect(useTheme.getState().theme).toBe("dark");
  });

  it("set method changes theme directly", () => {
    useTheme.getState().set("light");
    expect(useTheme.getState().theme).toBe("light");
  });
});
