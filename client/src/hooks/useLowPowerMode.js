import { useEffect, useState } from 'react'

// 900px matches MainLayout's isMobile breakpoint so the stripped-down
// background and the mobile layout switch at the same width (no dead zone
// where you'd get the desktop sidebar with the low-power background).
const QUERY = '(max-width: 900px), (pointer: coarse), (prefers-reduced-motion: reduce)'

/**
 * True on small/touch screens or when the user prefers reduced motion.
 *
 * Used to skip or shrink expensive always-on decorative effects (full-screen
 * SVG noise, dozens of animated motion paths, large blurred gradient fields,
 * hundreds of animated particles) that saturate the main thread / GPU on mobile
 * and cause the page to hang.
 *
 * MUST initialise synchronously (lazy useState, not useEffect): mount-time
 * consumers — e.g. MotionConfig gating entrance animations that START on the
 * first frame — would otherwise see one `false` render and kick off the very
 * work this hook exists to prevent. Prerender-safe: the prerenderer runs a
 * desktop-viewport Chromium, so matchMedia correctly reports false there and
 * the captured HTML keeps the full desktop treatment.
 */
export default function useLowPowerMode() {
  const [low, setLow] = useState(
    () => typeof window !== 'undefined' && !!window.matchMedia && window.matchMedia(QUERY).matches
  )

  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return
    const mq = window.matchMedia(QUERY)
    const update = () => setLow(mq.matches)
    update()
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, [])

  return low
}
