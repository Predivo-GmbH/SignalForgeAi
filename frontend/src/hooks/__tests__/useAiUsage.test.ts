describe("useAiUsage hooks", () => {
  it("exports useAiUsage", async () => {
    const mod = await import("../useAiUsage");
    expect(mod.useAiUsage).toBeDefined();
    expect(typeof mod.useAiUsage).toBe("function");
  });

  it("exports useUpdateCredit", async () => {
    const mod = await import("../useAiUsage");
    expect(mod.useUpdateCredit).toBeDefined();
    expect(typeof mod.useUpdateCredit).toBe("function");
  });
});
