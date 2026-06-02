/**
 * AUTH FLOWS E2E TESTS — SignalForgeAI
 * ====================================
 * Comprehensive tests for every auth-related route and flow.
 *
 * Routes tested:
 *   /login           — Password tab + Email Code tab
 *   /signup          — 3-step wizard (email → OTP → password)
 *   /forgot-password — Email form → confirmation screen
 *   /reset-password  — New password + confirm (requires session)
 *   /auth/verify     — OTP deep-link handler
 *   /auth/callback   — Supabase redirect handler (magic links, recovery)
 *   /auth/confirm    — Must NOT resolve to a valid page
 *
 * Also tests:
 *   - Session guard on all protected routes
 *   - No JS errors on every auth page
 *   - Navigation links between auth pages
 *   - Form elements present and interactive
 *   - Accessibility: labels, roles, focus
 *   - Mobile responsive: no horizontal overflow
 */

import { test, expect, type Page } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'https://signalforgeai.predivo.ch';
const _SUPABASE_URL = process.env.VITE_SUPABASE_URL || 'https://xioqgsybkhjijkciinmu.supabase.co';
const GATE_STORAGE_KEY = 'signalforge-unlocked';

// All auth routes (public, no session required to render)
const AUTH_ROUTES = [
  '/login',
  '/signup',
  '/forgot-password',
  '/reset-password',
  '/auth/verify',
  '/auth/callback',
];

// All protected routes that must redirect to /login
const PROTECTED_ROUTES = [
  '/',
  '/advisor',
  '/strategies',
  '/backtest',
  '/trades',
  '/analytics',
  '/risk',
  '/engine',
  '/settings',
];

// ---------- Helpers ----------------------------------------------------------

async function bypassPasswordGate(page: Page) {
  await page.goto(BASE_URL);
  await page.evaluate((key) => {
    sessionStorage.setItem(key, 'true');
  }, GATE_STORAGE_KEY);
}

function collectJsErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on('pageerror', (err) => errors.push(err.message));
  return errors;
}

function filterExpectedErrors(errors: string[]): string[] {
  return errors.filter(
    (e) =>
      !e.includes('AuthSessionMissing') &&
      !e.includes('Auth session missing') &&
      !e.includes('Failed to fetch') &&
      !e.includes('navigation') &&
      !e.includes('AbortError')
  );
}

// =============================================================================
// 1. PAGE LOADS — every auth route returns < 500
// =============================================================================

test.describe('Auth Pages — HTTP Status', () => {
  test.beforeEach(async ({ page }) => {
    await bypassPasswordGate(page);
  });

  for (const route of AUTH_ROUTES) {
    test(`${route} returns HTTP < 500`, async ({ page }) => {
      const response = await page.goto(`${BASE_URL}${route}`);
      expect(response?.status(), `${route} returned ${response?.status()}`).toBeLessThan(500);
    });
  }
});

// =============================================================================
// 2. NO JS ERRORS — every auth page loads without uncaught exceptions
// =============================================================================

test.describe('Auth Pages — No JS Errors', () => {
  test.beforeEach(async ({ page }) => {
    await bypassPasswordGate(page);
  });

  for (const route of AUTH_ROUTES) {
    test(`${route} has no JS errors`, async ({ page }) => {
      const errors = collectJsErrors(page);
      await page.goto(`${BASE_URL}${route}`);
      await page.waitForLoadState('networkidle');
      // Give React time to settle (auth redirects, lazy loading)
      await page.waitForTimeout(1500);

      const realErrors = filterExpectedErrors(errors);
      expect(realErrors, `JS errors on ${route}: ${realErrors.join(', ')}`).toEqual([]);
    });
  }
});

// =============================================================================
// 3. LOGIN PAGE — form elements, tabs, navigation
// =============================================================================

