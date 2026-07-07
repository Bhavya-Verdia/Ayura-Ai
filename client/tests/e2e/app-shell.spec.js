import { test, expect } from '@playwright/test'

// App-shell smoke tests with a fully mocked API — no backend required, so
// these run anywhere (CI included). The mock returns a logged-in, onboarded
// profile plus minimal empty-state payloads; anything unlisted gets `{}`.
const PROFILE = {
  id: 'e2e-user',
  name: 'E2E Tester',
  email: 'e2e@ayura.test',
  avatar_url: null,
  onboarding_complete: true,
  dominant_dosha: 'Vata',
  is_admin: false,
}

// Match backend calls only by path prefix — a glob like `**/api/**` would also
// intercept Vite's dev-served modules (e.g. /src/api/client.js) and break boot.
const isApiUrl = (url) => url.pathname.startsWith('/api/')

async function mockApi(page) {
  await page.route(isApiUrl, (route) => {
    const url = route.request().url()
    if (url.includes('/profile/me')) return route.fulfill({ json: PROFILE })
    if (url.includes('/plans/latest')) return route.fulfill({ status: 404, json: { detail: 'No plan yet' } })
    return route.fulfill({ json: {} })
  })
}

test.describe('app shell (mocked API)', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page)
  })

  test('dashboard renders for a logged-in user', async ({ page }) => {
    await page.goto('/dashboard')
    await expect(page.locator('.dash-sidebar')).toBeVisible()
    await expect(page.getByText('Your Wellness Plans')).toBeVisible()
    // Personalised greeting uses the mocked profile
    await expect(page.getByText(/E2E/).first()).toBeVisible()
  })

  test('sidebar navigation reaches every tab without errors', async ({ page }) => {
    const pageErrors = []
    page.on('pageerror', (err) => pageErrors.push(err.message))

    await page.goto('/dashboard')
    await expect(page.locator('.dash-sidebar')).toBeVisible()

    const tabs = [
      ['/chat', '.chat-page-root, .chat-canvas, textarea'],
      ['/progress', 'h1'],
      ['/checkin', 'h1'],
      ['/timeline', 'h1'],
      ['/reminders', 'h1'],
      ['/community', 'h1'],
      ['/notifications', 'h1'],
      ['/interaction-check', 'h1'],
      ['/settings', 'h1'],
    ]
    for (const [path, marker] of tabs) {
      await page.click(`.dash-sidebar a[href="${path}"]`)
      await expect(page.locator(marker).first()).toBeVisible({ timeout: 10_000 })
    }
    expect(pageErrors).toEqual([])
  })

  test('reminders shows its empty state', async ({ page }) => {
    await page.goto('/reminders')
    await expect(page.getByText('No reminders yet').first()).toBeVisible()
  })

  test('unauthenticated visitors are redirected to login', async ({ page }) => {
    await page.route(isApiUrl, (route) => {
      const url = route.request().url()
      if (url.includes('/profile/me') || url.includes('/auth/refresh')) {
        return route.fulfill({ status: 401, json: { detail: 'Not authenticated' } })
      }
      return route.fulfill({ json: {} })
    })
    await page.goto('/dashboard')
    await expect(page).toHaveURL(/\/login/)
  })
})
