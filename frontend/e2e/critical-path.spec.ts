/**
 * CRITICAL PATH E2E TESTS — SignalForgeAI
 * ========================================
 * Tests that the most fundamental user flows ACTUALLY WORK.
 * If these fail, the app is broken. CI MUST NOT use continue-on-error.
 *
 * Tests:
 * 1. Login flow: auth page loads, form is functional
 * 2. Edge functions: all 20 reachable, not returning 500
 * 3. Protected routes: redirect works AND auth page is functional
 * 4. Supabase: project is alive, auth service healthy
 */

import { test, expect } from '@playwright/test'

const BASE_URL = process.env.BASE_URL || 'https://signalforgeai.predivo.ch'

// -- Project Config ----------------------------------------------------------

const CONFIG = {
  authPath: '/login',
  testEmail: 'roger@mueller.ro',
  supabaseUrl: process.env.VITE_SUPABASE_URL || 'https://mtwhjvfptlhvztplgixr.supabase.co',
  supabaseAnonKey: process.env.VITE_SUPABASE_ANON_KEY || '',
  edgeFunctions: [
    'advisor',
    'ai-usage',
    'analytics',
    'backtests',
    'broker',
    'daily-maintenance',
    'engine-cron',
    'engine-monitor',
    'holdings',
    'market',
    'positions',
    'regime',
    'send-auth-email',
    'signals',
    'simulation',
    'simulation-snapshot',
    'strategies',
    'system-status',
    'trades',
    'universe-expansion',
  ],
  protectedRoutes: [
    '/advisor',
    '/strategies',
    '/backtest',
    '/trades',
    '/analytics',
    '/risk',
    '/engine',
    '/settings',
  ],
}

// -- Login Flow --------------------------------------------------------------

test.describe('CRITICAL PATH — Login Flow', () => {
  test('login page loads without JS errors', async ({ page }) => {
    const errors: string[] = []
    page.on('pageerror', (err) => errors.push(err.message))

    await page.goto(CONFIG.authPath)
    await page.waitForLoadState('networkidle')

    expect(errors, `JS errors: ${errors.join(', ')}`).toEqual([])
  })

  test('login form is functional', async ({ page }) => {
    await page.goto(CONFIG.authPath)
    await page.waitForLoadState('networkidle')

    const emailInput = page.locator('input[type="email"]').first()
    await expect(emailInput).toBeVisible({ timeout: 10000 })
    await expect(emailInput).toBeEditable()

    const passwordInput = page.locator('input[type="password"]')
    await expect(passwordInput).toBeVisible()
    await expect(passwordInput).toBeEditable()
  })

  test('signup page accessible', async ({ page }) => {
    await page.goto('/signup')
    await page.waitForLoadState('networkidle')

    const emailInput = page.locator('input[type="email"]').first()
    await expect(emailInput).toBeVisible({ timeout: 10000 })
  })
})

// -- Edge Function Health ----------------------------------------------------

test.describe('CRITICAL PATH — Edge Functions', () => {
  for (const funcName of CONFIG.edgeFunctions) {
    test(`"${funcName}" is reachable (not 500)`, async ({ request }) => {
      const response = await request.post(
        `${CONFIG.supabaseUrl}/functions/v1/${funcName}`,
        {
          headers: { 'Content-Type': 'application/json' },
          data: JSON.stringify({ _health_check: true }),
          failOnStatusCode: false,
        }
      )

      const status = response.status()
      expect(status, `"${funcName}" returned 500 — DOWN`).not.toBe(500)

      if (status === 401) {
        const body = await response.text()
        expect(
          body.includes('requires authorization token'),
          `"${funcName}" has verify_jwt incorrectly enabled`
        ).toBe(false)
      }
    })
  }
})

// -- Protected Routes --------------------------------------------------------

test.describe('CRITICAL PATH — Route Guards', () => {
  for (const route of CONFIG.protectedRoutes) {
    test(`${route} redirects to login with working form`, async ({ page }) => {
      await page.goto(route)
      await page.waitForLoadState('networkidle')

      await expect(page).toHaveURL(/\/(login|auth)/)

      const emailInput = page.locator('input[type="email"]').first()
      await expect(emailInput).toBeVisible({ timeout: 5000 })
      await expect(emailInput).toBeEditable()
    })
  }
})

// -- Infrastructure ----------------------------------------------------------

test.describe('CRITICAL PATH — Infrastructure', () => {
  test('Supabase auth service is healthy', async ({ request }) => {
    const response = await request.get(
      `${CONFIG.supabaseUrl}/auth/v1/health`,
      {
        headers: CONFIG.supabaseAnonKey ? { apikey: CONFIG.supabaseAnonKey } : {},
        failOnStatusCode: false,
      }
    )
    expect(response.status()).toBe(200)
  })

  test('Supabase REST API is reachable', async ({ request }) => {
    const response = await request.get(
      `${CONFIG.supabaseUrl}/rest/v1/`,
      {
        headers: { apikey: 'test' },
        failOnStatusCode: false,
      }
    )
    expect(response.status()).toBeLessThan(500)
  })

  test('Production site is reachable', async ({ request }) => {
    const response = await request.get(BASE_URL, {
      failOnStatusCode: false,
    })
    expect(response.status()).toBeLessThan(500)
  })
})
