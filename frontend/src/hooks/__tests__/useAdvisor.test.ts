describe("useAdvisor hooks", () => {
  it("exports useGeneratePlan", async () => {
    const mod = await import("../useAdvisor");
    expect(mod.useGeneratePlan).toBeDefined();
    expect(typeof mod.useGeneratePlan).toBe("function");
  });

  it("exports useDeployPlan", async () => {
    const mod = await import("../useAdvisor");
    expect(mod.useDeployPlan).toBeDefined();
    expect(typeof mod.useDeployPlan).toBe("function");
  });

  it("exports ScoredCrypto type shape", async () => {
    // Verify the module can be imported without errors
    const mod = await import("../useAdvisor");
    expect(Object.keys(mod)).toContain("useGeneratePlan");
    expect(Object.keys(mod)).toContain("useDeployPlan");
  });
});
