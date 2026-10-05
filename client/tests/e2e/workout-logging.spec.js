import { test, expect } from '@playwright/test'
import { readFileSync } from 'node:fs'

// Logging a set from inside the plan, the way a user reaches it: Dashboard,
// then View Plan, then the day, then the exercise. The component tests drove
// the logger on its own and handed it a plan id directly. That would not
// notice if the plan the Dashboard renders had none, in which case the logger
// renders nothing at all.
//
// The fixture is real engine output (week one only): a 3-day intermediate
// strength plan. The API is mocked like app-shell.spec.js, with an in-memory
// log store so a reload shows what was saved.
const GYM_PLAN = JSON.parse(readFileSync(new URL('./fixtures/gym-plan.json', import.meta.url)))

const PROFILE = {
  id: 'e2e-user',
  name: 'E2E Tester',
  email: 'e2e@ayura.test',
  onboarding_complete: true,
  dominant_dosha: 'Vata',
  is_admin: false,
}

const isApiUrl = (url) => url.pathname.startsWith('/api/')

async function mockApi(page, store) {
  await page.route(isApiUrl, (route) => {
    const req = route.request()
    const url = new URL(req.url())
    if (url.pathname.startsWith('/api/profile/me')) return route.fulfill({ json: PROFILE })
    if (url.pathname.startsWith('/api/plans/history')) {
      return route.fulfill({
        json: { items: [{ plan_type: 'gym', plan_data: { gym_plan: GYM_PLAN }, created_at: new Date().toISOString() }] },
      })
    }
    if (url.pathname.startsWith('/api/workouts/logs')) {
      if (req.method() === 'POST') {
        const body = req.postDataJSON()
        store.posted.push(body)
        store.logs[`${body.week}:${body.day}:${body.exercise_id}`] = body
        return route.fulfill({ json: { ok: true } })
      }
      expect(url.searchParams.get('plan_id')).toBe(GYM_PLAN.plan_id)
      return route.fulfill({ json: { logs: Object.values(store.logs) } })
    }
    return route.fulfill({ json: {} })
  })
}

async function openSquat(page) {
  await page.goto('/dashboard')
  await page.locator('.dash-plan-card', { hasText: 'Fitness & Gym' })
    .getByRole('button', { name: /View Plan/ }).click()
  await page.getByRole('button', { name: /Monday/ }).first().click()
  return page.locator('.gym-exercise-row', { hasText: 'Barbell Squat' }).first()
}

test.describe('workout logging (mocked API)', () => {
  test('a set logged in the plan is saved against it and shown on return', async ({ page }) => {
    const store = { posted: [], logs: {} }
    await mockApi(page, store)

    const squat = await openSquat(page)
    await squat.getByRole('button', { name: /Log your sets/ }).click()
    const editor = squat.getByRole('group', { name: /Log sets for Barbell Squat/ })
    // The plan asks for four sets, so four rows open.
    await expect(editor.getByPlaceholder('reps')).toHaveCount(4)
    await editor.getByLabel('Set 1 kg').fill('100')
    await editor.getByLabel('Set 1 reps').fill('5')
    await editor.getByLabel('Set 2 kg').fill('100')
    await editor.getByLabel('Set 2 reps').fill('4')
    await editor.getByRole('radio', { name: 'Very hard' }).click()
    await editor.getByRole('button', { name: 'Save' }).click()

    await expect(squat.getByText('Logged: 100×5, 100×4')).toBeVisible()
    // Empty rows are not sent as sets of zero.
    expect(store.posted).toEqual([{
      plan_id: GYM_PLAN.plan_id,
      week: 1,
      day: 1,
      exercise_id: 'barbell_squat',
      sets: [{ kg: 100, reps: 5 }, { kg: 100, reps: 4 }],
      effort: 'hard',
    }])

    // A fresh load reads the log back from the server, not from component state.
    await page.reload()
    const again = await openSquat(page)
    await expect(again.getByText('Logged: 100×5, 100×4')).toBeVisible()
    await again.getByRole('button', { name: /Edit/ }).click()
    await expect(again.getByLabel('Set 2 reps')).toHaveValue('4')
    await expect(again.getByRole('radio', { name: 'Very hard' })).toHaveAttribute('aria-checked', 'true')
  })

  test('effort-based work has nothing to log, and every lift does', async ({ page }) => {
    await mockApi(page, { posted: [], logs: {} })
    await openSquat(page)
    const day = page.locator('.gym-day-card.open')
    // Monday is four barbell lifts and a Mountain Climbers interval finisher.
    for (const lift of ['Barbell Squat', 'Barbell Bench Press', 'Bent Over Barbell Row', 'Barbell Shoulder Press']) {
      await expect(day.locator('.gym-exercise-row', { hasText: lift }).first()
        .getByRole('button', { name: /Log your sets/ })).toBeVisible()
    }
    await expect(day.locator('.gym-exercise-row', { hasText: 'Mountain Climbers' }).first()
      .getByRole('button', { name: /Log your sets/ })).toHaveCount(0)
  })
})
