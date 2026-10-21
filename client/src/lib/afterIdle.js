/* Resolve once the page has loaded and the main thread is idle.
 *
 * The Sentry and PostHog SDKs are ~230 kB gzip between them. Fetched at boot,
 * they compete with the route chunk and the fonts for bandwidth, and with
 * hydration for the CPU, and on a mid-range phone that pushed the landing
 * page's first paint back by seconds. Neither SDK is needed before the page is
 * usable: events wait on the SDK promise, so nothing is dropped, only sent later.
 *
 * One shared promise, so both SDKs start in the same idle slot.
 */

let idle = null

export function afterIdle() {
  if (idle) return idle
  idle = new Promise((resolve) => {
    const whenIdle = () => {
      if ('requestIdleCallback' in window) window.requestIdleCallback(resolve, { timeout: 4000 })
      else setTimeout(resolve, 1500)
    }
    if (document.readyState === 'complete') whenIdle()
    else window.addEventListener('load', whenIdle, { once: true })
  })
  return idle
}
