describe("useStrategies hooks", () => {
  it("exports useStrategies", async () => {
    const mod = await import("../useStrategies");
    expect(mod.useStrategies).toBeDefined();
    expect(typeof mod.useStrategies).toBe("function");
  });

  it("exports useStrategy", async () => {
    const mod = await import("../useStrategies");
    expect(mod.useStrategy).toBeDefined();
  });

  it("exports useCreateStrategy", async () => {
    const mod = await import("../useStrategies");
    expect(mod.useCreateStrategy).toBeDefined();
  });

  it("exports useUpdateStrategy", async () => {
    const mod = await import("../useStrategies");
    expect(mod.useUpdateStrategy).toBeDefined();
  });

  it("exports useToggleStrategy", async () => {
    const mod = await import("../useStrategies");
    expect(mod.useToggleStrategy).toBeDefined();
  });

  it("exports useDeleteStrategy", async () => {
    const mod = await import("../useStrategies");
    expect(mod.useDeleteStrategy).toBeDefined();
  });

  it("exports useStrategyPresets", async () => {
    const mod = await import("../useStrategies");
    expect(mod.useStrategyPresets).toBeDefined();
  });

  it("exports useExchangeAvailability", async () => {
    const mod = await import("../useStrategies");
    expect(mod.useExchangeAvailability).toBeDefined();
  });
});
