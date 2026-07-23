import { useMemo } from 'react'
import { useReducedMotion } from 'framer-motion'
import { useTheme } from '../providers/ThemeProvider'
import useLowPowerMode from '../hooks/useLowPowerMode'

function seededRandom(seed) {
  const value = Math.sin(seed * 12.9898) * 43758.5453
  return value - Math.floor(value)
}

export default function ParticleField({
  count = 120,
  color1 = '#06b6d4',
  color2 = '#8b5cf6',
  spread = 18,
  style = {},
  className = '',
}) {
  const { theme } = useTheme()
  const prefersReducedMotion = useReducedMotion()
  const lowPower = useLowPowerMode()
  // Phones get the same field density as the laptop for a consistent look;
  // only reduced-motion thins the field (and drops the blurred orbs below).
  const particleCount = lowPower ? Math.min(count, 22) : Math.min(count, 160)

  const particles = useMemo(() => {
    return Array.from({ length: particleCount }, (_, index) => {
      const depth = seededRandom(index + 201)
      const drift = 12 + seededRandom(index + 301) * spread
      return {
        id: index,
        x: seededRandom(index + 1) * 100,
        y: seededRandom(index + 101) * 100,
        size: 1 + depth * 3.4,
        opacity: 0.18 + depth * (theme === 'light' ? 0.22 : 0.46),
        duration: 14 + seededRandom(index + 401) * 18,
        delay: seededRandom(index + 501) * -18,
        driftX: (seededRandom(index + 601) - 0.5) * drift,
        driftY: (seededRandom(index + 701) - 0.5) * drift,
        color: seededRandom(index + 801) > 0.5 ? color1 : color2,
      }
    })
  }, [color1, color2, particleCount, spread, theme])

  const orbs = useMemo(() => {
    if (lowPower) return []
    return Array.from({ length: 7 }, (_, index) => ({
      id: index,
      x: seededRandom(index + 901) * 100,
      y: seededRandom(index + 1001) * 100,
      size: 90 + seededRandom(index + 1101) * 150,
      duration: 18 + seededRandom(index + 1201) * 20,
      delay: seededRandom(index + 1301) * -18,
      color: seededRandom(index + 1401) > 0.5 ? color1 : color2,
    }))
  }, [color1, color2, lowPower])

  return (
    <div
      className={`particle-field-wrap particle-field-${theme} ${className}`.trim()}
      style={{
        position: 'absolute',
        inset: 0,
        zIndex: 0,
        pointerEvents: 'none',
        overflow: 'hidden',
        ...style,
      }}
      aria-hidden="true"
    >
      {orbs.map((orb) => (
        <span
          key={`orb-${orb.id}`}
          className="particle-orb"
          style={{
            left: `${orb.x}%`,
            top: `${orb.y}%`,
            width: `${orb.size}px`,
            height: `${orb.size}px`,
            /* Soft radial fill: with blur(34px) on top (desktop) it reads the
               same as a solid disc did, and on mobile the gradient alone IS
               the blur — the GPU tier drops the filter with no visible step. */
            background: `radial-gradient(closest-side, ${orb.color} 0%, transparent 88%)`,
            animationDuration: prefersReducedMotion ? '0s' : `${orb.duration}s`,
            animationPlayState: prefersReducedMotion ? 'paused' : 'running',
            animationDelay: prefersReducedMotion ? '0s' : `${orb.delay}s`,
          }}
        />
      ))}
      {particles.map((particle) => (
        <span
          key={particle.id}
          className="particle-dot"
          style={{
            left: `${particle.x}%`,
            top: `${particle.y}%`,
            width: `${particle.size}px`,
            height: `${particle.size}px`,
            opacity: prefersReducedMotion ? particle.opacity * 0.5 : particle.opacity,
            background: particle.color,
            color: particle.color,
            '--drift-x': `${particle.driftX}px`,
            '--drift-y': `${particle.driftY}px`,
            animationDuration: prefersReducedMotion ? '0s' : `${particle.duration}s`,
            animationPlayState: prefersReducedMotion ? 'paused' : 'running',
            animationDelay: prefersReducedMotion ? '0s' : `${particle.delay}s`,
          }}
        />
      ))}
    </div>
  )
}
