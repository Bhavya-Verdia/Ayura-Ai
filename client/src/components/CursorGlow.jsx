import { useEffect, useRef } from 'react'

/**
 * CursorGlow — a soft light that trails the cursor.
 *
 * Perf: instead of animating a full-viewport gradient's *position* on every
 * mousemove (a full-screen repaint per frame — the old approach), we translate a
 * single fixed element with `transform` (compositor-only, no layout/paint) and
 * coalesce updates through requestAnimationFrame.
 *
 * Cross-platform: only mounts the listener on fine-pointer + hover devices and
 * bails under prefers-reduced-motion, so touch devices pay nothing.
 */
export default function CursorGlow() {
  const ref = useRef(null)

  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return
    const fine = window.matchMedia('(hover: hover) and (pointer: fine)')
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)')
    if (!fine.matches || reduce.matches) return

    let raf = 0
    let x = window.innerWidth / 2
    let y = window.innerHeight / 2

    const apply = () => {
      raf = 0
      const el = ref.current
      if (el) el.style.transform = `translate3d(${x - 300}px, ${y - 300}px, 0)`
    }
    const onMove = (e) => {
      x = e.clientX
      y = e.clientY
      if (!raf) raf = requestAnimationFrame(apply)
    }

    window.addEventListener('mousemove', onMove, { passive: true })
    return () => {
      window.removeEventListener('mousemove', onMove)
      if (raf) cancelAnimationFrame(raf)
    }
  }, [])

  return <div ref={ref} className="cursor-glow" aria-hidden="true" />
}
