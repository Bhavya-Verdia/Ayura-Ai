import { m } from 'framer-motion'
import { DOSHA_COLORS, DOSHA_LABELS, TRAIT_PRIORITY_LABEL, TRAIT_DISPLAY_NAMES } from './doshaDisplay'

// Prakriti is deliberately capped at 55 for self-report, so it lives on a
// narrower scale than the uncapped Vikriti and needs its own bands — against the
// shared ladder below, "Dominant" (>=66) was unreachable and every constitution
// came back "Elevated" no matter how clear the answers were.
function qualitativeLabel(pct, capped) {
  const [dominant, elevated, moderate] = capped ? [46, 34, 20] : [66, 46, 26]
  if (pct >= dominant) return { text: 'Dominant', color: 'var(--ayura-teal)' }
  if (pct >= elevated) return { text: 'Elevated', color: 'var(--ayura-amber)' }
  if (pct >= moderate) return { text: 'Moderate', color: 'var(--text-secondary)' }
  return { text: 'Low', color: 'var(--text-secondary)' }
}

export function SpectrumSection({ title, scores, highlightDominant, capped, footnote }) {
  const sorted = Object.entries(scores).sort((a, b) => b[1] - a[1])
  return (
    <div className="da-spectrum-section">
      <h4 className="da-spectrum-title">{title}</h4>
      {sorted.map(([dosha, pct]) => {
        const ql = qualitativeLabel(pct, capped)
        return (
          <div key={dosha} className={`da-dosha-bar-row ${highlightDominant && dosha === sorted[0][0] ? 'dominant' : ''}`}>
            <span className="da-dosha-bar-label" style={{ color: DOSHA_COLORS[dosha] }}>
              {DOSHA_LABELS[dosha]}
            </span>
            <div className="da-dosha-bar-track">
              <m.div
                className="da-dosha-bar-fill"
                style={{ background: DOSHA_COLORS[dosha] }}
                initial={{ width: 0 }}
                animate={{ width: `${capped ? Math.round((pct / 55) * 100) : pct}%` }}
                transition={{ duration: 0.9, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
              />
            </div>
            <div className="da-dosha-bar-right">
              <span className="da-dosha-bar-pct">{capped ? pct : `${pct}%`}</span>
              <span className="da-dosha-bar-qual" style={{ color: ql.color }}>{ql.text}</span>
            </div>
          </div>
        )
      })}
      {footnote && <p className="da-spectrum-footnote">{footnote}</p>}
    </div>
  )
}

export function TraitBreakdown({ traits }) {
  if (!traits || Object.keys(traits).length === 0) return null
  const sortOrder = ['Primary', 'Strong', 'Moderate', 'Manasa', 'Secondary']
  const entries = Object.entries(traits)
    .filter(([, v]) => v)
    .sort((a, b) => {
      const ai = sortOrder.indexOf(TRAIT_PRIORITY_LABEL[a[0]] || 'Secondary')
      const bi = sortOrder.indexOf(TRAIT_PRIORITY_LABEL[b[0]] || 'Secondary')
      return (ai === -1 ? sortOrder.length : ai) - (bi === -1 ? sortOrder.length : bi)
    })
  return (
    <div className="da-trait-breakdown">
      <span className="da-breakdown-title">What drove your result</span>
      <div className="da-breakdown-rows">
        {entries.map(([trait, dosha]) => {
          // A blend ("vata+pitta") colours by its primary and labels both parts.
          const [primary, secondary] = String(dosha).split('+')
          const label = secondary
            ? `${DOSHA_LABELS[primary] || primary} + ${DOSHA_LABELS[secondary] || secondary}`
            : (DOSHA_LABELS[dosha] || dosha)
          return (
            <div key={trait} className="da-breakdown-row">
              <span className="da-breakdown-trait">{TRAIT_DISPLAY_NAMES[trait] || trait}</span>
              <span className="da-breakdown-arrow">→</span>
              <span className="da-breakdown-dosha" style={{ color: DOSHA_COLORS[primary] || 'var(--text-secondary)' }}>
                {label}
              </span>
              <span className="da-breakdown-priority">{TRAIT_PRIORITY_LABEL[trait] || ''}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
