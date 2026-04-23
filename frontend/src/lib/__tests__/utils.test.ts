import { cn } from "../cn";
import { friendlyAuthError } from "../utils";
import { TRIGGER_LABELS } from "../constants";
import { CRYPTO_LIST, CRYPTO_NAME_MAP } from "../cryptoSymbols";

describe("cn (class merge)", () => {
  it("merges simple classes", () => {
    expect(cn("foo", "bar")).toBe("foo bar");
  });

  it("handles conditional classes", () => {
    expect(cn("base", false && "hidden", "visible")).toBe("base visible");
  });

  it("handles undefined values", () => {
    expect(cn("base", undefined, "end")).toBe("base end");
  });

  it("deduplicates tailwind classes", () => {
    const result = cn("p-4", "p-2");
    expect(result).toBe("p-2");
  });
});

describe("friendlyAuthError", () => {
  it("returns friendly message for rate limit", () => {
    const result = friendlyAuthError(new Error("email rate limit exceeded"), "fallback");
    expect(result).toContain("Too many emails");
  });

  it("returns friendly message for invalid credentials", () => {
    const result = friendlyAuthError(new Error("Invalid login credentials"), "fallback");
    expect(result).toContain("Incorrect email or password");
  });

  it("returns friendly message for expired token", () => {
    const result = friendlyAuthError(new Error("Token has expired"), "fallback");
    expect(result).toContain("expired");
  });

  it("returns friendly message for network error", () => {
    const result = friendlyAuthError(new Error("network error"), "fallback");
    expect(result).toContain("Connection error");
  });

  it("returns error message for unknown Error", () => {
    const result = friendlyAuthError(new Error("something weird"), "fallback");
    expect(result).toBe("something weird");
  });

  it("returns fallback for non-Error", () => {
    const result = friendlyAuthError("string error", "fallback");
    expect(result).toBe("fallback");
  });

  it("returns friendly message for email not confirmed", () => {
    const result = friendlyAuthError(new Error("email not confirmed"), "fallback");
    expect(result).toContain("not been verified");
  });

  it("returns friendly message for user not found", () => {
    const result = friendlyAuthError(new Error("user not found"), "fallback");
    expect(result).toContain("No account found");
  });

  it("returns friendly message for invalid OTP", () => {
    const result = friendlyAuthError(new Error("invalid otp token"), "fallback");
    expect(result).toContain("Invalid verification code");
  });
});

describe("TRIGGER_LABELS", () => {
  it("has entries", () => {
    expect(Object.keys(TRIGGER_LABELS).length).toBeGreaterThan(0);
  });

  it("contains macd_crossover label", () => {
    expect(TRIGGER_LABELS.macd_crossover).toBe("MACD crossover");
  });

  it("contains rsi_midline_cross label", () => {
    expect(TRIGGER_LABELS.rsi_midline_cross).toBe("RSI midline cross");
  });
});

describe("CRYPTO_LIST", () => {
  it("is populated with entries", () => {
    expect(CRYPTO_LIST.length).toBeGreaterThan(100);
  });

  it("includes Bitcoin", () => {
    const btc = CRYPTO_LIST.find((c) => c.symbol === "BTC");
    expect(btc).toBeDefined();
    expect(btc?.name).toBe("Bitcoin");
  });

  it("includes Ethereum", () => {
    const eth = CRYPTO_LIST.find((c) => c.symbol === "ETH");
    expect(eth).toBeDefined();
    expect(eth?.name).toBe("Ethereum");
  });
});

describe("CRYPTO_NAME_MAP", () => {
  it("maps BTC to Bitcoin", () => {
    expect(CRYPTO_NAME_MAP.BTC).toBe("Bitcoin");
  });

  it("maps ETH to Ethereum", () => {
    expect(CRYPTO_NAME_MAP.ETH).toBe("Ethereum");
  });

  it("maps SOL to Solana", () => {
    expect(CRYPTO_NAME_MAP.SOL).toBe("Solana");
  });
});
