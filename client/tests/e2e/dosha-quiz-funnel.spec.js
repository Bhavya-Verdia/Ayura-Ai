import { test, expect } from '@playwright/test'
import { TRAIT_QUESTIONS, MANASA_TRAIT_IDS } from '../../src/pages/doshaQuiz/questions.js'

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

// Question order is fixed (only the options are shuffled), so the index says
// which questions are the Manasa block.
const isManasa = (index) => MANASA_TRAIT_IDS.includes(TRAIT_QUESTIONS[index]?.id)

/** Answer the visible trait question, then wait until its card has gone.
 *
 * The counter above the card moves the moment the index does, while the old
 * card is still sliding out — so "Question N of" being visible does not mean
 * card N is. This helper used to tap "the first card" right then, which was the
 * outgoing one, and wait for a Next that the new card never showed: about one
 * full run in four. Waiting for the heading to change is what "card N is up"
 * means with AnimatePresence mode="wait", and it reads in any locale. */
async function answerCurrentQuestion(page, index) {
  await expect(page.getByText(`Question ${index + 1} of`)).toBeVisible()
  const heading = page.locator('h2.da-question')
  const answered = await heading.innerText()
  await page.locator('.da-trait-card').first().click()
  // Mind questions move on 220ms after a pick. The rest open a 2s blend window,
  // which "Next" skips; if a slow run outlasts it, the auto-advance has already
  // done the job and the Next is gone, so a missed click is not a failure.
  if (!isManasa(index)) await page.locator('.da-next-btn').click({ timeout: 1500 }).catch(() => {})
  await expect(heading).not.toHaveText(answered)
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

  test('a tap on the card that is sliding out does not skip the next question', async ({ page }) => {
    // The counter above the card updates the moment the index moves, while the
    // old card is still sliding out (AnimatePresence mode="wait", 300ms). A tap
    // on that outgoing card ran its stale handler — answered the old question
    // again and advanced a second time — so the next question was never shown.
    // Mind (Manasa) questions auto-advance 220ms after a pick, which puts the
    // whole window inside one quick double-tap. This is what made the funnel
    // test above fail about one run in four, at "Question 24 of".
    await page.goto('/dosha-quiz')
    await expect(page.getByText('Question 1 of')).toBeVisible()
    const total = Number((await page.getByText(/Question 1 of \d+/).innerText()).match(/of (\d+)/)[1])
    const firstManasa = total - 5          // the last five are the Manasa block
    for (let i = 0; i < firstManasa; i++) await answerCurrentQuestion(page, i)

    await expect(page.getByText(`Question ${firstManasa + 1} of`)).toBeVisible()
    const manasaQuestion = await page.locator('h2.da-question').innerText()
    await page.locator('.da-trait-card').first().click()
    await expect(page.getByText(`Question ${firstManasa + 2} of`)).toBeVisible()
    // Tap the outgoing card in the gap, as a quick finger does: a DOM click, so
    // Playwright does not wait for the slide to finish first.
    await page.evaluate(() => document.querySelector('.da-trait-card')?.click())

    await page.waitForTimeout(800)          // past the 220ms advance and the 300ms slide
    await expect(page.getByText(`Question ${firstManasa + 2} of`)).toBeVisible()
    await expect(page.locator('h2.da-question')).not.toHaveText(manasaQuestion)
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

/* Localisation of the assessment.
 *
 * The quiz was hardcoded English while Settings offers eight languages, so a
 * Hindi speaker answered 27 nuanced questions about digestion, pulse and
 * emotional regulation in a second language. For a self-report instrument that
 * is an accuracy problem, not a polish one: comprehension IS the measurement,
 * and the result drives all seven plan types.
 */
test.describe('dosha assessment localisation', () => {
  test.beforeEach(async ({ page }) => {
    await stubAnalytics(page)
    await mockApi(page)
    await page.addInitScript(() => localStorage.setItem('ayura_lang', 'hi'))
  })

  test('renders the questions in Hindi when Hindi is selected', async ({ page }) => {
    await page.goto('/dosha-quiz')
    await expect(page.getByText('Question 1 of')).toBeVisible()
    const heading = page.locator('.da-question')
    await expect(heading).toBeVisible()
    // Devanagari, and specifically not the English source string.
    await expect(heading).toHaveText(/[ऀ-ॿ]/)
    await expect(heading).not.toHaveText(/body frame/i)
  })

  test('option values are untouched by translation', async ({ page }) => {
    // Scoring keys on option *values*; only the copy is localised. If a
    // translation ever replaced a value, every Hindi user's constitution would
    // be computed from garbage — silently, since the UI would look fine.
    await page.goto('/dosha-quiz')
    await expect(page.locator('.da-trait-card').first()).toBeVisible()
    for (let i = 0; i < 3; i++) {
      await page.locator('.da-trait-card').first().click()
      await page.locator('.da-next-btn').click()
    }
    await expect.poll(() => countOf(page, 'assessment_step_completed')).toBeGreaterThanOrEqual(3)
    const steps = named(await readEvents(page), 'assessment_step_completed')
    // Question ids stay the English source ids regardless of display language.
    expect(steps.map((e) => e.properties.question_id)).toEqual(
      expect.arrayContaining(['body_frame', 'skin', 'digestion']),
    )
  })

  test('an untranslated language falls back to English rather than blanking', async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem('ayura_lang', 'fr'))
    await page.goto('/dosha-quiz')
    const heading = page.locator('.da-question')
    await expect(heading).toBeVisible()
    await expect(heading).not.toHaveText(/^\s*$/)
    await expect(heading).not.toHaveText(/quiz\.trait/)
  })
})
