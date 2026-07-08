import { useEffect, useState } from 'react'

// Mobile gets the full desktop visual treatment (per product decision:
// identical UI/background/colors on every screen size), so the only thing
// that strips the decorative layers now is an explicit OS-level
// "reduce motion" accessibility preference.
const QUERY = '(prefers-reduced-motion: reduce)'

/**
 * True only when the user prefers reduced motion.
 *
 * Consumers use this to swap the always-on decorative effects (animated
 * motion paths, blurred gradient fields, particles, ambient canvases) for
 * static equivalents — an accessibility fallback, no longer a mobile tier.
 *
 * MUST initialise synchronously (lazy useState, not useEffect): mount-time
 * consumers — e.g. MotionConfig gating entrance animations that START on the
 * first frame — would otherwise see one `false` render and kick off the very
 * work this hook exists to prevent.
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
