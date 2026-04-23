describe("useSystemStatus hooks", () => {
  it("exports useSystemStatus", async () => {
    const mod = await import("../useSystemStatus");
    expect(mod.useSystemStatus).toBeDefined();
    expect(typeof mod.useSystemStatus).toBe("function");
  });

  it("exports useRestartWorker", async () => {
    const mod = await import("../useSystemStatus");
    expect(mod.useRestartWorker).toBeDefined();
    expect(typeof mod.useRestartWorker).toBe("function");
  });
});
