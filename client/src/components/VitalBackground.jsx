import { useTheme } from '../providers/ThemeProvider'

/* ────────────────────────────────────────────────────────────────────────────
   STATIC ambient background.

   The animated version of this background was confirmed (A/B on both macOS and
   Android — full removal made the flicker vanish) to be the app-wide UI flicker
   source: continuously animating conic/aurora/dash-sweep layers force large,
   permanent GPU compositor surfaces that intermittently composite empty on
   scroll/click/load. That flicker only manifests when a real display scans the
   frame out, so it never showed up in screen recordings or headless tests.

   This component now renders the SAME layered look — aurora glow, conic field,
   grid, the signature flowing strands, grain — but every layer is a single
   static paint. No CSS animation, no `will-change`, no blend modes, no live
   filters, no canvas. `.vital-bg-static` (index.css) hard-disables those on all
   descendants, so nothing re-rasterizes after the first paint. If ambient
   motion is ever wanted again, reintroduce it in small, individually-tested
   increments — never all layers at once.
   ──────────────────────────────────────────────────────────────────────────── */

function makeVitalPaths(side) {
  return Array.from({ length: 12 }, (_, i) => ({
    id: i,
    d: `M ${side > 0 ? -150 - i * 7 : 850 + i * 7} ${28 + i * 9}
        C ${side > 0 ? 110 + i * 3 : 650 - i * 4} ${-20 + i * 4},
          ${side > 0 ? 210 + i * 7 : 500 - i * 6} ${210 - i * 2},
          ${side > 0 ? 740 - i * 2 : -30 + i * 4} ${150 + i * 6}`,
    width: 0.55 + i * 0.025,
    opacity: 0.08 + i * 0.006,
  }))
}

/* Flowing strands, painted once. The dash segment is staggered per path to read
   as a mid-flight frame of the old animation rather than 12 identical strokes. */
function VitalPaths({ side = 1 }) {
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

function PulseLines() {
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

/* Static aurora glows — soft radial gradients, no float animation, no blur. */
function AuroraBlobs({ theme }) {
  const isDark = theme === 'dark'
  const blobs = [
    {
      cls: 'aurora-blob-1',
      style: {
        top: '-10%', left: '-5%', width: '68%', height: '68%',
        background: isDark
          ? 'radial-gradient(circle, rgba(92,171,116,0.22) 0%, transparent 70%)'
          : 'radial-gradient(circle, rgba(13,148,136,0.18) 0%, transparent 70%)',
      },
    },
    {
      cls: 'aurora-blob-2',
      style: {
        top: '-5%', right: '-10%', width: '62%', height: '62%',
        background: isDark
          ? 'radial-gradient(circle, rgba(230,162,60,0.18) 0%, transparent 70%)'
          : 'radial-gradient(circle, rgba(124,58,237,0.12) 0%, transparent 70%)',
      },
    },
    {
      cls: 'aurora-blob-3',
      style: {
        bottom: '-15%', left: '30%', width: '56%', height: '56%',
        background: isDark
          ? 'radial-gradient(circle, rgba(251,146,60,0.12) 0%, transparent 70%)'
          : 'radial-gradient(circle, rgba(234,88,12,0.08) 0%, transparent 70%)',
      },
    },
  ]
  return (
    <>
      {blobs.map((blob) => (
        <div
          key={blob.cls}
          className={blob.cls}
          style={{ position: 'absolute', borderRadius: '50%', pointerEvents: 'none', ...blob.style }}
          aria-hidden="true"
        />
      ))}
    </>
  )
}

export default function VitalBackground({ density = 'normal' }) {
  const { theme } = useTheme()

  return (
    <div className={`vital-bg vital-bg-static vital-bg-${theme} vital-bg-${density}`} aria-hidden="true">
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
