import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const BASE = "http://localhost:5173";

test.describe("Accessibility — WCAG 2.1 AA on public routes", () => {
  const publicRoutes = [
    { path: "/login", name: "Login" },
    { path: "/signup", name: "Signup" },
    { path: "/forgot-password", name: "Forgot Password" },
    { path: "/reset-password", name: "Reset Password" },
  ];

  for (const { path, name } of publicRoutes) {
    test(`${name} page passes axe-core WCAG 2.1 AA`, async ({ page }) => {
      await page.goto(`${BASE}${path}`);
      await page.waitForLoadState("networkidle");

      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
        .analyze();

      const violations = results.violations.filter(
        (v) => v.impact === "critical" || v.impact === "serious",
      );

      if (violations.length > 0) {
        console.log(
          `A11y violations on ${name}:`,
          JSON.stringify(
            violations.map((v) => ({
              id: v.id,
              impact: v.impact,
              description: v.description,
              nodes: v.nodes.length,
            })),
            null,
            2,
          ),
        );
      }

      expect(violations).toHaveLength(0);
    });
  }
});
