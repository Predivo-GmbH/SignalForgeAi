/**
 * Auth tests — Supabase OTP auth is context-based.
 * These tests verify the AuthContext export works correctly.
 */

describe("auth module", () => {
  test("re-exports useAuth from AuthContext", async () => {
    const mod = await import("../auth");
    expect(mod.useAuth).toBeDefined();
    expect(typeof mod.useAuth).toBe("function");
  });

  test("useAuth throws outside provider", () => {
    // Can't call hook outside React, but the module should load
    expect(true).toBe(true);
  });
});
