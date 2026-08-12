/* global process */
import { test, expect } from '@playwright/test'

/**
 * End-to-end coverage for the two yoga flows that only exist in the browser:
 * the guided session player, and the end-of-week feedback that generates the
 * next week.
 *
 * Requires the seeded verify user (scratchpad/seed_ui_user.py) against a local
 * backend, and is skipped unless YOGA_E2E=1 — it needs that fixture and a
 * writable local database, neither of which CI has.
 *
 * The feedback test generates a real week, so it asserts on the delta rather
 * than an absolute week count: it mutates the fixture it runs against and must
 * stay repeatable without a reseed.
 */

test.skip(!process.env.YOGA_E2E, 'set YOGA_E2E=1 with a seeded local backend')

const EMAIL = process.env.YOGA_E2E_EMAIL || 'uiverify@ayura.test'
const PASSWORD = process.env.YOGA_E2E_PASSWORD || 'VerifyPass123!'

async function login(page) {
  await page.goto('/login')
  await page.locator('#email').fill(EMAIL)
  await page.locator('#password').fill(PASSWORD)
  await page.locator('button.auth-submit').click()
  await page.waitForURL(/dashboard|home|\/$/, { timeout: 20000 })
}

async function openYogaPlan(page) {
  await page.goto('/dashboard')
  // The plan cards live below the fold; each generated plan exposes "View Plan".
  const yogaCard = page.locator('.dash-plan-card', { hasText: /yoga/i }).first()
  await yogaCard.scrollIntoViewIfNeeded()
  await yogaCard.getByRole('button', { name: /view plan/i }).click()
  await expect(page.locator('.yoga-view')).toBeVisible({ timeout: 20000 })
}

test.describe('Yoga practice mode', () => {
  test('a day expands and offers guided practice', async ({ page }) => {
    await login(page)
    await openYogaPlan(page)

    // Every day of the week has a session — no rest days.
    const restBadges = page.locator('.yoga-duration-badge-sm.rest')
    await expect(restBadges).toHaveCount(0)

    await page.locator('.yoga-day-toggle').first().click()
    await expect(page.getByRole('button', { name: /start guided practice/i })).toBeVisible()
  })

  test('the session player counts down and advances', async ({ page }) => {
    await login(page)
    await openYogaPlan(page)
    await page.locator('.yoga-day-toggle').first().click()
    await page.getByRole('button', { name: /start guided practice/i }).click()

    const player = page.locator('.sp-overlay')
    await expect(player).toBeVisible()

    // Segment counter and a timer are present before anything is pressed.
    await expect(player.locator('.sp-step-count')).toContainText(/1 of \d+/)
    const timer = player.locator('.sp-timer')
    const startText = await timer.textContent()

    await player.getByRole('button', { name: /^start$/i }).click()
    await page.waitForTimeout(2500)
    await expect(timer).not.toHaveText(startText)

    // Skipping moves to the next segment.
    await player.getByRole('button', { name: /skip segment/i }).click()
    await expect(player.locator('.sp-step-count')).toContainText(/2 of \d+/)

    // Exiting closes the overlay.
    await player.getByRole('button', { name: /exit practice/i }).click()
    await expect(player).toBeHidden()
  })

  test('bilateral poses are announced as separate sides', async ({ page }) => {
    await login(page)
    await openYogaPlan(page)
    await page.locator('.yoga-day-toggle').first().click()
    await page.getByRole('button', { name: /start guided practice/i }).click()

    const player = page.locator('.sp-overlay')
    const titles = []
    for (let i = 0; i < 12; i++) {
      titles.push(await player.locator('.sp-title').textContent())
      const skip = player.getByRole('button', { name: /skip segment/i })
      if (!(await skip.isVisible())) break
      await skip.click()
    }
    expect(titles.some(t => /right side/i.test(t))).toBeTruthy()
    expect(titles.some(t => /left side/i.test(t))).toBeTruthy()
  })
})

test.describe('Week feedback and next-week generation', () => {
  test('feedback generates week 2 and explains the adjustment', async ({ page }) => {
    await login(page)
    await openYogaPlan(page)

    const weekTabs = page.locator('.yoga-week-tab:not(.pending)')
    const before = await weekTabs.count()
    test.skip(before >= 4, 'plan already complete — reseed to re-run')

    // The feedback card is asked about the newest week, so land on it first.
    await weekTabs.nth(before - 1).click()

    const card = page.locator('.wf-card')
    await card.scrollIntoViewIfNeeded()
    await expect(card).toBeVisible()

    await card.getByRole('button', { name: /^too hard$/i }).click()
    await card.getByRole('button', { name: /^too long$/i }).click()
    await card.getByRole('button', { name: /^drained$/i }).click()

    await card.getByRole('button', { name: /generate week/i }).click()

    // The new week appears without a page reload.
    await expect(weekTabs).toHaveCount(before + 1, { timeout: 30000 })
    await expect(page.locator('.yoga-progression-note')).toBeVisible()
    await expect(page.locator('.yoga-progression-list li').first())
      .toContainText(/shorter|gentler|restorative/i)
  })
})

test('completing a session records it', async ({ page }) => {
  await login(page)
  await openYogaPlan(page)
  await page.locator('.yoga-day-toggle').first().click()
  await page.getByRole('button', { name: /start guided practice/i }).click()

  const player = page.locator('.sp-overlay')
  await expect(player).toBeVisible()

  // Skip through to the end rather than waiting out a 30-minute practice.
  for (let i = 0; i < 60; i++) {
    const skip = player.getByRole('button', { name: /skip segment/i })
    if (!(await skip.isVisible())) break
    await skip.click()
  }

  await expect(player.getByText(/practice complete/i)).toBeVisible({ timeout: 15000 })
  // The session is posted on completion; the card says so once it lands.
  await expect(player.locator('.sp-save-state'))
    .toContainText(/saved to your timeline/i, { timeout: 15000 })
})
