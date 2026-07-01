import { useRef, useCallback } from 'react'
import { m, useMotionValue, useSpring } from 'framer-motion'

/**
 * MagneticButton — wraps any element with a magnetic cursor attraction.
 * The element subtly pulls toward the cursor when within `radius` px.
 *
 * Usage:
 *   <MagneticButton className="lnd-cta-main" strength={0.3}>
 *     Get Started →
 *   </MagneticButton>
 */
export default function MagneticButton({
  children,
  strength = 0.28,
  className = '',
  style = {},
  onClick,
  as: Tag = 'button',
  href,
  ...props
}) {
  const ref = useRef(null)

  const rawX = useMotionValue(0)
  const rawY = useMotionValue(0)
  const x = useSpring(rawX, { stiffness: 160, damping: 16, mass: 0.4 })
  const y = useSpring(rawY, { stiffness: 160, damping: 16, mass: 0.4 })

  const handleMouseMove = useCallback((e) => {
    const el = ref.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const cx = rect.left + rect.width / 2
    const cy = rect.top + rect.height / 2
    rawX.set((e.clientX - cx) * strength)
    rawY.set((e.clientY - cy) * strength)
  }, [rawX, rawY, strength])

  const handleMouseLeave = useCallback(() => {
    rawX.set(0)
    rawY.set(0)
  }, [rawX, rawY])

  const MotionTag = m[Tag] || m.button

  return (
    <MotionTag
      ref={ref}
      className={className}
      style={{ x, y, ...style }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      onClick={onClick}
      href={href}
      whileTap={{ scale: 0.97 }}
      {...props}
    >
      {children}
    </MotionTag>
  )
}
