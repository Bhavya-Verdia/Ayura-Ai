import { useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { useRegisterSW } from 'virtual:pwa-register/react'

// Long-lived tabs never re-check for a new SW on their own; poll hourly so an
// update is discovered without requiring a full page navigation.
const SW_CHECK_INTERVAL_MS = 60 * 60 * 1000

// Hybrid auto-update: no "reload" prompt. When a new service worker is
// waiting, apply it (skipWaiting + reload) at the next SAFE moment —
// right after a fresh open (before the user has typed anything), the tab
// being hidden/backgrounded, or a route navigation — so the user never
// loses in-progress form/chat state to a surprise mid-view reload.
// If none of those happen, the browser still activates the new SW once all
// tabs close, so nobody is ever stuck on an old version.
export default function ReloadPrompt() {
  const location = useLocation()
  // Pathname at the moment the update was detected — a reload is only safe
  // once the user has navigated AWAY from the view they were on.
  const pendingSincePath = useRef(null)
  const registrationRef = useRef(null)

  const {
    offlineReady: [offlineReady, setOfflineReady],
    needRefresh: [needRefresh],
    updateServiceWorker,
  } = useRegisterSW({
    onRegisteredSW(_url, registration) {
      if (registration) {
        registrationRef.current = registration
        setInterval(() => registration.update().catch(() => {}), SW_CHECK_INTERVAL_MS)
      }
    },
    onRegisterError(error) {
      console.error('SW registration error', error)
    },
  })

  // Offline capability is silent by design: the toast fired on every FIRST
  // visit (SW install), covering the nav's Sign In/Get Started CTAs at the
  // exact moment a new visitor is forming an impression — and "works offline"
  // means nothing to someone who hasn't used the app yet.
  useEffect(() => {
    if (offlineReady) setOfflineReady(false)
  }, [offlineReady, setOfflineReady])

  // "Arrival": a fresh load OR the app coming back to the foreground —
  // mobile browsers keep tabs alive for days, so returning to the app is the
  // moment users expect to be on the latest version. On each arrival we
  // re-check for a new SW and open a short window in which an update applies
  // immediately (the user just got here, nothing is in progress yet).
  // Typing closes the window — never insta-reload over form state.
  const arrivedAtRef = useRef(performance.now())
  const typedSinceArrivalRef = useRef(false)
  // Mirror needRefresh into a ref so the mount-only visibility listener sees
  // the current value (an update found-but-deferred in a previous foreground
  // session applies the moment the user returns).
  const needRefreshRef = useRef(false)
  useEffect(() => { needRefreshRef.current = needRefresh }, [needRefresh])
  useEffect(() => {
    const markTyped = () => { typedSinceArrivalRef.current = true }
    const onVisible = () => {
      if (document.hidden) return
      arrivedAtRef.current = performance.now()
      typedSinceArrivalRef.current = false
      if (needRefreshRef.current) {
        updateServiceWorker(true)
        return
      }
      registrationRef.current?.update().catch(() => {})
    }
    window.addEventListener('keydown', markTyped)
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      window.removeEventListener('keydown', markTyped)
      document.removeEventListener('visibilitychange', onVisible)
    }
    // updateServiceWorker is stable (from useRegisterSW)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Safe moment #0: update discovered within the arrival window (fresh open
  // or foregrounding re-check above) and the user hasn't typed — apply right
  // away so opening or returning to the app always lands on the latest
  // version, no interaction required.
  useEffect(() => {
    if (
      needRefresh &&
      !typedSinceArrivalRef.current &&
      performance.now() - arrivedAtRef.current < 30_000
    ) {
      updateServiceWorker(true)
    }
  }, [needRefresh, updateServiceWorker])

  // Safe moment #1: tab hidden/backgrounded — reload happens out of sight.
  useEffect(() => {
    if (!needRefresh) return
    if (pendingSincePath.current === null) pendingSincePath.current = location.pathname
    const onVisibilityChange = () => {
      if (document.hidden) updateServiceWorker(true)
    }
    document.addEventListener('visibilitychange', onVisibilityChange)
    return () => document.removeEventListener('visibilitychange', onVisibilityChange)
    // location.pathname deliberately omitted: this effect only captures the
    // path at detection time; navigation is handled by the effect below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [needRefresh, updateServiceWorker])

  // Safe moment #2: route navigation — the user is leaving the current view
  // anyway, so a reload costs nothing. Old-build chunks for the target route
  // are served from the SW precache, so the pre-reload frame can't 404.
  useEffect(() => {
    if (!needRefresh || pendingSincePath.current === null) return
    if (location.pathname !== pendingSincePath.current) {
      updateServiceWorker(true)
    }
  }, [location.pathname, needRefresh, updateServiceWorker])

  return null // Renderless component, handles logic only
}
