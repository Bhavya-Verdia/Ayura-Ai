import { test, expect } from '@playwright/test'
import { readFileSync } from 'node:fs'

// Workout mode, the way it is used: open the day, start, tick sets as they are
// done, rest between them, and the exercise is logged when it is finished —
// not at the end — so a closed tab costs at most the exercise in progress.
const BASE = JSON.parse(readFileSync(new URL('./fixtures/gym-plan.json', import.meta.url)))
const WEEK1 = BASE.four_week_plan[0]
const GYM_PLAN = { ...BASE, generated_at: new Date().toISOString(),
  four_week_plan: [WEEK1, { ...WEEK1, week: 2, theme: 'Volume Build' }] }

const PROFILE = {
  id: 'e2e-user', name: 'E2E Tester', email: 'e2e@ayura.test',
  onboarding_complete: true, dominant_dosha: 'Vata', is_admin: false,
}

async function mockApi(page, store, adjustments = { exercises: {}, notices: [], stop: null }) {
  await page.route((url) => url.pathname.startsWith('/api/'), (route) => {
    const req = route.request()
    const p = new URL(req.url()).pathname
    if (p.startsWith('/api/profile/me')) return route.fulfill({ json: PROFILE })
    if (p.startsWith('/api/plans/history')) {
      return route.fulfill({ json: { items: [{ plan_type: 'gym', plan_data: { gym_plan: GYM_PLAN }, created_at: GYM_PLAN.generated_at }] } })
    }
    if (p.startsWith('/api/workouts/logs')) {
      if (req.method() === 'POST') { store.logs.push(req.postDataJSON()); return route.fulfill({ json: { ok: true } }) }
      return route.fulfill({ json: { logs: [] } })
    }
    if (p.startsWith('/api/workouts/adjustments')) return route.fulfill({ json: { week: 2, based_on_week: 1, ...adjustments } })
    if (p.startsWith('/api/workouts/checkins')) return route.fulfill({ json: { checkins: [] } })
    if (p.startsWith('/api/practice/session')) { store.sessions.push(req.postDataJSON()); return route.fulfill({ json: { id: 's' } }) }
    return route.fulfill({ json: {} })
  })
}

async function startMonday(page, week = 1) {
  await page.goto('/dashboard')
  await page.locator('.dash-plan-card', { hasText: 'Fitness & Gym' }).getByRole('button', { name: /View Plan/ }).click()
  if (week > 1) await page.getByRole('button', { name: new RegExp(`Week ${week}`) }).click()
  await page.getByRole('button', { name: /Monday/ }).first().click()
  await page.getByRole('button', { name: 'Start workout' }).click()
  return page.getByRole('dialog', { name: 'Workout' })
}

