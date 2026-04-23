import { pnlColor, formatPrice, fmtUsd, formatPnl, formatPnlPercent, formatDate, formatTime } from "../format";

describe("pnlColor", () => {
  it("returns secondary for null", () => {
    expect(pnlColor(null)).toContain("secondary");
  });

  it("returns secondary for undefined", () => {
    expect(pnlColor(undefined)).toContain("secondary");
  });

  it("returns positive for positive values", () => {
    expect(pnlColor(100)).toContain("positive");
  });

  it("returns negative for negative values", () => {
    expect(pnlColor(-50)).toContain("negative");
  });

  it("returns secondary for zero", () => {
    expect(pnlColor(0)).toContain("secondary");
  });
});

describe("formatPrice", () => {
  it("formats large prices with 2 decimals", () => {
    expect(formatPrice(50000)).toBe("$50000.00");
  });

  it("formats medium prices with 4 decimals", () => {
    expect(formatPrice(1.5)).toBe("$1.5000");
  });

  it("formats small prices with 6 decimals", () => {
    expect(formatPrice(0.0005)).toBe("$0.000500");
  });
});

describe("fmtUsd", () => {
  it("returns -- for null", () => {
    expect(fmtUsd(null)).toBe("--");
  });

  it("returns -- for undefined", () => {
    expect(fmtUsd(undefined)).toBe("--");
  });

  it("formats positive values with $ prefix", () => {
    const result = fmtUsd(1234.56);
    expect(result).toContain("$");
    expect(result).toContain("1,234.56");
  });
});

describe("formatPnl", () => {
  it("returns -- for null", () => {
    expect(formatPnl(null)).toBe("--");
  });

  it("formats positive pnl with +$ prefix", () => {
    expect(formatPnl(500)).toBe("+$500.00");
  });

  it("formats negative pnl with -$ prefix", () => {
    expect(formatPnl(-250)).toBe("-$250.00");
  });

  it("formats zero pnl with +$ prefix", () => {
    expect(formatPnl(0)).toBe("+$0.00");
  });
});

describe("formatPnlPercent", () => {
  it("returns -- for null", () => {
    expect(formatPnlPercent(null)).toBe("--");
  });

  it("formats positive percent with + prefix", () => {
    expect(formatPnlPercent(5.5)).toBe("+5.50%");
  });

  it("formats negative percent", () => {
    expect(formatPnlPercent(-3.14)).toBe("-3.14%");
  });
});

describe("formatDate", () => {
  it("formats ISO date string", () => {
    const result = formatDate("2026-01-15T10:30:00Z");
    expect(result).toContain("Jan");
    expect(result).toContain("15");
    expect(result).toContain("2026");
  });
});

describe("formatTime", () => {
  it("returns -- for null", () => {
    expect(formatTime(null)).toBe("--");
  });

  it("returns -- for undefined", () => {
    expect(formatTime(undefined)).toBe("--");
  });

  it("formats date with time", () => {
    const result = formatTime("2026-01-15T14:30:00Z");
    expect(result).toContain("Jan");
    expect(result).toContain("15");
  });
});
