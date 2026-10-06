import { test, expect } from '@playwright/test'
import { readFileSync } from 'node:fs'

// After a month: the block is announced as over, says what it came to, and
// starts the next one; the long history shows every block; intermediate
// programming is offered — and only applied — when the server says so.
const BASE = JSON.parse(readFileSync(new URL('./fixtures/gym-plan.json', import.meta.url)))
const daysAgo = (n) => new Date(Date.now() - n * 864e5).toISOString()

const PROFILE = {
  id: 'e2e-user', name: 'E2E Tester', email: 'e2e@ayura.test',
  onboarding_complete: true, dominant_dosha: 'Vata', is_admin: false,
}

const SUMMARY = {
  block: 1, sessions_logged: 10, sessions_planned: 12, adherence: 0.83, progress: true,
  exercises_measured: 4, progressed: [{ exercise: 'Barbell Squat', change_percent: 9 }],
}

const BLOCKS = {
  consecutive: 3,
  blocks: [1, 2, 3].map(i => ({
    plan_id: `g${i}`, sessions_logged: 9 + i, sessions_planned: 12, progress: true, finished: true,
    progressed: [], best_lifts: { barbell_squat: { name: 'Barbell Squat', one_rm: 80 + i * 5 } },
  })),
  level_up: {
    to: 'intermediate', blocks: 3, gains: [{ exercise: 'Barbell Squat', change_percent: 12 }],
    reason: 'You have finished 3 blocks in a row and your lifts went up across them.',
  },
}

async function mockApi(page, plan, store, blocks = BLOCKS) {
  await page.route((url) => url.pathname.startsWith('/api/'), (route) => {
    const req = route.request()
    const url = new URL(req.url())
    const p = url.pathname
    if (p.startsWith('/api/profile/me')) return route.fulfill({ json: PROFILE })
    if (p.startsWith('/api/plans/history')) {
      return route.fulfill({
        json: { items: [{ plan_type: 'gym', plan_data: { gym_plan: plan }, created_at: plan.generated_at }] },
      })
    }
    if (p.startsWith('/api/workouts/summary')) return route.fulfill({ json: SUMMARY })
    if (p.startsWith('/api/workouts/blocks')) return route.fulfill({ json: blocks })
    if (p.startsWith('/api/workouts/level-up')) {
      store.levelUp += 1
      return route.fulfill({ json: { fitness_level: 'intermediate' } })
    }
    if (p.startsWith('/api/workouts/logs')) return route.fulfill({ json: { logs: [] } })
    if (p.startsWith('/api/workouts/checkins')) return route.fulfill({ json: { checkins: [] } })
    if (p.startsWith('/api/preferences/gym')) return route.fulfill({ json: { is_set: true, preferences: {} } })
    if (p === '/api/plans/gym' && req.method() === 'POST') {
      store.regenerated += 1
      return route.fulfill({ json: { gym_plan: plan } })
    }
    return route.fulfill({ json: {} })
  })
}

async function openPlan(page) {
  await page.goto('/dashboard')
  await page.locator('.dash-plan-card', { hasText: 'Fitness & Gym' })
    .getByRole('button', { name: /View Plan/ }).click()
}

test.describe('gym blocks (mocked API)', () => {
  test('a month on, the block is announced as over and the next one starts', async ({ page }) => {
    const store = { regenerated: 0, levelUp: 0 }
    await mockApi(page, { ...BASE, generated_at: daysAgo(30) }, store)
    await openPlan(page)
    const card = page.locator('.gym-block-card.over', { hasText: 'Block 1 complete' })
    await expect(card).toContainText('10 of 12')
    await expect(card).toContainText('Barbell Squat +9%')
    await card.getByRole('button', { name: 'Start block 2' }).click()
    await expect.poll(() => store.regenerated).toBe(1)
  })

  test('a block in its first week is not announced as over', async ({ page }) => {
    await mockApi(page, { ...BASE, generated_at: daysAgo(3) }, { regenerated: 0, levelUp: 0 },
      { blocks: [], consecutive: 0, level_up: null })
    await openPlan(page)
    await expect(page.getByText(/Block 1 complete/)).toHaveCount(0)
    await expect(page.getByRole('heading', { name: 'Your blocks' })).toHaveCount(0)
  })

  test('history spans every block, and intermediate is offered, then applied on request', async ({ page }) => {
    const store = { regenerated: 0, levelUp: 0 }
    await mockApi(page, { ...BASE, generated_at: daysAgo(3) }, store)
    await openPlan(page)
    const history = page.locator('.gym-history')
    await expect(history.getByText('Block 3', { exact: false }).first()).toBeVisible()
    await expect(history).toContainText('85 kg → 90 kg → 95 kg')
    expect(store.levelUp).toBe(0)
    await history.getByRole('button', { name: /Move to intermediate/ }).click()
    await expect.poll(() => store.levelUp).toBe(1)
    await expect.poll(() => store.regenerated).toBe(1)
  })

  test('two months at intermediate are offered advanced, in the server\'s words', async ({ page }) => {
    const store = { regenerated: 0, levelUp: 0 }
    const offer = { to: 'advanced', from: 'intermediate', blocks: 2, gains: [],
      reason: 'You have finished 2 blocks in a row at intermediate and your lifts went up across them.' }
    await mockApi(page, { ...BASE, generated_at: daysAgo(3) }, store, { ...BLOCKS, level_up: offer })
    await openPlan(page)
    const history = page.locator('.gym-history')
    await expect(history.getByText('Ready for advanced programming')).toBeVisible()
    await expect(history).toContainText('at intermediate')
    await history.getByRole('button', { name: 'Move to advanced and rebuild my plan' }).click()
    await expect.poll(() => store.levelUp).toBe(1)
  })
})
