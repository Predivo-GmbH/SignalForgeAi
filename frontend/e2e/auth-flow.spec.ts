import { test, expect } from '@playwright/test';

const BASE = 'https://signalforgeai.predivo.ch';

test.describe('Auth Pages — Visual & Functional', () => {
  test.use({ viewport: { width: 1920, height: 1080 } });

  test('Login page renders correctly', async ({ page }) => {
    await page.goto(`${BASE}/login`);
    await page.waitForLoadState('networkidle');

    // Should show SignalForgeAI branding
    await expect(page.locator('text=SignalForgeAI').first()).toBeVisible();
    // Should show sign-in heading
    await expect(page.locator('text=/sign in/i').first()).toBeVisible();
    // Should have email input
    await expect(page.locator('input[type="email"]')).toBeVisible();
    // Screenshot
    await page.screenshot({ path: 'e2e/screenshots/login.png', fullPage: true });
  });

  test('Signup page renders correctly', async ({ page }) => {
    await page.goto(`${BASE}/signup`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('text=SignalForgeAI').first()).toBeVisible();
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await page.screenshot({ path: 'e2e/screenshots/signup.png', fullPage: true });
  });

  test('Forgot password page renders correctly', async ({ page }) => {
    await page.goto(`${BASE}/forgot-password`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('input[type="email"]')).toBeVisible();
    await page.screenshot({ path: 'e2e/screenshots/forgot-password.png', fullPage: true });
  });

  test('Login page has no console errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    await page.goto(`${BASE}/login`);
    await page.waitForLoadState('networkidle');
    // Filter out expected Supabase auth errors (no session)
    const realErrors = errors.filter(e =>
      !e.includes('AuthSessionMissing') &&
      !e.includes('Auth session missing') &&
      !e.includes('Failed to fetch')
    );
    expect(realErrors).toHaveLength(0);
  });

  test('Login page links to signup and forgot password', async ({ page }) => {
    await page.goto(`${BASE}/login`);
    await page.waitForLoadState('networkidle');

    // Should have signup link
    const signupLink = page.locator('a[href="/signup"]');
    await expect(signupLink).toBeVisible();

    // Should have forgot password link
    const forgotLink = page.locator('a[href="/forgot-password"]');
    await expect(forgotLink).toBeVisible();
  });

  test('Signup page links back to login', async ({ page }) => {
    await page.goto(`${BASE}/signup`);
    await page.waitForLoadState('networkidle');

    const loginLink = page.locator('a[href="/login"]');
    await expect(loginLink).toBeVisible();
  });

  test('Unauthenticated user redirected to login from dashboard', async ({ page }) => {
    await page.goto(`${BASE}/`);
    await page.waitForLoadState('networkidle');
    // Should redirect to /login
    await expect(page).toHaveURL(/\/login/);
  });

  test('Login page is responsive — no horizontal overflow', async ({ page }) => {
    // Test at mobile width
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(`${BASE}/login`);
    await page.waitForLoadState('networkidle');

    const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
    const viewportWidth = await page.evaluate(() => window.innerWidth);
    expect(bodyWidth).toBeLessThanOrEqual(viewportWidth);

    await page.screenshot({ path: 'e2e/screenshots/login-mobile.png', fullPage: true });
  });

  test('All auth pages load without 500 errors', async ({ page }) => {
    const pages = ['/login', '/signup', '/forgot-password', '/reset-password'];
    for (const path of pages) {
      const response = await page.goto(`${BASE}${path}`);
      expect(response?.status()).toBeLessThan(500);
    }
  });

  test('Static assets load correctly (favicon, CSS, JS)', async ({ page }) => {
    const failedRequests: string[] = [];
    page.on('response', response => {
      if (response.status() >= 400 && !response.url().includes('supabase')) {
        failedRequests.push(`${response.status()} ${response.url()}`);
      }
    });

    await page.goto(`${BASE}/login`);
    await page.waitForLoadState('networkidle');

    expect(failedRequests).toHaveLength(0);
  });

  test('Dark theme is applied by default', async ({ page }) => {
    await page.goto(`${BASE}/login`);
    await page.waitForLoadState('networkidle');

    const hasDarkClass = await page.evaluate(() =>
      document.documentElement.classList.contains('dark')
    );
    expect(hasDarkClass).toBe(true);
  });
});
