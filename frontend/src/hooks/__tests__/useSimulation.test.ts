describe("useSimulation hooks", () => {
  it("exports useSimulation", async () => {
    const mod = await import("../useSimulation");
    expect(mod.useSimulation).toBeDefined();
    expect(typeof mod.useSimulation).toBe("function");
  });

  it("exports useLatestSimulation", async () => {
    const mod = await import("../useSimulation");
    expect(mod.useLatestSimulation).toBeDefined();
  });

  it("exports useStartSimulation", async () => {
    const mod = await import("../useSimulation");
    expect(mod.useStartSimulation).toBeDefined();
  });

  it("exports useStopSimulation", async () => {
    const mod = await import("../useSimulation");
    expect(mod.useStopSimulation).toBeDefined();
  });

  it("exports useCombinedPortfolio", async () => {
    const mod = await import("../useSimulation");
    expect(mod.useCombinedPortfolio).toBeDefined();
  });

  it("exports useBHPortfolio (deprecated)", async () => {
    const mod = await import("../useSimulation");
    expect(mod.useBHPortfolio).toBeDefined();
  });

  it("exports usePaperPortfolio (deprecated)", async () => {
    const mod = await import("../useSimulation");
    expect(mod.usePaperPortfolio).toBeDefined();
  });

  it("exports useUpdateReserve", async () => {
    const mod = await import("../useSimulation");
    expect(mod.useUpdateReserve).toBeDefined();
  });
});