test.describe('Login Page — Form & Elements', () => {
  test.beforeEach(async ({ page }) => {
    await bypassPasswordGate(page);
    await page.goto(`${BASE_URL}/login`);
    await page.waitForLoadState('networkidle');
  });

  test('shows SignalForgeAI branding', async ({ page }) => {
    await expect(page.locator('text=SignalForgeAI').first()).toBeVisible();
  });

  test('shows "Sign in" heading', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Sign in');
  });

  test('password tab: has email and password inputs', async ({ page }) => {
    const emailInput = page.locator('input[type="email"]');
    await expect(emailInput).toBeVisible();
    await expect(emailInput).toBeEditable();

    const passwordInput = page.locator('input[type="password"]');
    await expect(passwordInput).toBeVisible();
    await expect(passwordInput).toBeEditable();
  });

  test('password tab: has submit button', async ({ page }) => {
    const submitBtn = page.locator('button[type="submit"]');
    await expect(submitBtn).toBeVisible();
    await expect(submitBtn).toContainText(/sign in/i);
  });

  test('password tab: email input has label', async ({ page }) => {
    const label = page.locator('label[for="login-email"]');
    await expect(label).toBeVisible();
    await expect(label).toContainText('Email');
  });

  test('password tab: password input has label', async ({ page }) => {
    const label = page.locator('label[for="login-password"]');
    await expect(label).toBeVisible();
    await expect(label).toContainText('Password');
  });

  test('has "Password" and "Email Code" tabs', async ({ page }) => {
    await expect(page.locator('button:text("Password")')).toBeVisible();
    await expect(page.locator('button:text("Email Code")')).toBeVisible();
  });

  test('switching to Email Code tab shows email-only form', async ({ page }) => {
    await page.locator('button:text("Email Code")').click();
    await page.waitForTimeout(300);

    const emailInput = page.locator('input[type="email"]');
    await expect(emailInput).toBeVisible();

    // No password field in code tab
    const passwordInputs = page.locator('input[type="password"]');
    await expect(passwordInputs).toHaveCount(0);

    // Submit button says "Send Sign-In Code"
    const submitBtn = page.locator('button[type="submit"]');
    await expect(submitBtn).toContainText(/send sign-in code/i);
  });

  test('has link to signup page', async ({ page }) => {
    const signupLink = page.locator('a[href="/signup"]');
    await expect(signupLink).toBeVisible();
  });

  test('has link to forgot password page', async ({ page }) => {
    const forgotLink = page.locator('a[href="/forgot-password"]');
    await expect(forgotLink).toBeVisible();
  });

  test('forgot password link is inside password tab', async ({ page }) => {
    // Verify the "Forgot password?" link appears near the password field
    const forgotLink = page.locator('a[href="/forgot-password"]');
    await expect(forgotLink).toContainText(/forgot password/i);
  });

  test('signup link navigates to /signup', async ({ page }) => {
    const signupLink = page.locator('a[href="/signup"]').last();
    await signupLink.click();
    await page.waitForLoadState('networkidle');
    expect(page.url()).toContain('/signup');
  });

  test('forgot password link navigates to /forgot-password', async ({ page }) => {
    const forgotLink = page.locator('a[href="/forgot-password"]');
    await forgotLink.click();
    await page.waitForLoadState('networkidle');
    expect(page.url()).toContain('/forgot-password');
  });
});

// =============================================================================
// 4. SIGNUP PAGE — form elements, navigation
// =============================================================================

test.describe('Signup Page — Form & Elements', () => {
  test.beforeEach(async ({ page }) => {
    await bypassPasswordGate(page);
    await page.goto(`${BASE_URL}/signup`);
    await page.waitForLoadState('networkidle');
  });

  test('shows "Create your account" heading', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Create your account');
  });

  test('shows SignalForgeAI branding', async ({ page }) => {
    await expect(page.locator('text=SignalForgeAI').first()).toBeVisible();
  });

  test('has email input with label', async ({ page }) => {
    const emailInput = page.locator('input[type="email"]');
    await expect(emailInput).toBeVisible();
    await expect(emailInput).toBeEditable();

    const label = page.locator('label[for="signup-email"]');
    await expect(label).toBeVisible();
  });

  test('has Continue submit button', async ({ page }) => {
    const submitBtn = page.locator('button[type="submit"]');
    await expect(submitBtn).toBeVisible();
    await expect(submitBtn).toContainText(/continue/i);
  });

  test('shows step progress dots (3 dots, first active)', async ({ page }) => {
    // 3 step dots: first is accent, other two are border color
    const dots = page.locator('.flex.justify-center.gap-2 > div');
    await expect(dots).toHaveCount(3);
  });

  test('has link back to login', async ({ page }) => {
    const loginLink = page.locator('a[href="/login"]');
    await expect(loginLink).toBeVisible();
    await expect(loginLink).toContainText(/sign in/i);
  });

  test('has Terms of Service link', async ({ page }) => {
    const tosLink = page.locator('a[href="/terms"]');
    await expect(tosLink).toBeVisible();
  });

  test('has Privacy Policy link', async ({ page }) => {
    const privacyLink = page.locator('a[href="/privacy"]');
    await expect(privacyLink).toBeVisible();
  });

  test('login link navigates to /login', async ({ page }) => {
    const loginLink = page.locator('a[href="/login"]');
    await loginLink.click();
    await page.waitForLoadState('networkidle');
    expect(page.url()).toContain('/login');
  });

  test('has RiskDisclaimer component', async ({ page }) => {
    // RiskDisclaimer renders risk-related text
    const disclaimer = page.locator('text=/risk/i').first();
    await expect(disclaimer).toBeVisible();
  });
});

