import { test, expect } from "@playwright/test";

const BASE = "http://localhost:5173";

test.describe("Feature user journeys", () => {
  test("F-001: Login page renders sign-in form", async ({ page }) => {
    await page.goto(`${BASE}/login`);
    await page.waitForLoadState("networkidle");

    // Should show branding
    await expect(page.locator("text=SignalForgeAI").first()).toBeVisible();
    // Should have email input
    await expect(page.locator('input[type="email"]')).toBeVisible();
  });

  test("F-001: Signup page renders registration form", async ({ page }) => {
    await page.goto(`${BASE}/signup`);
    await page.waitForLoadState("networkidle");

    await expect(page.locator("text=SignalForgeAI").first()).toBeVisible();
    await expect(page.locator('input[type="email"]')).toBeVisible();
  });

  test("F-001: Login page links to signup and forgot password", async ({ page }) => {
    await page.goto(`${BASE}/login`);
    await page.waitForLoadState("networkidle");

    const signupLink = page.locator('a[href="/signup"]');
    await expect(signupLink).toBeVisible();

    const forgotLink = page.locator('a[href="/forgot-password"]');
    await expect(forgotLink).toBeVisible();
  });

  test("F-001: Signup page links back to login", async ({ page }) => {
    await page.goto(`${BASE}/signup`);
    await page.waitForLoadState("networkidle");

    const loginLink = page.locator('a[href="/login"]');
    await expect(loginLink).toBeVisible();
  });

  test("F-001: Forgot password page renders email input", async ({ page }) => {
    await page.goto(`${BASE}/forgot-password`);
    await page.waitForLoadState("networkidle");

    await expect(page.locator('input[type="email"]')).toBeVisible();
  });

  test("F-015: Dark theme is applied by default", async ({ page }) => {
    await page.goto(`${BASE}/login`);
    await page.waitForLoadState("networkidle");

    const hasDarkClass = await page.evaluate(() =>
      document.documentElement.classList.contains("dark"),
    );
    expect(hasDarkClass).toBe(true);
  });

  test("Login page is responsive — no horizontal overflow", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(`${BASE}/login`);
    await page.waitForLoadState("networkidle");

    const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
    const viewportWidth = await page.evaluate(() => window.innerWidth);
    expect(bodyWidth).toBeLessThanOrEqual(viewportWidth);
  });
});
