import { ApiError } from "../api";

describe("ApiError", () => {
  it("creates error with status, message, and code", () => {
    const err = new ApiError(404, "Not found", "NOT_FOUND");
    expect(err.status).toBe(404);
    expect(err.message).toBe("Not found");
    expect(err.code).toBe("NOT_FOUND");
    expect(err.name).toBe("ApiError");
  });

  it("defaults code to UNKNOWN", () => {
    const err = new ApiError(500, "Server error");
    expect(err.code).toBe("UNKNOWN");
  });

  it("is an instance of Error", () => {
    const err = new ApiError(400, "Bad request");
    expect(err).toBeInstanceOf(Error);
  });
});

describe("api module exports", () => {
  it("exports invokeFunction", async () => {
    const mod = await import("../api");
    expect(mod.invokeFunction).toBeDefined();
    expect(typeof mod.invokeFunction).toBe("function");
  });

  it("exports queryTable", async () => {
    const mod = await import("../api");
    expect(mod.queryTable).toBeDefined();
    expect(typeof mod.queryTable).toBe("function");
  });

  it("exports insertRow", async () => {
    const mod = await import("../api");
    expect(mod.insertRow).toBeDefined();
  });

  it("exports updateRow", async () => {
    const mod = await import("../api");
    expect(mod.updateRow).toBeDefined();
  });

  it("exports deleteRow", async () => {
    const mod = await import("../api");
    expect(mod.deleteRow).toBeDefined();
  });

  it("exports legacy api object", async () => {
    const mod = await import("../api");
    expect(mod.api).toBeDefined();
    expect(mod.api.get).toBe(mod.queryTable);
    expect(mod.api.invoke).toBe(mod.invokeFunction);
  });
});