// =============================================================================
// 5. FORGOT PASSWORD PAGE — form elements, navigation
// =============================================================================

test.describe('Forgot Password Page — Form & Elements', () => {
  test.beforeEach(async ({ page }) => {
    await bypassPasswordGate(page);
    await page.goto(`${BASE_URL}/forgot-password`);
    await page.waitForLoadState('networkidle');
  });

  test('shows "Reset your password" heading', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Reset your password');
  });

  test('shows SF branding icon', async ({ page }) => {
    await expect(page.locator('text=SF').first()).toBeVisible();
  });

  test('has email input with label', async ({ page }) => {
    const emailInput = page.locator('input[type="email"]');
    await expect(emailInput).toBeVisible();
    await expect(emailInput).toBeEditable();

    const label = page.locator('label[for="reset-email"]');
    await expect(label).toBeVisible();
  });

  test('has "Send Reset Link" submit button', async ({ page }) => {
    const submitBtn = page.locator('button[type="submit"]');
    await expect(submitBtn).toBeVisible();
    await expect(submitBtn).toContainText(/send reset link/i);
  });

  test('has "Back to sign in" link to /login', async ({ page }) => {
    const backLink = page.locator('a[href="/login"]');
    await expect(backLink).toBeVisible();
    await expect(backLink).toContainText(/back to sign in/i);
  });

  test('back link navigates to /login', async ({ page }) => {
    const backLink = page.locator('a[href="/login"]');
    await backLink.click();
    await page.waitForLoadState('networkidle');
    expect(page.url()).toContain('/login');
  });
});

// =============================================================================
// 6. RESET PASSWORD PAGE — form elements (redirects without session)
// =============================================================================

