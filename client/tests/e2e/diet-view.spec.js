import { test, expect } from '@playwright/test'
import { readFileSync } from 'node:fs'

// The diet plan as the app builds it now — real output for a 62-year-old diabetic
// on warfarin who keeps a Monday fast — read the way a user reaches it. Every week
// is full detail with computed nutrition; weeks 2-4 used to be meal names only.
const DIET_PLAN = JSON.parse(readFileSync(new URL('./fixtures/diet-plan.json', import.meta.url)))

const PROFILE = {
  id: 'e2e-user', name: 'E2E Tester', email: 'e2e@ayura.test',
  onboarding_complete: true, dominant_dosha: 'Pitta', is_admin: false,
}

async function openDiet(page) {
  await page.route((url) => url.pathname.startsWith('/api/'), (route) => {
    const p = new URL(route.request().url()).pathname
    if (p.startsWith('/api/profile/me')) return route.fulfill({ json: PROFILE })
    if (p.startsWith('/api/plans/history')) {
      return route.fulfill({ json: { items: [{ plan_type: 'diet', plan_data: { diet_plan: DIET_PLAN }, created_at: DIET_PLAN.generated_at }] } })
    }
    return route.fulfill({ json: {} })
  })
  await page.goto('/dashboard')
  await page.locator('.dash-plan-card', { hasText: 'Diet & Nutrition' }).getByRole('button', { name: /View Plan/ }).click()
}

test.describe('diet view (real plan fixture)', () => {
  test('targets, medicines and the withheld fast are shown with their sources', async ({ page }) => {
    await openDiet(page)
    const targets = page.locator('.diet-targets-card')
    await expect(targets).toContainText('Carbohydrate')
    await expect(targets).toContainText('Sodium')
    await targets.getByRole('button', { name: /Where these numbers come from/ }).click()
    await expect(targets).toContainText('ADA')
    const clinical = page.locator('.diet-clinical-card')
    await expect(clinical).toContainText('Fasting')
    await expect(clinical).toContainText('Warfarin')
    await expect(clinical).toContainText('Metformin')
    await expect(page.locator('.diet-energy-card')).toContainText('calculated from the foods and grams')
  })

  test('week 3 is full detail, with portions and computed nutrition', async ({ page }) => {
    await openDiet(page)
    await page.getByRole('button', { name: /Week 3/ }).click()
    await page.getByRole('button', { name: /^Wed/ }).click()
    const lunch = page.locator('.diet-meal-card.meal-lunch')
    await expect(lunch).toContainText(DIET_PLAN.diet_weeks[2].daily_plan.Wednesday.lunch.meal_name)
    await lunch.getByRole('button').first().click()
    await expect(lunch.locator('.diet-llm-portion')).toContainText(' g')
    await expect(page.locator('.diet-day-macros')).toContainText('calculated')
    await expect(page.locator('.diet-compact-meals')).toHaveCount(0)
  })
})

test.describe('diet view — where you are in the plan', () => {
  // The same plan, written nine days ago: week 2 is under way.
  const RECENT = { ...DIET_PLAN, generated_at: new Date(Date.now() - 9 * 864e5).toISOString() }

  async function openRecent(page, onReplace) {
    await page.route((url) => url.pathname.startsWith('/api/'), (route) => {
      const p = new URL(route.request().url()).pathname
      if (p.startsWith('/api/profile/me')) return route.fulfill({ json: PROFILE })
      if (p.startsWith('/api/plans/history')) {
        return route.fulfill({ json: { items: [{ plan_type: 'diet', plan_data: { diet_plan: RECENT }, created_at: RECENT.generated_at }] } })
      }
      if (p.startsWith('/api/meals/replace')) return onReplace(route)
      return route.fulfill({ json: {} })
    })
    await page.goto('/dashboard')
    await page.locator('.dash-plan-card', { hasText: 'Diet & Nutrition' }).getByRole('button', { name: /View Plan/ }).click()
  }

  test('opens on today, not week 1 Monday, and offers no end-of-plan card', async ({ page }) => {
    await openRecent(page, (r) => r.fulfill({ json: {} }))
    const heading = page.locator('.diet-day-heading')
    await expect(heading).toContainText('Week 2')
    await expect(heading).toContainText('Today')
    await expect(page.locator('.diet-day-btn.is-today')).toHaveCount(1)
    await expect(page.locator('.diet-plan-complete')).toHaveCount(0)
  })

  test('another dish replaces the meal in place, and can be put back', async ({ page }) => {
    let body = null
    await openRecent(page, (route) => {
      body = JSON.parse(route.request().postData())
      const week = RECENT.diet_weeks.find(w => w.week_number === body.week)
      const day = structuredClone(week.daily_plan[body.day])
      day[body.slot] = { ...day[body.slot], meal_name: 'Vegetable Khichdi', replaced_from: week.daily_plan[body.day][body.slot] }
      return route.fulfill({ json: { week: body.week, day_name: body.day, day } })
    })
    const lunch = page.locator('.diet-meal-card.meal-lunch')
    await lunch.getByRole('button', { name: /Another dish/ }).click()
    await expect(lunch.locator('.diet-meal-name-llm')).toHaveText('Vegetable Khichdi')
    expect(body).toMatchObject({ week: 2, slot: 'lunch', undo: false })
    await expect(lunch.getByRole('button', { name: /^Back to / })).toBeVisible()
  })
})

test('a finished plan opens on its last week, under the end-of-plan card', async ({ page }) => {
  const OLD = { ...DIET_PLAN, generated_at: new Date(Date.now() - 40 * 864e5).toISOString() }
  await page.route((url) => url.pathname.startsWith('/api/'), (route) => {
    const p = new URL(route.request().url()).pathname
    if (p.startsWith('/api/profile/me')) return route.fulfill({ json: PROFILE })
    if (p.startsWith('/api/plans/history')) {
      return route.fulfill({ json: { items: [{ plan_type: 'diet', plan_data: { diet_plan: OLD }, created_at: OLD.generated_at }] } })
    }
    return route.fulfill({ json: {} })
  })
  await page.goto('/dashboard')
  await page.locator('.dash-plan-card', { hasText: 'Diet & Nutrition' }).getByRole('button', { name: /View Plan/ }).click()
  await expect(page.locator('.diet-plan-complete')).toBeVisible()
  await expect(page.locator('.diet-day-heading')).toContainText('Week 4')
})
