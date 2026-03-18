/**
 * WebSocket/Realtime tests — now uses Supabase Realtime.
 */
import { disconnectAll } from "../ws";

describe("Realtime module", () => {
  test("exports subscribeTable and subscribeBroadcast", async () => {
    const mod = await import("../ws");
    expect(mod.subscribeTable).toBeDefined();
    expect(mod.subscribeBroadcast).toBeDefined();
    expect(mod.disconnectAll).toBeDefined();
  });

  test("disconnectAll runs without error", () => {
    expect(() => disconnectAll()).not.toThrow();
  });
});
