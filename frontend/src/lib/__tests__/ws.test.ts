import { WebSocketManager } from "../ws";

describe("WebSocketManager", () => {
  test("constructs correct URL for signals channel", () => {
    const mgr = new WebSocketManager("ws://localhost:8000");
    expect(mgr.getUrl("signals")).toBe("ws://localhost:8000/ws/signals");
  });

  test("constructs correct URL for prices channel", () => {
    const mgr = new WebSocketManager("ws://localhost:8000");
    expect(mgr.getUrl("prices")).toBe("ws://localhost:8000/ws/prices");
  });

  test("appends token as query param for signals", () => {
    const mgr = new WebSocketManager("ws://localhost:8000");
    expect(mgr.getUrl("signals", "tok123")).toBe(
      "ws://localhost:8000/ws/signals?token=tok123",
    );
  });
});
