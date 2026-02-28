// Vitest globals:true — do NOT import from 'vitest'

describe("useBrokerConnections", () => {
  it("exports query hook", async () => {
    const mod = await import("@/hooks/useBrokerConnections");
    expect(mod.useBrokerConnections).toBeDefined();
    expect(typeof mod.useBrokerConnections).toBe("function");
  });

  it("exports connect mutation hook", async () => {
    const mod = await import("@/hooks/useBrokerConnections");
    expect(mod.useConnectBroker).toBeDefined();
    expect(typeof mod.useConnectBroker).toBe("function");
  });

  it("exports disconnect mutation hook", async () => {
    const mod = await import("@/hooks/useBrokerConnections");
    expect(mod.useDisconnectBroker).toBeDefined();
    expect(typeof mod.useDisconnectBroker).toBe("function");
  });

  it("exports BrokerConnection interface type via runtime shape", async () => {
    // Verify module exports are structurally sound
    const mod = await import("@/hooks/useBrokerConnections");
    const exports = Object.keys(mod);
    expect(exports).toContain("useBrokerConnections");
    expect(exports).toContain("useConnectBroker");
    expect(exports).toContain("useDisconnectBroker");
  });
});
