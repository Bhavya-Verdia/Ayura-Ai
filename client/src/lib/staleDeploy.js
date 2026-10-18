/* Recovery for a tab that outlived a deploy.
 *
 * Every deploy renames each hashed chunk, and the old ones are gone from the
 * server. A tab opened before it keeps the old entry chunk, so its next lazy
 * route asks for a file that no longer exists. Each browser words the failure
 * differently, and none of the wording means anything to a user. Before this
 * it reached the ErrorBoundary, whose Try Again re-rendered the same
 * React.lazy — which caches its rejected import and threw again, every time.
 *
 * The fix is to load the new build: one reload, guarded so a chunk that is
 * genuinely missing from the new build too cannot reload forever. Where
 * sessionStorage is unavailable the guard cannot hold across a reload, so we
 * do not reload at all, and the boundary offers the reload as a button.
 */

const GUARD_KEY = 'ayura_stale_deploy_reload_at'
const GUARD_MS = 30_000

const CHUNK_ERROR = new RegExp([
  'Failed to fetch dynamically imported module',   // Chromium
  'Importing a module script failed',              // Safari
  'error loading dynamically imported module',     // Firefox
  'Unable to preload CSS',                         // Vite's CSS preload
].join('|'), 'i')

// Set once a reload is under way. After preventDefault, Vite resolves the
// import to undefined, and React.lazy throws "reading 'default'" from it while
// the page unloads — the boundary must neither paint nor report that.
let reloading = false

export function isReloadingForDeploy() {
  return reloading
}

export function isChunkLoadError(error) {
  const message = typeof error === 'string' ? error : error?.message
  return typeof message === 'string' && CHUNK_ERROR.test(message)
}

/**
 * Reload into the new build. Returns false when the guard says not to: we
 * already reloaded for this a moment ago, so the chunk is missing from the
 * current build as well — a broken deploy, not a stale tab. The caller then
 * shows the ErrorBoundary, which is the one place this gets reported.
 */
export function reloadForNewDeploy() {
  try {
    const last = Number(window.sessionStorage.getItem(GUARD_KEY)) || 0
    if (Date.now() - last < GUARD_MS) return false
    window.sessionStorage.setItem(GUARD_KEY, String(Date.now()))
  } catch {
    return false
  }
  reloading = true
  window.location.reload()
  return true
}

export function installStaleDeployRecovery() {
  // Vite dispatches this for a failed dynamic import and for its preloads.
  // preventDefault stops Vite rethrowing, so a reload is not raced by the
  // ErrorBoundary painting "Something went wrong" over the page first. When
  // the guard refuses, the error carries on to the boundary.
  window.addEventListener('vite:preloadError', (event) => {
    if (reloadForNewDeploy()) event.preventDefault()
  })
}
