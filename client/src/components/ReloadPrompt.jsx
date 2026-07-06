import { useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { useRegisterSW } from 'virtual:pwa-register/react'
import { toast } from 'sonner'

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

  const {
    offlineReady: [offlineReady, setOfflineReady],
    needRefresh: [needRefresh],
    updateServiceWorker,
  } = useRegisterSW({
    onRegisteredSW(_url, registration) {
      if (registration) {
        setInterval(() => registration.update().catch(() => {}), SW_CHECK_INTERVAL_MS)
      }
    },
    onRegisterError(error) {
      console.error('SW registration error', error)
    },
  })

  useEffect(() => {
    if (offlineReady) {
      toast.success('App is ready to work offline.')
      setOfflineReady(false)
    }
  }, [offlineReady, setOfflineReady])

  // Typing means in-progress form state — never insta-reload over it.
  const hasTypedRef = useRef(false)
  useEffect(() => {
    const mark = () => { hasTypedRef.current = true }
    window.addEventListener('keydown', mark, { once: true })
    return () => window.removeEventListener('keydown', mark)
  }, [])

  // Safe moment #0: the update is discovered moments after OPENING the app
  // (the SW checks for a new version on registration, so a deploy is found
  // within seconds of a fresh visit). The user just arrived and hasn't typed
  // anything — reload right away so opening the site always lands on the
  // latest version, no interaction required.
  useEffect(() => {
    if (needRefresh && !hasTypedRef.current && performance.now() < 30_000) {
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
