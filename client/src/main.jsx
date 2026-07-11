import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { HelmetProvider } from 'react-helmet-async'
import { LazyMotion, domAnimation, MotionConfig } from 'framer-motion'
import App from './App'
import { AuthProvider } from './providers/AuthContext'
import { ThemeProvider } from './providers/ThemeProvider'
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client'
import { queryClient, idbPersister } from './queryClient'
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

// Lazy-load Sentry ONLY when a real DSN is configured. A top-level static import
// would pull the whole SDK (~100KB+) into the entry chunk and block first paint
// even for users with no Sentry. The dynamic import makes it a separate async
// chunk that's never fetched unless a DSN is set. Replay is errors-only (no
// always-on session recording).
const SENTRY_DSN = import.meta.env.VITE_SENTRY_DSN
if (SENTRY_DSN && !SENTRY_DSN.includes('sentry.example.com')) {
  import('@sentry/react').then((Sentry) => {
    Sentry.init({
      dsn: SENTRY_DSN,
      integrations: [
        Sentry.browserTracingIntegration(),
        Sentry.replayIntegration({ maskAllText: true, blockAllMedia: true }),
      ],
      tracesSampleRate: 0.1,
      replaysSessionSampleRate: 0,
      replaysOnErrorSampleRate: 1.0,
    })
  })
}

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

ReactDOM.createRoot(document.getElementById('root')).render(
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