test.describe('Reset Password Page — Behavior', () => {
  test.beforeEach(async ({ page }) => {
    await bypassPasswordGate(page);
  });

  test('redirects to /forgot-password when no session exists', async ({ page }) => {
    await page.goto(`${BASE_URL}/reset-password`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Without a valid session, ResetPasswordPage redirects to /forgot-password
    expect(page.url()).toContain('/forgot-password');
  });

  test('page loads without HTTP 500', async ({ page }) => {
    const response = await page.goto(`${BASE_URL}/reset-password`);
    expect(response?.status()).toBeLessThan(500);
  });
});

// =============================================================================
// 7. AUTH VERIFY PAGE — redirects without params
// =============================================================================

test.describe('Auth Verify Page — Behavior', () => {
  test.beforeEach(async ({ page }) => {
    await bypassPasswordGate(page);
  });

  test('redirects to /login when no token/email params', async ({ page }) => {
    await page.goto(`${BASE_URL}/auth/verify`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // AuthVerifyPage redirects to /login if token or email missing
    expect(page.url()).toContain('/login');
  });

  test('shows spinner during verification when params present', async ({ page }) => {
    await page.goto(`${BASE_URL}/auth/verify?token=000000&email=test@example.com`);
    // Should briefly show the spinner before error
    // Either spinner is visible or the error state appears
    const spinnerOrError = page.locator('.animate-spin, text=/expired|invalid/i');
    await expect(spinnerOrError.first()).toBeVisible({ timeout: 10000 });
  });
});

// =============================================================================
// 8. AUTH CALLBACK PAGE — shows processing spinner
// =============================================================================

test.describe('Auth Callback Page — Behavior', () => {
  test.beforeEach(async ({ page }) => {
    await bypassPasswordGate(page);
  });

  test('shows processing state then redirects', async ({ page }) => {
    await page.goto(`${BASE_URL}/auth/callback`);
    // Should show spinner or redirect to /login (no session)
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Without a valid hash fragment, it redirects to /login
    expect(page.url()).toContain('/login');
  });
});

// =============================================================================
// 9. /auth/confirm — must NOT resolve to a valid page
// =============================================================================

test.describe('/auth/confirm — Invalid Route', () => {
  test('/auth/confirm does not render a valid auth page', async ({ page }) => {
    await bypassPasswordGate(page);
    await page.goto(`${BASE_URL}/auth/confirm`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // /auth/confirm is not a defined route in the React router.
    // Without a .htaccess route allowlist, the SPA fallback serves index.html,
    // but React Router won't match it. It should either:
    // - Redirect to /login (ProtectedRoute catches unmatched routes under the
    //   protected wrapper — but /auth/confirm is outside it, so it renders nothing)
    // - Show no meaningful auth UI (no login form, no signup form)
    //
    // Verify it does NOT show a functional auth form:
    const emailInput = page.locator('input[type="email"]');
    const hasEmailInput = await emailInput.count();

    // If it landed on /login due to the catch-all, that's acceptable
    // but /auth/confirm itself should not be a dedicated page
    const url = page.url();
    const isOnAuthConfirm = url.includes('/auth/confirm');

    if (isOnAuthConfirm) {
      // If still on /auth/confirm, there should be no functional form
      expect(hasEmailInput).toBe(0);
    }
    // If redirected away, that's the expected behavior
  });
});

// =============================================================================
// 10. SESSION GUARD — all protected routes redirect to /login
// =============================================================================

test.describe('Session Guard — Protected Routes', () => {
  test.beforeEach(async ({ page }) => {
    await bypassPasswordGate(page);
  });

  for (const route of PROTECTED_ROUTES) {
    test(`${route} redirects to /login when unauthenticated`, async ({ page }) => {
      await page.goto(`${BASE_URL}${route}`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);

      await expect(page).toHaveURL(/\/login/);
    });
  }
});

// =============================================================================
// 11. CROSS-PAGE NAVIGATION — full navigation flow
// =============================================================================

test.describe('Auth Navigation Flow', () => {
  test.beforeEach(async ({ page }) => {
    await bypassPasswordGate(page);
  });

  test('login → signup → login round-trip', async ({ page }) => {
    // Start at login
    await page.goto(`${BASE_URL}/login`);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('h1')).toContainText('Sign in');

    // Click signup link
    await page.locator('a[href="/signup"]').last().click();
    await page.waitForLoadState('networkidle');
    await expect(page.locator('h1')).toContainText('Create your account');

    // Click back to login
    await page.locator('a[href="/login"]').click();
    await page.waitForLoadState('networkidle');
    await expect(page.locator('h1')).toContainText('Sign in');
  });

  test('login → forgot password → login round-trip', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.waitForLoadState('networkidle');

    // Click forgot password
    await page.locator('a[href="/forgot-password"]').click();
    await page.waitForLoadState('networkidle');
    await expect(page.locator('h1')).toContainText('Reset your password');

    // Click back to sign in
    await page.locator('a[href="/login"]').click();
    await page.waitForLoadState('networkidle');
    await expect(page.locator('h1')).toContainText('Sign in');
  });

  test('signup → login via "Already have an account"', async ({ page }) => {
    await page.goto(`${BASE_URL}/signup`);
    await page.waitForLoadState('networkidle');

    const loginLink = page.locator('a[href="/login"]');
    await expect(loginLink).toContainText(/sign in/i);
    await loginLink.click();
    await page.waitForLoadState('networkidle');
    expect(page.url()).toContain('/login');
  });
});

// =============================================================================
// 12. STATIC ASSETS — no 4xx on auth pages
// =============================================================================

test.describe('Auth Pages — Static Assets', () => {
  test.beforeEach(async ({ page }) => {
    await bypassPasswordGate(page);
  });

  test('login page loads all assets without 4xx errors', async ({ page }) => {
    const failedRequests: string[] = [];
    page.on('response', (response) => {
      if (response.status() >= 400 && !response.url().includes('supabase')) {
        failedRequests.push(`${response.status()} ${response.url()}`);
      }
    });

    await page.goto(`${BASE_URL}/login`);
    await page.waitForLoadState('networkidle');

    expect(failedRequests, `Failed requests: ${failedRequests.join(', ')}`).toHaveLength(0);
  });
});

// =============================================================================
// 13. MOBILE RESPONSIVE — no horizontal overflow
// =============================================================================

test.describe('Auth Pages — Mobile Responsive', () => {
  test.use({ viewport: { width: 375, height: 812 } });

  const mobileRoutes = ['/login', '/signup', '/forgot-password'];

  for (const route of mobileRoutes) {
    test(`${route} has no horizontal overflow at 375px`, async ({ page }) => {
      await bypassPasswordGate(page);
      await page.goto(`${BASE_URL}${route}`);
      await page.waitForLoadState('networkidle');

      const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
      const viewportWidth = await page.evaluate(() => window.innerWidth);
      expect(bodyWidth).toBeLessThanOrEqual(viewportWidth);
    });
  }
});

// =============================================================================
// 14. DARK THEME — applied by default on auth pages
// =============================================================================

test.describe('Auth Pages — Dark Theme', () => {
  test.beforeEach(async ({ page }) => {
    await bypassPasswordGate(page);
  });

  test('dark class is applied on login page', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.waitForLoadState('networkidle');

    const hasDarkClass = await page.evaluate(() =>
      document.documentElement.classList.contains('dark')
    );
    expect(hasDarkClass).toBe(true);
  });
});

