import { test, expect } from '@playwright/test'

// Saved preferences must be reachable and must survive being saved again.
//
// The form used to open only when nothing was saved, so once a feature had
// preferences nobody could get back to them. When it did open, it started
// blank, so saving it again to change one answer wiped every other one.
// A third failure hid behind the first two: the modal neither scrolled nor
// escaped the page's stacking context, so at 720px the diet form's Save button
// was off-screen and on a phone it sat under the tab bar. The plain click
// below is the check that it is reachable.
//
// These run against a mocked API, like app-shell.spec.js. Each test records
// what the form POSTs back.
const PROFILE = {
  id: 'e2e-user',
  name: 'E2E Tester',
  email: 'e2e@ayura.test',
  onboarding_complete: true,
  dominant_dosha: 'Vata',
  is_admin: false,
  allergies: ['peanuts'],
}

const SAVED = {
  diet: {
    diet_goal: 'gut_health',
    dietary_type: 'vegan',
    intermittent_fasting: 'no',
    water_intake: '2-3L',
    gut_health_issue: 'acidity',
    food_allergies: ['dairy'],
    food_intolerances: [],
    fasting_days: ['Monday', 'Ekadashi'],
  },
  panchakarma: {
    panchakarma_goal: 'detox',
    detox_experience: 'some',
    available_time_days: 14,
    setting: 'clinic',
    self_care_time_per_day: '1 hour',
    access_to_ayurvedic_herbs: 'yes',
    diet_adherence_ability: 'strict',
    koshtha: 'mridu',
    current_ayurvedic_medicines: ['Ashwagandha Churna', 'Brahmi Ghrita'],
  },
}

const isApiUrl = (url) => url.pathname.startsWith('/api/')

async function mockApi(page, posted) {
  await page.route(isApiUrl, (route) => {
    const req = route.request()
    const url = new URL(req.url())
    if (url.pathname.startsWith('/api/profile/me')) return route.fulfill({ json: PROFILE })
    if (url.pathname.startsWith('/api/plans/history')) {
      return route.fulfill({
        json: {
          items: Object.keys(SAVED).map(t => ({
            plan_type: t, plan_data: {}, created_at: new Date().toISOString(),
          })),
        },
      })
    }
    const pref = url.pathname.match(/^\/api\/preferences\/([a-z]+)\/?$/)
    if (pref) {
      if (req.method() === 'POST') {
        posted[pref[1]] = req.postDataJSON()
        return route.fulfill({ json: { feature: pref[1], preferences: posted[pref[1]], is_set: true } })
      }
      return route.fulfill({ json: { feature: pref[1], preferences: SAVED[pref[1]], is_set: true } })
    }
    return route.fulfill({ json: {} })
  })
}

test.describe('editing saved preferences (mocked API)', () => {
  test('the diet form opens on what is saved and writes it back unchanged', async ({ page }) => {
    const posted = {}
    await mockApi(page, posted)
    await page.goto('/dashboard')

    await page.getByRole('button', { name: 'Edit Diet & Nutrition preferences' }).click()
    await expect(page.locator('select[name="diet_goal"]')).toHaveValue('gut_health')
    await expect(page.locator('select[name="dietary_type"]')).toHaveValue('vegan')
    await expect(page.locator('select[name="gut_health_issue"]')).toHaveValue('acidity')
    await expect(page.locator('input[name="fasting_days"]')).toHaveValue('Monday, Ekadashi')
    // The saved allergy and the one onboarding recorded are both shown.
    await expect(page.getByRole('button', { name: 'Dairy', exact: true })).toHaveClass(/active/)
    await expect(page.getByRole('button', { name: 'Peanuts', exact: true })).toHaveClass(/active/)

    await page.getByRole('button', { name: /Save & Generate/ }).click()
    await expect.poll(() => posted.diet).toBeTruthy()
    expect(posted.diet).toMatchObject({
      diet_goal: 'gut_health',
      dietary_type: 'vegan',
      water_intake: '2-3L',
      gut_health_issue: 'acidity',
      fasting_days: ['Monday', 'Ekadashi'],
    })
    expect([...posted.diet.food_allergies].sort()).toEqual(['dairy', 'peanuts'])
  })

  test('Panchakarma keeps Koshtha and the medicines already being taken', async ({ page }) => {
    const posted = {}
    await mockApi(page, posted)
    await page.goto('/dashboard')

    await page.getByRole('button', { name: 'Edit Panchakarma Detox preferences' }).click()
    await expect(page.locator('select[name="koshtha"]')).toHaveValue('mridu')
    await expect(page.locator('input[name="available_time_days"]')).toHaveValue('14')
    await expect(page.locator('input[name="current_ayurvedic_medicines"]'))
      .toHaveValue('Ashwagandha Churna, Brahmi Ghrita')

    // Change one answer; the rest must come back as they were.
    await page.locator('select[name="setting"]').selectOption('home')
    await page.getByRole('button', { name: /Save & Generate/ }).click()
    await expect.poll(() => posted.panchakarma).toBeTruthy()
    expect(posted.panchakarma).toMatchObject({
      setting: 'home',
      koshtha: 'mridu',
      available_time_days: 14,
      detox_experience: 'some',
      current_ayurvedic_medicines: ['Ashwagandha Churna', 'Brahmi Ghrita'],
    })
  })
})
