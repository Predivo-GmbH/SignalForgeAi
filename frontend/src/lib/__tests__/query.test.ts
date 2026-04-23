import { queryClient } from "../query";

describe("queryClient", () => {
  it("is defined", () => {
    expect(queryClient).toBeDefined();
  });

  it("has default staleTime of 30s", () => {
    const defaults = queryClient.getDefaultOptions();
    expect(defaults.queries?.staleTime).toBe(30_000);
  });

  it("has retry set to 1", () => {
    const defaults = queryClient.getDefaultOptions();
    expect(defaults.queries?.retry).toBe(1);
  });

  it("has refetchOnWindowFocus disabled", () => {
    const defaults = queryClient.getDefaultOptions();
    expect(defaults.queries?.refetchOnWindowFocus).toBe(false);
  });
});
