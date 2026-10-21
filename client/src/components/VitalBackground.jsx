
/* ────────────────────────────────────────────────────────────────────────────
   STATIC ambient background.

   The animated version of this background was confirmed (A/B on both macOS and
   Android — full removal made the flicker vanish) to be the app-wide UI flicker
   source: continuously animating conic/aurora/dash-sweep layers force large,
   permanent GPU compositor surfaces that intermittently composite empty on
   scroll/click/load. That flicker only manifests when a real display scans the
   frame out, so it never showed up in screen recordings or headless tests.

   This is NOT the old animation paused — that read as leftover motion (12
   identical strands frozen mid-dash, blobs tuned to look right only while
   drifting). It is composed to be still: one off-centre key light, a fanned
   strand bundle whose strokes fade out at both ends via SVG gradients, a grid
   lit from the same direction, and a vignette that closes the frame.

   Every layer is a single static paint. No CSS animation, no `will-change`, no
   blend modes, no live filters, no canvas — softness comes from multi-stop
   gradients rather than `filter: blur()`, which is what made the old aurora
   blobs evictable full-viewport GPU textures. `.vital-bg-static` (index.css)
   hard-disables those properties on the whole subtree, so nothing
   re-rasterizes after the first paint. If ambient motion is ever wanted again,
   reintroduce it in small, individually-tested increments — never all layers
   at once.
   ──────────────────────────────────────────────────────────────────────────── */

/* A fanned bundle of nadi strands sweeping across the frame. Fewer, wider-spaced
   lines than the old 12 — at this opacity a dense bundle just reads as haze. */
function makeStrands(side) {
  const flip = (x) => (side > 0 ? x : 760 - x)
  return Array.from({ length: 7 }, (_, i) => ({
    id: i,
    d: `M ${flip(-60)} ${40 + i * 16}
        C ${flip(200)} ${-10 + i * 22},
          ${flip(430)} ${240 - i * 10},
          ${flip(820)} ${120 + i * 14}`,
    // Peaked at the centre of the bundle so it has a spine rather than reading
    // as seven equal-weight lines.
    width: 1.1 - Math.abs(i - 3) * 0.18,
    opacity: 0.9 - Math.abs(i - 3) * 0.17,
  }))
}

function VitalPaths({ side = 1 }) {
  const strands = makeStrands(side)
  const gradId = `strand-fade-${side > 0 ? 'a' : 'b'}`
  return (
    <svg className="vital-paths" viewBox="0 0 760 420" preserveAspectRatio="none" aria-hidden="true">
      <defs>
        {/* Strokes fade to nothing at both ends, so the strands read as light
            passing through the frame instead of lines clipped by its edges. */}
        <linearGradient id={gradId} x1={side > 0 ? '0' : '1'} y1="0" x2={side > 0 ? '1' : '0'} y2="0">
          <stop offset="0%" stopColor="currentColor" stopOpacity="0" />
          <stop offset="18%" stopColor="currentColor" stopOpacity="0.5" />
          <stop offset="52%" stopColor="currentColor" stopOpacity="1" />
          <stop offset="86%" stopColor="currentColor" stopOpacity="0.18" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
        </linearGradient>
      </defs>
      {strands.map((strand) => (
        <path
          key={`${side}-${strand.id}`}
          d={strand.d}
          stroke={`url(#${gradId})`}
          strokeWidth={strand.width}
          strokeLinecap="round"
          opacity={strand.opacity * 0.22}
          fill="none"
        />
      ))}
    </svg>
  )
}

/* The vital-sign motif: one hero trace with a ghost above and below it. */
function PulseLines() {
  return (
    <svg className="vital-pulse-lines" viewBox="0 0 1200 300" preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <linearGradient id="pulse-fade" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="currentColor" stopOpacity="0" />
          <stop offset="22%" stopColor="currentColor" stopOpacity="0.7" />
          <stop offset="46%" stopColor="currentColor" stopOpacity="1" />
          <stop offset="78%" stopColor="currentColor" stopOpacity="0.35" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
        </linearGradient>
      </defs>
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
          stroke="url(#pulse-fade)"
          strokeWidth={row === 1 ? 1.3 : 0.7}
          strokeLinecap="round"
          opacity={row === 1 ? 0.34 : 0.14}
        />
      ))}
    </svg>
  )
}

/* Light pools. Pure radial gradients with a smooth multi-stop falloff — the
   same soft look the old blur(90px) blobs had, at zero filter cost and with no
   evictable filtered texture. Positioned as one key light (upper left) plus two
   dimmer bounces, rather than three co-equal blobs. */
// Colours are in index.css (.vital-pool--key/--warm/--bounce, per data-theme):
// nothing here may depend on the theme, or a prerendered page could not be
// hydrated for a light-theme visitor.
const POOLS = [
  { cls: 'vital-pool vital-pool--key', style: { top: '-22%', left: '-14%', width: '86%', height: '86%' } },
  { cls: 'vital-pool vital-pool--warm', style: { top: '-8%', right: '-16%', width: '64%', height: '64%' } },
  { cls: 'vital-pool vital-pool--bounce', style: { bottom: '-24%', left: '26%', width: '68%', height: '62%' } },
]

function LightPools() {
  return (
    <>
      {POOLS.map((pool) => (
        <div key={pool.cls} className={pool.cls} style={pool.style} aria-hidden="true" />
      ))}
    </>
  )
}

export default function VitalBackground({ density = 'normal' }) {
  return (
    <div className={`vital-bg vital-bg-static vital-bg-${density}`} aria-hidden="true">
      <LightPools />
      <div className="vital-gradient-field" />
      <div className="vital-grid-field" />
      <VitalPaths side={1} />
      <VitalPaths side={-1} />
      <PulseLines />
      <div className="vital-vignette" />
      <div className="vital-noise-field" />
    </div>
  )
}
