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
