/* Product analytics (PostHog).
 *
 * PRIVACY CONTRACT — read before adding any call site.
 * This is a health app. Dosha results, conditions, symptoms, medicines, chat
 * text, plan bodies and free-text input are SENSITIVE PERSONAL DATA under the
 * DPDP Act and must never leave the app as analytics. So the SDK is configured
 * to make leaking hard by default, not merely discouraged:
 *
 *   autocapture           off — autocapture sends the text of clicked elements,
 *                              which on this UI means condition names, symptom
 *                              chips and medicine titles.
 *   session recording     off — the screen itself shows health data.
 *   capture_pageview      off — we send the route path manually (below) so query
 *                              strings (reset tokens, verification tokens, ids)
 *                              are never transmitted.
 *   person_profiles       identified_only — no profile for anonymous visitors.
 *   respect_dnt           on  — Do Not Track browsers are not measured.
 *
 * Event properties must stay to counts, enums and booleans that you could show
 * a stranger. If you are about to pass a symptom, a dosha, a plan or anything a
 * user typed, don't — the funnel does not need it.
 *
 * Loaded lazily and only when a key is configured, mirroring the Sentry pattern
 * in main.jsx: a static import would put the SDK in the entry chunk and delay
 * first paint for everyone, including users with no analytics configured.
 */

const KEY = import.meta.env.VITE_POSTHOG_KEY
const HOST = import.meta.env.VITE_POSTHOG_HOST || 'https://eu.i.posthog.com'

// Resolves to the posthog module once loaded, or null when analytics is off.
// Every helper below awaits this, so call sites never branch on configuration.
let clientPromise = null
// The resolved client, kept alongside the promise so an event can be sent
// synchronously. See trackSync.
let client = null

function enabled() {
  // `window.__PRERENDER__` is set by scripts/prerender.mjs before any app script
  // runs. A build must not appear in the funnel as a real visit, and loading the
  // SDK during a snapshot bakes a modulepreload for its chunk into the static
  // HTML. See that script for the full note.
  if (typeof window !== 'undefined' && window.__PRERENDER__) return false
  return Boolean(KEY) && !String(KEY).startsWith('phc_your')
}

function load() {
  if (!enabled()) return Promise.resolve(null)
  if (!clientPromise) {
    clientPromise = import('posthog-js')
      .then(({ posthog }) => {
        posthog.init(KEY, {
          api_host: HOST,
          autocapture: false,
          disable_session_recording: true,
          capture_pageview: false,
          capture_pageleave: true,
          person_profiles: 'identified_only',
          respect_dnt: true,
        })
        client = posthog
        return posthog
      })
      .catch(() => null) // analytics must never break the app
  }
  return clientPromise
}

/** Start the SDK. Safe and free to call when no key is configured. */
export function initAnalytics() {
  return load()
}

/** Record a route view. Pass the route path only — never a full URL. */
export async function trackPageview(path) {
  const posthog = await load()
  posthog?.capture('$pageview', { $current_url: path })
}

/** Record a product event. See the privacy contract above on properties. */
export async function track(event, properties) {
  const posthog = await load()
  posthog?.capture(event, properties)
}

/** Record an event without awaiting, for use while the page is being torn down.
 *
 * `track` awaits the lazy import, and on `pagehide` that continuation never runs
 * — the page is gone before the microtask does. Anything reporting an exit has
 * to reach the SDK in the same tick. Returns false when the SDK isn't loaded
 * yet, so the caller can fall back to the async path.
 */
export function trackSync(event, properties) {
  if (!client) return false
  client.capture(event, properties)
  return true
}

/** Tie events to a stable user id after login. Never pass email or health data. */
export async function identifyUser(userId) {
  if (!userId) return
  const posthog = await load()
  posthog?.identify(String(userId))
}

/** Drop identity on logout so the next user on this device is a separate person. */
export async function resetAnalytics() {
  const posthog = await load()
  posthog?.reset()
}

/* Funnel event names, centralised so call sites can't drift into typos and so
 * the set stays reviewable in one place. These are the launch questions:
 * did they sign up, did they finish onboarding, did they get a plan, did they
 * come back. */
export const EVENTS = {
  SIGNED_UP: 'signed_up',
  LOGGED_IN: 'logged_in',
  ONBOARDING_STARTED: 'onboarding_started',
  ONBOARDING_COMPLETED: 'onboarding_completed',

  /* Dosha assessment funnel. This is the longest flow in the product (27
   * questions, auto-advancing, no save/resume) and every plan is generated from
   * its output, so it gets step-level granularity rather than just start/finish:
   * without the per-question event there is no way to see WHERE people leave.
   *
   * Note what is deliberately absent — no answers, no dominant dosha, no
   * constitution type, no symptom or condition ids. Those are the health data the
   * privacy contract above rules out. Question ids describe the instrument, not
   * the respondent, so they are safe; the answers to them are not. */
  ASSESSMENT_STARTED: 'assessment_started',
  ASSESSMENT_STEP_COMPLETED: 'assessment_step_completed',
  ASSESSMENT_PHASE_REACHED: 'assessment_phase_reached',
  ASSESSMENT_SUBMITTED: 'assessment_submitted',
  ASSESSMENT_COMPLETED: 'assessment_completed',
  ASSESSMENT_ABANDONED: 'assessment_abandoned',
  ASSESSMENT_RETAKE_STARTED: 'assessment_retake_started',
  PLAN_GENERATED: 'plan_generated',
  CHAT_MESSAGE_SENT: 'chat_message_sent',
  CHECKIN_SUBMITTED: 'checkin_submitted',
}
