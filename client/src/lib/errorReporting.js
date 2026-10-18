/* Error reporting (Sentry).
 *
 * Lazy-load Sentry ONLY when a real DSN is configured. A top-level static import
 * would pull the whole SDK (~100KB+) into the entry chunk and block first paint
 * even for users with no Sentry. The dynamic import makes it a separate async
 * chunk that's never fetched unless a DSN is set. Replay is errors-only (no
 * always-on session recording).
 *
 * `window.__PRERENDER__` is set by scripts/prerender.mjs before any app script
 * runs. Loading Sentry during a snapshot would bake a modulepreload for its
 * 84 kB chunk into dist/index.html — making every landing visitor eagerly fetch
 * the SDK this dynamic import exists to defer — and would report the build
 * machine as a live session. See that script for the full note.
 *
 * PRIVACY: the same contract as lib/analytics.js. `reportError` context is
 * statuses, enums and server-written messages — never an answer the user gave.
 * A report marked `noReplay` also never attaches a session replay, because the
 * screens that send one (onboarding) are made of health answers, and a masked
 * replay still records which chip was selected.
 */

const DSN = import.meta.env.VITE_SENTRY_DSN

let sentryPromise = null

function enabled() {
  return Boolean(DSN) && !DSN.includes('sentry.example.com') && !window.__PRERENDER__
}

export function initErrorReporting() {
  if (sentryPromise || !enabled()) return sentryPromise
  sentryPromise = import('@sentry/react')
    .then((Sentry) => {
      Sentry.init({
        dsn: DSN,
        integrations: [
          Sentry.browserTracingIntegration(),
          Sentry.replayIntegration({
            maskAllText: true,
            blockAllMedia: true,
            beforeErrorSampling: (event) => event.tags?.no_replay !== 'true',
          }),
        ],
        tracesSampleRate: 0.1,
        replaysSessionSampleRate: 0,
        replaysOnErrorSampleRate: 1.0,
      })
      return Sentry
    })
    .catch(() => null)
  return sentryPromise
}

/**
 * Send one error to Sentry, if Sentry is configured. Never throws, never waits
 * the caller: a failure to report must not become a second failure on screen.
 *
 *   flow      short enum naming where it happened ('onboarding')
 *   extra     statuses and server messages only — see the privacy note above
 *   noReplay  true on any screen that displays health answers
 */
export function reportError(error, { flow, extra = {}, noReplay = false } = {}) {
  const ready = initErrorReporting()
  if (!ready) return
  ready.then((Sentry) => {
    if (!Sentry) return
    Sentry.withScope((scope) => {
      if (flow) scope.setTag('flow', flow)
      if (noReplay) scope.setTag('no_replay', 'true')
      scope.setExtras(extra)
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    })
  }).catch(() => {})
}
