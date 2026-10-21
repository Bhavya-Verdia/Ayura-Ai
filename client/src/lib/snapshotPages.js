/* The routes served as prerendered HTML (scripts/prerender.mjs), as lazy
 * components that main.jsx can load before it hydrates.
 *
 * React.lazy suspends at least once even when its module has already loaded,
 * because a promise only reports its value asynchronously. During hydration
 * that leaves the page an unhydrated region after the root commits, and any
 * context update landing in that gap (the session check answering, the query
 * cache restoring) makes React draw the page again over the snapshot. Once
 * `preload` has resolved, the factory below hands React a thenable that calls
 * back synchronously, so the page hydrates in the same pass as the root.
 */
import { lazy } from 'react'

function preloadable(factory) {
  let module = null
  let pending = null
  const preload = () => {
    pending ??= factory().then((m) => (module = m))
    return pending
  }
  const Component = lazy(() => (module ? { then: (resolve) => resolve(module) } : preload()))
  Component.preload = preload
  return Component
}

/* True while React is adopting a snapshot. The page is already on screen, so the
 * route entrance (fade from opacity 0 and a 16px rise) must not run: it faded the
 * whole page out and back in on every cold visit. PageWrapper reads it once and
 * clears it, so later navigations animate as before. */
export const hydration = { active: false }

export const Landing = preloadable(() => import('../pages/Landing'))
export const DoshaTest = preloadable(() => import('../pages/DoshaTest'))
export const Login = preloadable(() => import('../pages/Login'))
export const Register = preloadable(() => import('../pages/Register'))
