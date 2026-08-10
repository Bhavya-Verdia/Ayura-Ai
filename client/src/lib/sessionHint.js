/* "Has this browser been signed in before?" — a non-sensitive boot hint.
 *
 * The auth cookies are HTTP-only by design, so JS cannot tell whether a session
 * exists until /profile/me answers. That answer is what gates rendering the app
 * shell, which means the shell's chunks (MainLayout, Dashboard) could not even
 * begin downloading until a network round-trip had completed — a serial
 * waterfall of profile → MainLayout → Dashboard before anything appeared.
 *
 * This flag lets a returning user's shell chunks be fetched IN PARALLEL with
 * that request. It is only ever a prefetch hint: nothing is rendered or trusted
 * because of it, and being wrong costs a warm cache entry, never access. Real
 * authorization stays entirely server-side.
 *
 * Deliberately NOT the user id, name, or anything about the account — a stale
 * "1" in localStorage must reveal nothing about who last used the device.
 */
const KEY = 'ayura_returning'

export function markReturningUser() {
  try {
    localStorage.setItem(KEY, '1')
  } catch {
    // Private mode / storage disabled — prefetching is an optimisation only.
  }
}

export function clearReturningUser() {
  try {
    localStorage.removeItem(KEY)
  } catch {
    // As above: nothing depends on this succeeding.
  }
}

export function isReturningUser() {
  try {
    return localStorage.getItem(KEY) === '1'
  } catch {
    return false
  }
}
