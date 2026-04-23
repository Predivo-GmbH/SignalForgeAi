import { test, expect } from "@playwright/test";

const BASE = "http://localhost:5173";

test.describe("Smoke — All routes load without JS errors", () => {
  // Public routes (no auth required — should render or redirect)
  const publicRoutes = [
    "/login",
    "/signup",
    "/forgot-password",
    "/reset-password",
  ];

  for (const route of publicRoutes) {
    test(`${route} loads without 500 errors`, async ({ page }) => {
      const response = await page.goto(`${BASE}${route}`);
      expect(response?.status()).toBeLessThan(500);
    });
  }

  test("Login page has no console errors", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });
    await page.goto(`${BASE}/login`);
    await page.waitForLoadState("networkidle");
    // Filter out expected Supabase auth errors
    const realErrors = errors.filter(
      (e) =>
        !e.includes("AuthSessionMissing") &&
        !e.includes("Auth session missing") &&
        !e.includes("Failed to fetch") &&
        !e.includes("supabase"),
    );
    expect(realErrors).toHaveLength(0);
  });

  test("Signup page has no console errors", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });
    await page.goto(`${BASE}/signup`);
    await page.waitForLoadState("networkidle");
    const realErrors = errors.filter(
      (e) =>
        !e.includes("AuthSessionMissing") &&
        !e.includes("Auth session missing") &&
        !e.includes("Failed to fetch") &&
        !e.includes("supabase"),
    );
    expect(realErrors).toHaveLength(0);
  });

  test("Static assets load correctly", async ({ page }) => {
    const failedRequests: string[] = [];
    page.on("response", (response) => {
      if (response.status() >= 400 && !response.url().includes("supabase")) {
        failedRequests.push(`${response.status()} ${response.url()}`);
      }
    });
    await page.goto(`${BASE}/login`);
    await page.waitForLoadState("networkidle");
    expect(failedRequests).toHaveLength(0);
  });

  // Protected routes redirect to login when unauthenticated
  const protectedRoutes = [
    "/",
    "/advisor",
    "/strategies",
    "/trades",
    "/analytics",
    "/risk",
    "/engine",
    "/settings",
    "/backtest",
  ];

  for (const route of protectedRoutes) {
    test(`${route} redirects to login when unauthenticated`, async ({ page }) => {
      await page.goto(`${BASE}${route}`);
      await page.waitForLoadState("networkidle");
      // Should redirect to /login (or show password gate first)
      const url = page.url();
      expect(url).toMatch(/\/(login|$)/);
    });
  }
});
