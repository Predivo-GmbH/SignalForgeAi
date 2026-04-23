import { getPasswordScore } from "../password-utils";

describe("getPasswordScore", () => {
  it("returns 0 for empty string", () => {
    expect(getPasswordScore("")).toBe(0);
  });

  it("returns 1 for short lowercase only", () => {
    expect(getPasswordScore("abc")).toBe(1);
  });

  it("returns 2 for lowercase + uppercase", () => {
    expect(getPasswordScore("aBc")).toBe(2);
  });

  it("returns 3 for lowercase + uppercase + number", () => {
    expect(getPasswordScore("aBc1")).toBe(3);
  });

  it("returns 4 for 8+ chars with uppercase, lowercase, number", () => {
    expect(getPasswordScore("Abcdefg1")).toBe(4);
  });

  it("returns 5 for full strength password", () => {
    expect(getPasswordScore("Abcdefg1!")).toBe(5);
  });

  it("returns correct score for only special characters", () => {
    expect(getPasswordScore("!!!!!!!!")).toBe(2); // 8+ chars + special
  });
});
