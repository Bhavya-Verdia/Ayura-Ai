import { test, expect } from '@playwright/test'

// Onboarding regression, mocked API — no backend required.
//
// The bug this guards: the wizard's per-step rules ran from "Continue", and the
// LAST step has no Continue button. So goal and dosha — the two required answers
// on that step — were checked by nothing, went to the API as "", and came back a
// 422 whose `detail` is a LIST. That list was set as the error string and thrown
// at JSX, which crashed the page into the ErrorBoundary with everything the user
// had typed. Two real signups on 2026-09-09 saved nothing at all.

const NEW_USER = {
  id: 'e2e-new-user',
  name: 'Fresh Signup',
  email: 'fresh@ayura.test',
  avatar_url: null,
  onboarding_complete: false,
  dominant_dosha: null,
  is_admin: false,
}

const isApiUrl = (url) => url.pathname.startsWith('/api/')

/** Mocks the API and records every PUT /profile/me body that is actually sent. */
async function mockApi(page, { putStatus = 200 } = {}) {
  const puts = []
  await page.route(isApiUrl, (route) => {
    const req = route.request()
    const url = req.url()
    if (url.includes('/profile/me') && req.method() === 'PUT') {
      puts.push(req.postDataJSON())
      if (putStatus !== 200) {
        // The real 422 shape: `detail` is a list of error objects.
        return route.fulfill({
          status: 422,
          json: {
            detail: [
              {
                type: 'string_pattern_mismatch',
                loc: ['body', 'dominant_dosha'],
                msg: "String should match pattern '^(vata|pitta|kapha)$'",
                input: '',
              },
            ],
          },
        })
      }
      return route.fulfill({ json: { ...NEW_USER, ...puts[puts.length - 1], onboarding_complete: true } })
    }
    if (url.includes('/profile/me')) return route.fulfill({ json: NEW_USER })
    return route.fulfill({ json: {} })
  })
  return puts
}

async function fillFirstTwoSteps(page) {
  await page.goto('/onboarding')
  await page.locator('#onb-name').fill('Fresh Signup')
  await page.locator('#onb-age').fill('24')
  await page.getByRole('button', { name: 'Male', exact: true }).click()
  await page.getByRole('button', { name: 'Continue →' }).click()

  await page.locator('#onb-height').fill('175')
  await page.locator('#onb-weight').fill('70')
  // Required since activity_level stopped being hardcoded to 'moderate'. It sets the
  // diet plan's calorie target, which swings 2040-3220 kcal across these five
  // answers for one body.
  await page.getByRole('button', { name: /Desk-bound/ }).click()
  await page.getByRole('button', { name: 'Continue →' }).click()

  await expect(page.getByRole('button', { name: 'Complete Setup →' })).toBeVisible()
}

test.describe('onboarding (mocked API)', () => {
  test('unanswered goal is a message, not a lost form', async ({ page }) => {
    const puts = await mockApi(page)
    await fillFirstTwoSteps(page)

    // Dosha picked, goal skipped — the exact half-filled last step.
    await page.getByRole('button', { name: /^Vata/ }).click()
    await page.getByRole('button', { name: 'Complete Setup →' }).click()

    await expect(page.locator('.onb-error')).toHaveText('Please choose your primary wellness goal.')
    // Nothing was sent, and the wizard is still standing.
    expect(puts).toHaveLength(0)
    await expect(page.getByRole('button', { name: 'Complete Setup →' })).toBeVisible()
    await expect(page.getByText('Something went wrong.')).toHaveCount(0)
  })

  test('a complete last step saves and moves on', async ({ page }) => {
    const puts = await mockApi(page)
    await fillFirstTwoSteps(page)

    await page.getByRole('button', { name: /^Weight Loss/ }).click()
    await page.getByRole('button', { name: /^Vata/ }).click()
    await page.getByRole('button', { name: 'Complete Setup →' }).click()

    await expect(page).toHaveURL(/\/dosha-quiz/)
    expect(puts).toHaveLength(1)
    expect(puts[0]).toMatchObject({
      gender: 'male', age: 24, height_cm: 175, weight_kg: 70,
      goal: 'weight_loss', dominant_dosha: 'vata',
      // The answer, not the constant. This was `activity_level: 'moderate'` for
      // every user the app has ever had, while the diet plan read it as the basis
      // of a target it calls "a clinical target, not a suggestion".
      activity_level: 'sedentary',
    })
  })

  test('activity level is required, because the calorie target is computed from it', async ({ page }) => {
    const puts = await mockApi(page)
    await page.goto('/onboarding')
    await page.locator('#onb-name').fill('Fresh Signup')
    await page.locator('#onb-age').fill('24')
    await page.getByRole('button', { name: 'Male', exact: true }).click()
    await page.getByRole('button', { name: 'Continue →' }).click()

    await page.locator('#onb-height').fill('175')
    await page.locator('#onb-weight').fill('70')
    await page.getByRole('button', { name: 'Continue →' }).click()

    await expect(page.locator('.onb-error')).toHaveText('Please choose how active your usual week is.')
    expect(puts).toHaveLength(0)
  })

  test('a 422 from the API reads as text instead of crashing the page', async ({ page }) => {
    await mockApi(page, { putStatus: 422 })
    await fillFirstTwoSteps(page)

    await page.getByRole('button', { name: /^Weight Loss/ }).click()
    await page.getByRole('button', { name: /^Vata/ }).click()
    await page.getByRole('button', { name: 'Complete Setup →' }).click()

    await expect(page.locator('.onb-error')).toContainText('dominant_dosha')
    await expect(page.getByText('Something went wrong.')).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Complete Setup →' })).toBeVisible()
  })
})
