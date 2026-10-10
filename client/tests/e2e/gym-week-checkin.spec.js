import { test, expect } from '@playwright/test'
import { readFileSync } from 'node:fs'

// The week check-in and the weights it and the log set for the next week,
// reached the way a user reaches them: Dashboard, View Plan, a week tab. The
// adjustment rule itself is tested on the server (test_gym_week_adjust.py);
// this holds the page to what the server says.
//
// The fixture is real engine output for week one; week two is the same week
// renumbered, which is what the block's structure is — only the loads move.
const BASE = JSON.parse(readFileSync(new URL('./fixtures/gym-plan.json', import.meta.url)))
const WEEK1 = BASE.four_week_plan[0]
const GYM_PLAN = { ...BASE, four_week_plan: [WEEK1, { ...WEEK1, week: 2, theme: 'Volume Build' }] }

const PROFILE = {
  id: 'e2e-user', name: 'E2E Tester', email: 'e2e@ayura.test',
  onboarding_complete: true, dominant_dosha: 'Vata', is_admin: false,
}

const ADJUSTMENTS = {
  week: 2, based_on_week: 1, stop: null,
  notices: ['Last week felt too hard, so this week holds every weight where it was.'],
  exercises: {
    barbell_squat: {
      direction: 'hold', load_kg: 100, text: '100 kg',
      reason: 'Last week: 100×5, 100×4 — felt very hard; held this week because of your check-in.',
    },
  },
}

async function mockApi(page, store) {
  await page.route((url) => url.pathname.startsWith('/api/'), (route) => {
    const req = route.request()
    const url = new URL(req.url())
    if (url.pathname.startsWith('/api/profile/me')) return route.fulfill({ json: PROFILE })
    if (url.pathname.startsWith('/api/plans/history')) {
      return route.fulfill({
        json: { items: [{ plan_type: 'gym', plan_data: { gym_plan: GYM_PLAN }, created_at: new Date().toISOString() }] },
      })
    }
    if (url.pathname.startsWith('/api/workouts/checkins')) {
      if (req.method() === 'POST') {
        const body = req.postDataJSON()
        store.checkins.push(body)
        return route.fulfill({ json: { id: 'x', injuries_added: ['knee'], rebuild_recommended: true } })
      }
      return route.fulfill({ json: { checkins: [] } })
    }
    if (url.pathname.startsWith('/api/workouts/adjustments')) {
      store.adjustmentWeeks.push(url.searchParams.get('week'))
      return route.fulfill({ json: ADJUSTMENTS })
    }
    if (url.pathname.startsWith('/api/workouts/logs')) return route.fulfill({ json: { logs: [] } })
    if (url.pathname.startsWith('/api/preferences/gym')) return route.fulfill({ json: { is_set: true, preferences: {} } })
    if (url.pathname === '/api/plans/gym' && req.method() === 'POST') {
      store.regenerated.push(req.postDataJSON())
      return route.fulfill({ json: { gym_plan: GYM_PLAN } })
    }
    return route.fulfill({ json: {} })
  })
}

async function openPlan(page) {
  await page.goto('/dashboard')
  await page.locator('.dash-plan-card', { hasText: 'Fitness & Gym' })
    .getByRole('button', { name: /View Plan/ }).click()
}

test.describe('gym week check-in (mocked API)', () => {
  test('a check-in reporting pain is saved, and offers to rebuild the plan', async ({ page }) => {
    const store = { checkins: [], adjustmentWeeks: [], regenerated: [] }
    await mockApi(page, store)
    await openPlan(page)

    await page.getByRole('button', { name: 'Check in' }).click()
    const form = page.getByRole('group', { name: 'Week 1 check-in' })
    await form.getByRole('radio', { name: 'Too hard' }).click()
    await form.getByRole('button', { name: 'Knee' }).click()
    await form.getByLabel(/Add to my injuries/).check()
    await form.getByRole('button', { name: 'Save' }).click()

    expect(store.checkins).toEqual([{
      plan_id: GYM_PLAN.plan_id, week: 1, feeling: 'too_hard', pain_areas: ['knee'],
      unwell: false, red_flags: [], add_to_injuries: true,
    }])
    await expect(page.getByText('Week 1 checked in')).toBeVisible()
    await page.getByRole('button', { name: /Rebuild my plan around it/ }).click()
    await expect.poll(() => store.regenerated.length).toBe(1)
    expect(store.regenerated[0]).toEqual({ force_regenerate: true })
  })

  test('a red flag is answered with a doctor, before saving', async ({ page }) => {
    await mockApi(page, { checkins: [], adjustmentWeeks: [], regenerated: [] })
    await openPlan(page)
    await page.getByRole('button', { name: 'Check in' }).click()
    await page.getByRole('button', { name: 'Chest pain or pressure' }).click()
    await expect(page.getByRole('alert')).toContainText('see a doctor')
  })

  test('week two shows the weight set from week one, and why', async ({ page }) => {
    const store = { checkins: [], adjustmentWeeks: [], regenerated: [] }
    await mockApi(page, store)
    await openPlan(page)
    // Week one has nothing before it to adjust from.
    expect(store.adjustmentWeeks).toEqual([])

    await page.getByRole('button', { name: /Week 2/ }).click()
    await expect(page.getByText(ADJUSTMENTS.notices[0])).toBeVisible()
    await page.getByRole('button', { name: /Monday/ }).first().click()
    const squat = page.locator('.gym-exercise-row', { hasText: 'Barbell Squat' }).first()
    await expect(squat.locator('.gym-adjusted')).toContainText('This week for you: 100 kg')
    await expect(squat.locator('.gym-adjusted')).toContainText('felt very hard')
    expect(store.adjustmentWeeks).toContain('2')
  })
})
