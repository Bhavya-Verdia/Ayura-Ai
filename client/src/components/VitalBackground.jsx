import { m, useReducedMotion } from 'framer-motion'
import { useTheme } from '../providers/ThemeProvider'
import useLowPowerMode from '../hooks/useLowPowerMode'

function makeVitalPaths(side) {
  return Array.from({ length: 12 }, (_, i) => ({
    id: i,
    d: `M ${side > 0 ? -150 - i * 7 : 850 + i * 7} ${28 + i * 9}
        C ${side > 0 ? 110 + i * 3 : 650 - i * 4} ${-20 + i * 4},
          ${side > 0 ? 210 + i * 7 : 500 - i * 6} ${210 - i * 2},
          ${side > 0 ? 740 - i * 2 : -30 + i * 4} ${150 + i * 6}`,
    width: 0.55 + i * 0.025,
    opacity: 0.08 + i * 0.006,
    duration: 18 + i * 0.55,
  }))
}

function VitalPaths({ side = 1 }) {
  const prefersReducedMotion = useReducedMotion()
  const paths = makeVitalPaths(side)

  return (
    <svg className="vital-paths" viewBox="0 0 760 420" preserveAspectRatio="none" aria-hidden="true">
      {paths.map((path) => (
        <m.path
          key={`${side}-${path.id}`}
          d={path.d}
          stroke="currentColor"
          strokeWidth={path.width}
          strokeOpacity={path.opacity}
          fill="none"
          initial={{ pathLength: 0.18, pathOffset: 0, opacity: 0.35 }}
          animate={
            prefersReducedMotion
              ? { pathLength: 0.5, pathOffset: 0, opacity: path.opacity }
              : { pathLength: [0.18, 0.86, 0.18], pathOffset: [0, 1, 0], opacity: [0.22, 0.58, 0.22] }
          }
          transition={
            prefersReducedMotion
              ? { duration: 0 }
              : { duration: path.duration, repeat: Infinity, ease: 'linear' }
          }
        />
      ))}
    </svg>
  )
}

function PulseLines() {
  const prefersReducedMotion = useReducedMotion()
  return (
    <svg className="vital-pulse-lines" viewBox="0 0 1200 300" preserveAspectRatio="none" aria-hidden="true">
      {[0, 1, 2].map((row) => (
        <m.path
          key={row}
          d={`M0 ${82 + row * 72}
              C120 ${72 + row * 18}, 180 ${118 + row * 10}, 260 ${92 + row * 18}
              C330 ${70 + row * 14}, 390 ${85 + row * 8}, 450 ${85 + row * 8}
              L492 ${85 + row * 8} L520 ${26 + row * 26} L552 ${160 + row * 14}
              L584 ${70 + row * 12} L640 ${88 + row * 9}
              C760 ${126 + row * 10}, 840 ${46 + row * 16}, 960 ${86 + row * 13}
              C1050 ${116 + row * 7}, 1120 ${82 + row * 10}, 1200 ${98 + row * 10}`}
          fill="none"
          stroke="currentColor"
          strokeWidth={row === 1 ? 1.15 : 0.75}
          strokeOpacity={row === 1 ? 0.16 : 0.08}
          initial={{ pathLength: 0, pathOffset: 0.12 }}
          animate={
            prefersReducedMotion
              ? { pathLength: 1, pathOffset: 0 }
              : { pathLength: [0.08, 1, 0.08], pathOffset: [0, 0.9, 1.8] }
          }
          transition={
            prefersReducedMotion
              ? { duration: 0 }
              : { duration: 16 + row * 4, repeat: Infinity, ease: 'linear' }
          }
        />
      ))}
    </svg>
  )
}

/* Frozen (reduced-motion) renders of the animated path layers: plain SVG,
   painted once at load and never again. The dash segment is staggered per
   path to mimic a mid-flight frame of the animation rather than 12 identical
   full strokes. */
function VitalPathsFrozen({ side = 1 }) {
  const paths = makeVitalPaths(side)
  return (
    <svg className="vital-paths" viewBox="0 0 760 420" preserveAspectRatio="none" aria-hidden="true">
      {paths.map((path, i) => (
        <path
          key={`${side}-${path.id}`}
          d={path.d}
          stroke="currentColor"
          strokeWidth={path.width}
          strokeOpacity={path.opacity}
          opacity={0.45}
          fill="none"
          pathLength="1"
          strokeDasharray="0.55 0.45"
          strokeDashoffset={-((i * 0.13) % 1)}
        />
      ))}
    </svg>
  )
}

