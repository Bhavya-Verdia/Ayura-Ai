import { motion } from 'framer-motion'

const DOSHA_CONFIG = {
  vata:  { color: '#818CF8', label: 'Vata',  score: 65 },
  pitta: { color: '#fb923c', label: 'Pitta', score: 45 },
  kapha: { color: '#34d399', label: 'Kapha', score: 30 },
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
                <motion.circle
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
            fill={DOSHA_CONFIG[dominantDosha]?.color || '#2dd4bf'}
            style={{ fontFamily: 'Sora, sans-serif', fontWeight: 800, fontSize: size * 0.11 }}
          >
            {(scores[dominantDosha] ?? DOSHA_CONFIG[dominantDosha]?.score ?? 65)}
          </text>
          <text
            x={cx} y={cy + size * 0.09}
            textAnchor="middle"
            fill="rgba(158,170,166,0.8)"
            style={{ fontFamily: 'Manrope, sans-serif', fontWeight: 600, fontSize: size * 0.065, textTransform: 'uppercase', letterSpacing: 1 }}
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
