import { m } from 'framer-motion'
import { DOSHA_COLOR } from '../constants/dosha'

// Colors resolve through the single dosha source of truth (constants/dosha.js);
// only the placeholder scores/labels live here.
const DOSHA_CONFIG = {
  vata:  { color: DOSHA_COLOR.vata,  label: 'Vata',  score: 65 },
  pitta: { color: DOSHA_COLOR.pitta, label: 'Pitta', score: 45 },
  kapha: { color: DOSHA_COLOR.kapha, label: 'Kapha', score: 30 },
}

/**
 * DoshaArcRings — three concentric SVG arcs, one per dosha,
 * each animating from 0 → their score value via stroke-dashoffset.
 *
 * Usage:
 *   <DoshaArcRings dominantDosha="vata" scores={{ vata: 65, pitta: 45, kapha: 30 }} />
 */
export default function DoshaArcRings({
  dominantDosha = 'vata',
  scores = {},
  size = 180,
}) {
  const cx = size / 2
  const cy = size / 2

  // Three concentric rings with different radii
  const rings = [
    { key: 'vata',  radius: size * 0.41, strokeWidth: 7 },
    { key: 'pitta', radius: size * 0.31, strokeWidth: 6 },
    { key: 'kapha', radius: size * 0.21, strokeWidth: 5 },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
      <div style={{ position: 'relative', width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ overflow: 'visible' }}>
          <defs>
            {rings.map(({ key }) => {
              const cfg = DOSHA_CONFIG[key]
              return (
                <radialGradient key={`grd-${key}`} id={`arc-grd-${key}`} cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stopColor={cfg.color} stopOpacity="0.4" />
                  <stop offset="100%" stopColor={cfg.color} stopOpacity="1" />
                </radialGradient>
              )
            })}
            {/* Glow filters */}
            {rings.map(({ key }) => (
              <filter key={`filter-${key}`} id={`arc-glow-${key}`} x="-30%" y="-30%" width="160%" height="160%">
                <feGaussianBlur stdDeviation="2.5" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
            ))}
          </defs>

          {rings.map(({ key, radius, strokeWidth }) => {
            const cfg   = DOSHA_CONFIG[key]
            const score = scores[key] ?? cfg.score
            const circumference = 2 * Math.PI * radius
            const offset = circumference - (circumference * score) / 100

            return (
              <g key={key}>
                {/* Track */}
                <circle
                  cx={cx} cy={cy} r={radius}
                  fill="none"
                  stroke={`${cfg.color}18`}
                  strokeWidth={strokeWidth}
                />
                {/* Animated fill arc */}
                <m.circle
                  cx={cx} cy={cy} r={radius}
                  fill="none"
                  stroke={cfg.color}
                  strokeWidth={strokeWidth}
                  strokeLinecap="round"
                  strokeDasharray={circumference}
                  initial={{ strokeDashoffset: circumference }}
                  animate={{ strokeDashoffset: offset }}
                  transition={{ duration: 1.4, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
                  transform={`rotate(-90 ${cx} ${cy})`}
                  filter={dominantDosha === key ? `url(#arc-glow-${key})` : undefined}
                  style={{
                    filter: `drop-shadow(0 0 6px ${cfg.color}66)`,
                  }}
                />
              </g>
            )
          })}

          {/* Centre label */}
          <text
            x={cx} y={cy - 6}
            textAnchor="middle" dominantBaseline="middle"
            fill={DOSHA_CONFIG[dominantDosha]?.color || DOSHA_COLOR.default}
            style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: size * 0.13 }}
          >
            {(scores[dominantDosha] ?? DOSHA_CONFIG[dominantDosha]?.score ?? 65)}
          </text>
          <text
            x={cx} y={cy + size * 0.09}
            textAnchor="middle"
            fill="rgba(168,157,139,0.85)"
            style={{ fontFamily: 'var(--font-ui)', fontWeight: 600, fontSize: size * 0.065, textTransform: 'uppercase', letterSpacing: 1 }}
          >
            {dominantDosha}
          </text>
        </svg>
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', justifyContent: 'center' }}>
        {rings.map(({ key }) => {
          const cfg   = DOSHA_CONFIG[key]
          const score = scores[key] ?? cfg.score
          return (
            <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.78rem', fontWeight: 600 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: cfg.color, display: 'inline-block', boxShadow: `0 0 6px ${cfg.color}88` }} />
              <span style={{ color: 'var(--text-secondary)' }}>{cfg.label}</span>
              <span style={{ color: cfg.color, fontWeight: 700 }}>{score}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
