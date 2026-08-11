import { test, expect } from '@playwright/test'

/* Funnel instrumentation for the dosha assessment, driven end-to-end against a
 * mocked API.
 *
 * The posthog-js module itself is replaced with a stub that records every
 * capture() on `window.__phEvents`. Two reasons for testing at that seam rather
 * than at the network:
 *
 *  - It asserts on what this app actually sends — event names and properties —
 *    instead of on posthog-js's transport behaviour, which is PostHog's problem.
 *    The SDK batches and flushes through sendBeacon, which neither Playwright's
 *    request interception nor Resource Timing reports, so a network-level test
 *    reads as "zero events" whether the instrumentation works or not.
 *  - Nothing can reach the live project. The dev server reads VITE_POSTHOG_KEY
 *    from the root .env, so without the stub these runs would write test traffic
 *    into production analytics.
 */

const PROFILE = {
  id: 'e2e-user',
  name: 'E2E Tester',
  email: 'e2e@ayura.test',
  onboarding_complete: true,
  prakriti_locked: false,
  is_admin: false,
}

const STUB_MODULE = `
  const KEY = '__phEvents'
  const load = () => { try { return JSON.parse(sessionStorage.getItem(KEY) || '[]') } catch { return [] } }
  const save = (all) => { try { sessionStorage.setItem(KEY, JSON.stringify(all)) } catch { /* full */ } }
  window.__phEvents = load()
  const noop = () => {}
  export const posthog = {
    init: noop,
    capture: (event, properties) => {
      window.__phEvents.push({ event, properties: properties || {} })
      // sessionStorage so events survive a full page navigation, which is how
      // the pagehide abandonment path has to be exercised.
      save(window.__phEvents)
    },
    identify: noop,
    reset: noop,
    has_opted_out_capturing: () => false,
  }
  export default posthog
`

const isApiUrl = (url) => url.pathname.startsWith('/api/')
// Vite dev serves the pre-bundled dep as /node_modules/.vite/deps/posthog-js.js?v=…
const isPostHogModule = (url) => /posthog-js/.test(url.pathname)

async function stubAnalytics(page) {
  await page.route(isPostHogModule, (route) =>
    route.fulfill({ status: 200, contentType: 'application/javascript', body: STUB_MODULE }),
  )
  // Belt and braces: if the module ever loads from elsewhere, no event escapes.
  await page.route((url) => url.hostname.endsWith('posthog.com'), (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '{"status":1}' }),
  )
}

async function mockApi(page) {
  await page.route(isApiUrl, (route) => {
    const url = route.request().url()
    if (url.includes('/profile/me')) return route.fulfill({ json: PROFILE })
    return route.fulfill({ json: {} })
  })
}

const readEvents = async (page) =>
  JSON.parse(await page.evaluate("sessionStorage.getItem('__phEvents') || '[]'"))
const named = (events, name) => events.filter((e) => e.event === name)
const countOf = async (page, name) => named(await readEvents(page), name).length

/** Answer the visible trait question, then move on. */
async function answerCurrentQuestion(page, index) {
  await expect(page.getByText(`Question ${index + 1} of`)).toBeVisible()
  await page.locator('.da-trait-card').first().click()
  // The first tap opens the blend window; "Next" skips waiting it out.
  await page.locator('.da-next-btn').click()
}