test.describe('gym workout mode (mocked API)', () => {
  test('sets are ticked, rested between, and logged as each exercise ends', async ({ page }) => {
    const store = { logs: [], sessions: [] }
    await mockApi(page, store)
    const dlg = await startMonday(page)

    await expect(dlg.getByRole('heading', { name: 'Warm up' })).toBeVisible()
    await dlg.getByRole('button', { name: 'Next' }).click()

    await expect(dlg.getByRole('heading', { name: 'Barbell Squat' })).toBeVisible()
    await expect(dlg.getByText('Exercise 1 of 5')).toBeVisible()
    await dlg.getByLabel('Set 1 kg').fill('100')
    await dlg.getByLabel('Set 1 reps').fill('5')
    await dlg.getByRole('button', { name: 'Mark set 1 done' }).click()
    // 180 s rest, which can be cut short.
    await expect(dlg.getByRole('timer')).toContainText('2:5')
    await dlg.getByRole('button', { name: 'Skip rest' }).click()
    // The weight carries to the next set; an empty reps box is the plan's top.
    await expect(dlg.getByLabel('Set 2 kg')).toHaveValue('100')
    await dlg.getByRole('button', { name: 'Mark set 2 done' }).click()
    await dlg.getByRole('button', { name: 'Skip rest' }).click()
    await dlg.getByRole('radio', { name: 'Very hard' }).click()
    await dlg.getByRole('button', { name: 'Finish with 2 sets' }).click()

    await expect.poll(() => store.logs.length).toBe(1)
    expect(store.logs[0]).toEqual({ plan_id: GYM_PLAN.plan_id, week: 1, day: 1, exercise_id: 'barbell_squat',
      sets: [{ kg: 100, reps: 5 }, { kg: 100, reps: 5 }], effort: 'hard' })

    for (let i = 0; i < 3; i++) await dlg.getByRole('button', { name: 'Skip exercise' }).click()
    // Conditioning is timed, not logged.
    await expect(dlg.getByRole('heading', { name: 'Mountain Climbers' })).toBeVisible()
    await dlg.getByRole('button', { name: 'Next' }).click()
    await expect(dlg.getByRole('heading', { name: 'Cool down' })).toBeVisible()
    await dlg.getByRole('button', { name: 'Finish workout' }).click()

    await expect(dlg.getByText('1 of 5 exercises logged')).toBeVisible()
    await expect.poll(() => store.sessions.length).toBe(1)
    expect(store.sessions[0]).toMatchObject({ feature: 'gym', week: 1, day: 1, completed: true })
    await dlg.getByRole('button', { name: 'Back to plan' }).click()
    // The plan shows what the session logged.
    await expect(page.locator('.gym-exercise-row', { hasText: 'Barbell Squat' }).first()
      .getByText('Logged: 100×5, 100×5')).toBeVisible()
  })

  test("this week's adjusted weight is the starting weight", async ({ page }) => {
    await mockApi(page, { logs: [], sessions: [] }, { notices: [], stop: null, exercises: {
      barbell_squat: { direction: 'up', load_kg: 102.5, text: '102.5 kg', reason: 'Last week: easy.' } } })
    const dlg = await startMonday(page, 2)
    await dlg.getByRole('button', { name: 'Next' }).click()
    await expect(dlg.getByText('This week for you: 102.5 kg')).toBeVisible()
    await expect(dlg.getByLabel('Set 1 kg')).toHaveValue('102.5')
  })

  test('intervals run as rounds of hard and easy, not one countdown', async ({ page }) => {
    await page.clock.install()
    await mockApi(page, { logs: [], sessions: [] })
    const dlg = await startMonday(page)
    await dlg.getByRole('button', { name: 'Next' }).click()
    for (let i = 0; i < 4; i++) await dlg.getByRole('button', { name: 'Skip exercise' }).click()
    await expect(dlg.getByRole('heading', { name: 'Mountain Climbers' })).toBeVisible()
    const timer = dlg.getByRole('timer')
    await expect(timer).toContainText('Round 1 of 4 · Hard')
    await expect(timer).toContainText('0:30')
    await dlg.getByRole('button', { name: 'Start' }).click()
    await page.clock.runFor(31_000)
    await expect(timer).toContainText('Round 1 of 4 · Easy')
    await page.clock.runFor(31_000)
    await expect(timer).toContainText('Round 2 of 4 · Hard')
  })

  test('a reported warning sign withholds workout mode', async ({ page }) => {
    await mockApi(page, { logs: [], sessions: [] }, { exercises: {}, notices: [],
      stop: 'You reported chest pain or pressure last week. Stop training and see a doctor.' })
    await page.goto('/dashboard')
    await page.locator('.dash-plan-card', { hasText: 'Fitness & Gym' }).getByRole('button', { name: /View Plan/ }).click()
    await page.getByRole('button', { name: /Week 2/ }).click()
    await page.getByRole('button', { name: /Monday/ }).first().click()
    await expect(page.getByRole('button', { name: 'Start workout' })).toHaveCount(0)
    await expect(page.getByText(/Workout mode is paused/)).toBeVisible()
  })
})
