import { useRef, useCallback } from 'react'
import { m, useMotionValue, useSpring, useMotionTemplate, useReducedMotion } from 'framer-motion'
import useLowPowerMode from '../hooks/useLowPowerMode'

/**
 * TiltCard — a 3D pointer-tilt wrapper with a cursor-following light glare.
 *
 * The card leans toward the cursor in real perspective and a soft highlight
 * tracks the pointer across its surface. Purely a desktop flourish: it is gated
 * OFF for touch/coarse-pointer, small screens, and reduced-motion (via
 * useLowPowerMode + useReducedMotion), where it renders a plain element so the
 * existing CSS hover/reveal behaviour is untouched — no transform fighting, and
 * none of the phone-GPU raster cost.
 *
 * Transform-only (rotate + perspective); no layout, no filter, no continuous
 * loop — so it stays clear of the flicker/LCP issues this app has hardened.
 */
export default function TiltCard({
  children,
  className = '',
  max = 7,            // peak rotation in degrees
  glare = true,
  as: Tag = 'div',
  ...props
}) {
  const reduced = useReducedMotion()
  const lowPower = useLowPowerMode()   // true on touch / ≤900px / reduce-motion
  const enabled = !reduced && !lowPower

  const ref = useRef(null)
  const rotateX = useMotionValue(0)
  const rotateY = useMotionValue(0)
  const glareX = useMotionValue(50)
  const glareY = useMotionValue(50)
  const glareOpacity = useMotionValue(0)   // 0 at rest → only lights up under the cursor

  const sx = useSpring(rotateX, { stiffness: 220, damping: 20, mass: 0.4 })
  const sy = useSpring(rotateY, { stiffness: 220, damping: 20, mass: 0.4 })
  const glareFade = useSpring(glareOpacity, { stiffness: 180, damping: 26 })
  const glareBg = useMotionTemplate`radial-gradient(circle at ${glareX}% ${glareY}%, rgba(255,255,255,0.16), transparent 46%)`

  const handleMove = useCallback((e) => {
    const el = ref.current
    if (!el) return
    const r = el.getBoundingClientRect()
    const px = (e.clientX - r.left) / r.width   // 0 → 1 across
    const py = (e.clientY - r.top) / r.height    // 0 → 1 down
    rotateY.set((px - 0.5) * (max * 2))          // left/right lean
    rotateX.set((0.5 - py) * (max * 2))          // up/down lean
    glareX.set(px * 100)
    glareY.set(py * 100)
    glareOpacity.set(1)
  }, [max, rotateX, rotateY, glareX, glareY, glareOpacity])

  const handleLeave = useCallback(() => {
    rotateX.set(0)
    rotateY.set(0)
    glareOpacity.set(0)
  }, [rotateX, rotateY, glareOpacity])

  if (!enabled) {
    const Plain = Tag
    return <Plain className={className} {...props}>{children}</Plain>
  }

  const MotionTag = m[Tag] || m.div
  return (
    <MotionTag
      ref={ref}
      className={className}
      onMouseMove={handleMove}
      onMouseLeave={handleLeave}
      style={{ rotateX: sx, rotateY: sy, transformPerspective: 900 }}
      {...props}
    >
      {children}
      {glare && (
        <m.span
          aria-hidden="true"
          className="tilt-glare"
          style={{ background: glareBg, opacity: glareFade }}
        />
      )}
    </MotionTag>
  )
}
