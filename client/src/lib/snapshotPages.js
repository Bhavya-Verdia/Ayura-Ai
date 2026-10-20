/* The two routes served as prerendered HTML (scripts/prerender.mjs), as lazy
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

export const Landing = preloadable(() => import('../pages/Landing'))
export const DoshaTest = preloadable(() => import('../pages/DoshaTest'))
