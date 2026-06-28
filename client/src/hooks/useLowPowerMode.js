import { useEffect, useState } from 'react'

/**
 * True on small/touch screens or when the user prefers reduced motion.
 *
 * Used to skip or shrink expensive always-on decorative effects (full-screen
 * SVG noise, dozens of animated motion paths, large blurred gradient fields,
 * hundreds of animated particles) that saturate the main thread / GPU on mobile
 * and cause the page to hang. SSR/prerender-safe: defaults to `false` so the
 * prerendered HTML keeps the full desktop treatment, then corrects on mount.
 */
export default function useLowPowerMode() {
  const [low, setLow] = useState(false)

  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return
    const mq = window.matchMedia(
      '(max-width: 820px), (pointer: coarse), (prefers-reduced-motion: reduce)'
    )
    const update = () => setLow(mq.matches)
    update()
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, [])

  return low
}