function PulseLinesFrozen() {
  return (
    <svg className="vital-pulse-lines" viewBox="0 0 1200 300" preserveAspectRatio="none" aria-hidden="true">
      {[0, 1, 2].map((row) => (
        <path
          key={row}
          d={`M0 ${82 + row * 72}
              C120 ${72 + row * 18}, 180 ${118 + row * 10}, 260 ${92 + row * 18}
              C330 ${70 + row * 14}, 390 ${85 + row * 8}, 450 ${85 + row * 8}
              L492 ${85 + row * 8} L520 ${26 + row * 26} L552 ${160 + row * 14}
              L584 ${70 + row * 12} L640 ${88 + row * 9}
              C760 ${126 + row * 10}, 840 ${46 + row * 16}, 960 ${86 + row * 13}
              C1050 ${116 + row * 7}, 1120 ${82 + row * 10}, 1200 ${98 + row * 10}`}
          fill="none"
          stroke="currentColor"
          strokeWidth={row === 1 ? 1.15 : 0.75}
          strokeOpacity={row === 1 ? 0.16 : 0.08}
          pathLength="1"
          strokeDasharray="0.8 0.2"
          strokeDashoffset={-(row * 0.33)}
        />
      ))}
    </svg>
  )
}

/* Three independently floating aurora blobs.
   `lite` (reduced-motion): drop the blur filter; the radial gradients are
   already soft, so enlarging them ~25% fakes the blur's spread without a
   per-frame GPU re-sample. */
function AuroraBlobs({ theme, lite = false }) {
  const isDark = theme === 'dark'

  const blobs = [
    {
      cls: 'aurora-blob-1',
      style: {
        position: 'absolute',
        top: '-10%',
        left: '-5%',
        width: lite ? '68%' : '55%',
        height: lite ? '68%' : '55%',
        borderRadius: '50%',
        background: isDark
          ? 'radial-gradient(circle, rgba(92,171,116,0.22) 0%, transparent 70%)'
          : 'radial-gradient(circle, rgba(13,148,136,0.18) 0%, transparent 70%)',
        filter: lite ? undefined : 'blur(var(--aurora-blur, 90px))',
        pointerEvents: 'none',
      },
    },
    {
      cls: 'aurora-blob-2',
      style: {
        position: 'absolute',
        top: '-5%',
        right: '-10%',
        width: lite ? '62%' : '50%',
        height: lite ? '62%' : '50%',
        borderRadius: '50%',
        background: isDark
          ? 'radial-gradient(circle, rgba(230,162,60,0.18) 0%, transparent 70%)'
          : 'radial-gradient(circle, rgba(124,58,237,0.12) 0%, transparent 70%)',
        filter: lite ? undefined : 'blur(var(--aurora-blur, 90px))',
        pointerEvents: 'none',
      },
    },
    {
      cls: 'aurora-blob-3',
      style: {
        position: 'absolute',
        bottom: '-15%',
        left: '30%',
        width: lite ? '56%' : '45%',
        height: lite ? '56%' : '45%',
        borderRadius: '50%',
        background: isDark
          ? 'radial-gradient(circle, rgba(251,146,60,0.12) 0%, transparent 70%)'
          : 'radial-gradient(circle, rgba(234,88,12,0.08) 0%, transparent 70%)',
        filter: lite ? undefined : 'blur(var(--aurora-blur, 90px))',
        pointerEvents: 'none',
      },
    },
  ]

  return (
    <>
      {blobs.map((blob) => (
        <div key={blob.cls} className={blob.cls} style={blob.style} aria-hidden="true" />
      ))}
    </>
  )
}

export default function VitalBackground({ density = 'normal' }) {
  const { theme } = useTheme()
  const lowPower = useLowPowerMode()

  // Reduced-motion (OS accessibility preference): swap the animated layers
  // for static equivalents — frozen paths, unblurred blobs, no noise field.
  // Every screen size otherwise gets the identical full desktop treatment.
  if (lowPower) {
    return (
      <div className={`vital-bg vital-bg-${theme} vital-bg-${density}`} aria-hidden="true">
        <AuroraBlobs theme={theme} lite />
        <div className="vital-gradient-field" />
        <div className="vital-grid-field" />
        <VitalPathsFrozen side={1} />
        <VitalPathsFrozen side={-1} />
        <PulseLinesFrozen />
      </div>
    )
  }

  return (
    <div className={`vital-bg vital-bg-${theme} vital-bg-${density}`} aria-hidden="true">
      {/* Independently animated aurora blobs */}
      <AuroraBlobs theme={theme} />
      <div className="vital-gradient-field" />
      <div className="vital-grid-field" />
      <VitalPaths side={1} />
      <VitalPaths side={-1} />
      <PulseLines />
      <div className="vital-noise-field" />
    </div>
  )
}