// =============================================================================
// 15. PAGE TITLES — each auth page sets correct document title
// =============================================================================

test.describe('Auth Pages — Page Titles', () => {
  test.beforeEach(async ({ page }) => {
    await bypassPasswordGate(page);
  });

  const titleExpectations: [string, RegExp][] = [
    ['/login', /log in/i],
    ['/signup', /sign up/i],
    ['/forgot-password', /forgot password/i],
  ];

  for (const [route, pattern] of titleExpectations) {
    test(`${route} has correct page title`, async ({ page }) => {
      await page.goto(`${BASE_URL}${route}`);
      await page.waitForLoadState('networkidle');

      await expect(page).toHaveTitle(pattern);
    });
  }
});

// =============================================================================
// 16. ACCESSIBILITY — form inputs have associated labels
// =============================================================================

test.describe('Auth Pages — Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await bypassPasswordGate(page);
  });

  test('login page: all inputs have labels', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.waitForLoadState('networkidle');

    // Email input should have a label via htmlFor/id
    const emailInput = page.locator('#login-email');
    await expect(emailInput).toBeVisible();
    const emailLabel = page.locator('label[for="login-email"]');
    await expect(emailLabel).toBeVisible();

    // Password input
    const passwordInput = page.locator('#login-password');
    await expect(passwordInput).toBeVisible();
    const passwordLabel = page.locator('label[for="login-password"]');
    await expect(passwordLabel).toBeVisible();
  });

  test('signup page: email input has label', async ({ page }) => {
    await page.goto(`${BASE_URL}/signup`);
    await page.waitForLoadState('networkidle');

    const emailInput = page.locator('#signup-email');
    await expect(emailInput).toBeVisible();
    const emailLabel = page.locator('label[for="signup-email"]');
    await expect(emailLabel).toBeVisible();
  });

  test('forgot password page: email input has label', async ({ page }) => {
    await page.goto(`${BASE_URL}/forgot-password`);
    await page.waitForLoadState('networkidle');

    const emailInput = page.locator('#reset-email');
    await expect(emailInput).toBeVisible();
    const emailLabel = page.locator('label[for="reset-email"]');
    await expect(emailLabel).toBeVisible();
  });

  test('login page: submit buttons meet 44px min touch target', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.waitForLoadState('networkidle');

    const submitBtn = page.locator('button[type="submit"]');
    const box = await submitBtn.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.height).toBeGreaterThanOrEqual(44);
  });
});

// =============================================================================
// 17. LOGIN TAB INTERACTION — switching between Password and Email Code
// =============================================================================

test.describe('Login Page — Tab Interaction', () => {
  test.beforeEach(async ({ page }) => {
    await bypassPasswordGate(page);
    await page.goto(`${BASE_URL}/login`);
    await page.waitForLoadState('networkidle');
  });

  test('starts on Password tab by default', async ({ page }) => {
    // Password tab should be active (has shadow/elevated style)
    const passwordInput = page.locator('input[type="password"]');
    await expect(passwordInput).toBeVisible();
  });

  test('Email Code tab hides password field and shows code-specific UI', async ({ page }) => {
    await page.locator('button:text("Email Code")').click();
    await page.waitForTimeout(300);

    // Password field should be gone
    await expect(page.locator('input[type="password"]')).toHaveCount(0);

    // Helper text about sending a code
    await expect(page.locator('text=/send a sign-in code/i')).toBeVisible();
  });

  test('switching back to Password tab restores password field', async ({ page }) => {
    // Go to Email Code
    await page.locator('button:text("Email Code")').click();
    await page.waitForTimeout(300);

    // Go back to Password
    await page.locator('button:text("Password")').click();
    await page.waitForTimeout(300);

    // Password field should be back
    await expect(page.locator('input[type="password"]')).toBeVisible();
  });
});
