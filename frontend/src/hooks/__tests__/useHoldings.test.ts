describe("useHoldings hooks", () => {
  it("exports useHoldings", async () => {
    const mod = await import("../useHoldings");
    expect(mod.useHoldings).toBeDefined();
    expect(typeof mod.useHoldings).toBe("function");
  });

  it("exports useAddHolding", async () => {
    const mod = await import("../useHoldings");
    expect(mod.useAddHolding).toBeDefined();
  });

  it("exports useUpdateHolding", async () => {
    const mod = await import("../useHoldings");
    expect(mod.useUpdateHolding).toBeDefined();
  });

  it("exports useDeleteHolding", async () => {
    const mod = await import("../useHoldings");
    expect(mod.useDeleteHolding).toBeDefined();
  });

  it("exports useBulkImportHoldings", async () => {
    const mod = await import("../useHoldings");
    expect(mod.useBulkImportHoldings).toBeDefined();
  });
});
