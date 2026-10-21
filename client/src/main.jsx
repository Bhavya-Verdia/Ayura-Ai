import React from 'react'
import ReactDOM from 'react-dom/client'
import { Landing, DoshaTest, Login, Register, hydration } from './lib/snapshotPages'
import { isReturningUser } from './lib/sessionHint'
import { BrowserRouter } from 'react-router-dom'
import { HelmetProvider } from 'react-helmet-async'
import { LazyMotion, domAnimation, MotionConfig } from 'framer-motion'
import App from './App'
import { AuthProvider } from './providers/AuthContext'
import { ThemeProvider } from './providers/ThemeProvider'
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client'
import { queryClient, idbPersister } from './queryClient'
import { initAnalytics } from './lib/analytics'
import { initErrorReporting } from './lib/errorReporting'
import { installStaleDeployRecovery } from './lib/staleDeploy'
// Self-hosted fonts (was Google Fonts): same-origin woff2 discovered with the
// main CSS instead of a late 2-domain chain (googleapis CSS → gstatic font) —
// the webfont repaint was the mobile LCP bottleneck. Latin subsets only are
// fetched (unicode-range). font-display: swap comes with fontsource.
// Manrope ships as ONE variable woff2 (wght 200-800, ~25 kB) instead of five
// static weight files (~70 kB across 5 requests) — same glyphs, smaller critical path.
import '@fontsource-variable/manrope/wght.css'
import '@fontsource-variable/fraunces/opsz.css'
import '@fontsource-variable/fraunces/opsz-italic.css'
import './index.css'
import './i18n'

// Silence non-error console output in production so internal logs don't leak to
// the browser console. console.error is kept (Sentry captures it; it aids triage).
// Done at runtime because Vite 8 / rolldown doesn't expose a build-time console drop.
if (import.meta.env.PROD) {
  const noop = () => {}
  console.log = noop
  console.debug = noop
  console.info = noop
  console.warn = noop
}

// Sentry: lazy and DSN-gated, see lib/errorReporting.js.
initErrorReporting()

// A deploy replaces every hashed chunk, so a tab opened before it fails on the
// next lazy route. Reload once into the new build; see lib/staleDeploy.js.
installStaleDeployRecovery()

// Product analytics. Also lazy + key-gated (see lib/analytics.js for the privacy
// contract — autocapture and session recording are off because this UI displays
// health data). Kicked off here so the SDK fetch overlaps app render rather than
// waiting for the first route effect.
initAnalytics()

// LazyMotion + the `m` component (used app-wide instead of `motion`) ships only
// the `domAnimation` feature set and lets Rollup tree-shake out the heavier
// layout/drag projection code that the full `motion` proxy would force-bundle.
//
// reducedMotion: "user" honors the OS reduce-motion setting (framer uses JS
// transforms, which the CSS reduced-motion reset can't stop).
//
// HISTORY: this was briefly `'always'` on low-power devices to fix a "whole
// page blurred" incident on phones. The actual culprit was the FULL-PAGE route
// transition (PageWrapper animating filter:blur + transform on a viewport-sized
// layer — phone GPUs rasterize huge layers at capped resolution). PageWrapper
// keeps its cheap opacity-only variant on low power, which addresses that
// directly; small per-component entrances rasterize at native resolution and
// are safe, so movement stays enabled on mobile.
// eslint-disable-next-line react-refresh/only-export-components -- entry file, not hot-reloaded
function MotionRoot({ children }) {
  return (
    <LazyMotion features={domAnimation}>
      <MotionConfig reducedMotion="user">
        {children}
      </MotionConfig>
    </LazyMotion>
  )
}

const tree = (
  <React.StrictMode>
    <HelmetProvider>
      <BrowserRouter>
        <PersistQueryClientProvider client={queryClient} persistOptions={{ persister: idbPersister, maxAge: 1000 * 60 * 60 * 24 * 7 }}>
          <AuthProvider>
            <ThemeProvider>
              <MotionRoot>
                <App />
              </MotionRoot>
            </ThemeProvider>
          </AuthProvider>
        </PersistQueryClientProvider>
      </BrowserRouter>
    </HelmetProvider>
  </React.StrictMode>
)

// "/" and "/dosha-test" arrive as prerendered HTML (scripts/prerender.mjs).
// createRoot threw that DOM away and drew the page again once every chunk had
// loaded, so the hero a visitor was already reading was painted twice and the
// LCP was the second paint: 92% of a 5.7s mobile LCP was that redraw.
// hydrateRoot adopts the existing DOM.
//
// For either theme. The snapshot is captured dark, so nothing in it may render
// differently by theme: VitalBackground's colours are CSS keyed on data-theme,
// and the landing theme button reads useRenderedTheme(), which matches the
// snapshot during hydration and then updates. Hydration does not patch
// attributes, so a theme-dependent attribute anywhere on these two pages would
// keep its dark value for a light-theme visitor.

// The route's chunk is loaded before hydrating. Until React.lazy has it, the
// page is an unhydrated region, and React treats that region as reading every
// context above it: any provider update meanwhile (the query cache finishing
// its restore from IndexedDB) makes it give up and draw the page again. The
// snapshot is already on screen, so waiting costs no paint, and the page was
// not interactive before this chunk arrived anyway. See lib/snapshotPages.js.
const SNAPSHOT_ROUTES = {
  '/': Landing.preload,
  '/dosha-test': DoshaTest.preload,
  '/login': Login.preload,
  '/register': Register.preload,
}
// For a browser that has been signed in, PublicRoute's first render is the
// session check's loading screen (and then, usually, a redirect), which no
// snapshot of the form can match. Those visitors get the page drawn as before.
const SIGNED_OUT_ONLY = new Set(['/login', '/register'])

const container = document.getElementById('root')
const path = window.location.pathname
const route = SIGNED_OUT_ONLY.has(path) && isReturningUser() ? null : SNAPSHOT_ROUTES[path]
if (route && container.hasChildNodes()) {
  route()
    .catch(() => {})
    .then(() => {
      hydration.active = true
      ReactDOM.hydrateRoot(container, tree, {
        onRecoverableError: (error) => console.error('[hydrate]', error),
      })
    })
} else {
  ReactDOM.createRoot(container).render(tree)
}