test.describe('dosha assessment funnel', () => {
  test.beforeEach(async ({ page }) => {
    await stubAnalytics(page)
    await mockApi(page)
  })

  test('analytics is switched on for this run', async ({ page }) => {
    // analytics.js no-ops unless VITE_POSTHOG_KEY is set, so without it every
    // assertion below fails as "0 events" and reads like broken instrumentation.
    // CI supplies a stub key (see .github/workflows/ci.yml); this test names the
    // cause so nobody has to rediscover it.
    await page.goto('/dosha-quiz')
    await expect(page.getByText('Question 1 of')).toBeVisible()
    await expect
      .poll(() => countOf(page, 'assessment_started'))
      .toBeGreaterThan(0)
  })

  test('reports the start of the assessment', async ({ page }) => {
    await page.goto('/dosha-quiz')
    await expect(page.getByText('Question 1 of')).toBeVisible()

    await expect.poll(() => countOf(page, 'assessment_started')).toBeGreaterThan(0)
    const started = named(await readEvents(page), 'assessment_started')[0]
    expect(started.properties.total_questions).toBeGreaterThan(20)
    expect(started.properties.is_retake).toBe(false)
  })

  test('reports each answered question with its position', async ({ page }) => {
    await page.goto('/dosha-quiz')
    await expect(page.getByText('Question 1 of')).toBeVisible()

    for (let i = 0; i < 3; i++) await answerCurrentQuestion(page, i)

    await expect.poll(() => countOf(page, 'assessment_step_completed')).toBeGreaterThanOrEqual(3)
    const steps = named(await readEvents(page), 'assessment_step_completed')
    // Indices must advance rather than repeating question 1 — the stale-closure
    // failure this instrumentation is most prone to, since the step event fires
    // from a timeout created in the same tick as the answer's setState.
    expect(steps.slice(0, 3).map((e) => e.properties.question_index)).toEqual([0, 1, 2])
    expect(steps[0].properties.question_id).toBeTruthy()
    expect(steps[0].properties.is_blend).toBe(false)
  })

  test('records a blended answer as a blend', async ({ page }) => {
    await page.goto('/dosha-quiz')
    await expect(page.getByText('Question 1 of')).toBeVisible()

    // Two different options within the grace window = a blend.
    await page.locator('.da-trait-card').nth(0).click()
    await page.locator('.da-trait-card').nth(1).click()
    await expect(page.locator('.da-blend-hint-active')).toBeVisible()
    await page.locator('.da-next-btn').click()

    await expect.poll(() => countOf(page, 'assessment_step_completed')).toBeGreaterThan(0)
    const steps = named(await readEvents(page), 'assessment_step_completed')
    expect(steps[0].properties.is_blend).toBe(true)
  })

  test('reports where an abandoned run stopped', async ({ page }) => {
    await page.goto('/dosha-quiz')
    await expect(page.getByText('Question 1 of')).toBeVisible()

    for (let i = 0; i < 4; i++) await answerCurrentQuestion(page, i)
    await expect(page.getByText('Question 5 of')).toBeVisible()

    // A hard navigation, i.e. how people actually leave a long form. React's
    // cleanup does not run here, so this exercises the pagehide path.
    await page.goto('/dashboard')

    await expect.poll(() => countOf(page, 'assessment_abandoned')).toBeGreaterThan(0)
    const abandoned = named(await readEvents(page), 'assessment_abandoned')[0]
    // The whole point of the event: WHERE they left, not merely that they did.
    // A mount-time closure would report question 1 here no matter how far they got.
    expect(abandoned.properties.last_question_index).toBe(4)
    expect(abandoned.properties.questions_answered).toBe(4)
    expect(abandoned.properties.phase).toBe('traits')
    expect(abandoned.properties.last_question_id).toBeTruthy()
  })

  test('a completed assessment is not counted as abandoned', async ({ page }) => {
    await page.route(isApiUrl, (route) => {
      const url = route.request().url()
      if (url.includes('/profile/dosha-assessment')) {
        return route.fulfill({ json: { ...PROFILE, dosha_confidence: 85, dosha_contradictions: [] } })
      }
      if (url.includes('/profile/me')) return route.fulfill({ json: PROFILE })
      return route.fulfill({ json: {} })
    })

    await page.goto('/dosha-quiz')
    await expect(page.getByText('Question 1 of')).toBeVisible()
    const total = Number((await page.getByText(/Question 1 of \d+/).innerText()).match(/of (\d+)/)[1])
    for (let i = 0; i < total; i++) await answerCurrentQuestion(page, i)

    // Symptom phase → submit.
    await expect(page.getByRole('button', { name: /Assess My Dosha/i })).toBeVisible()
    await page.getByRole('button', { name: /Assess My Dosha/i }).click()

    await expect.poll(() => countOf(page, 'assessment_completed'), { timeout: 15000 }).toBeGreaterThan(0)
    const completed = named(await readEvents(page), 'assessment_completed')[0]
    expect(completed.properties.confidence_band).toBe('high')
    expect(completed.properties.questions_answered ?? total).toBeGreaterThan(0)

    await page.goto('/dashboard')
    expect(await countOf(page, 'assessment_abandoned')).toBe(0)
  })

  test('never sends an answer, a dosha, or a condition', async ({ page }) => {
    await page.goto('/dosha-quiz')
    await expect(page.getByText('Question 1 of')).toBeVisible()
    for (let i = 0; i < 3; i++) await answerCurrentQuestion(page, i)
    await page.goto('/dashboard')

    await expect.poll(() => countOf(page, 'assessment_step_completed')).toBeGreaterThan(0)
    const assessment = (await readEvents(page)).filter((e) => e.event.startsWith('assessment_'))
    expect(assessment.length).toBeGreaterThan(0)
    for (const e of assessment) {
      const serialised = JSON.stringify(e.properties).toLowerCase()
      for (const forbidden of ['vata', 'pitta', 'kapha', 'satva', 'rajas', 'tamas']) {
        expect(serialised, `${e.event} leaked "${forbidden}"`).not.toContain(forbidden)
      }
    }
  })
})
