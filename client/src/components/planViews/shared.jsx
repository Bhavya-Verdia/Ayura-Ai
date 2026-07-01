import React from 'react'
import { m } from 'framer-motion'
import {
  ChevronRight,
} from 'lucide-react'
import '../PlanViewer.css'

export const isObjectArray = (arr) =>
  Array.isArray(arr) && arr.length > 0 && typeof arr[0] === 'object' && arr[0] !== null


export const getCardTitle = (obj) => {
  const titleKeys = ['day_name', 'pose', 'name', 'meal', 'remedy_name', 'medicine_name', 'focus', 'therapy']
  for (const key of titleKeys) {
    if (obj[key]) return obj[key]
  }
  for (const [, v] of Object.entries(obj)) {
    if (typeof v === 'string') return v
  }
  return 'Item'
}


export function renderValue(val) {
  if (!val) return null

  if (typeof val === 'string') {
    return <p className="plan-string-val">{val}</p>
  }

  if (Array.isArray(val)) {
    if (isObjectArray(val)) {
      return (
        <div className="plan-grid">
          {val.map((item, i) => {
            const title = getCardTitle(item)
            const otherEntries = Object.entries(item).filter(([, v]) => v !== title)
            return (
              <m.div
                key={i}
                className="plan-card"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.32, delay: i * 0.05, ease: [0.16, 1, 0.3, 1] }}
              >
                <div className="plan-card-title">
                  <ChevronRight size={13} className="plan-card-chevron" />
                  {title}
                </div>
                {otherEntries.map(([k, v]) => {
                  if (k === 'safety_tier' || k === 'safety_level') {
                    const tierStr = String(v).toLowerCase()
                    let tierClass = 'tier-safe'
                    if (tierStr.includes('high') || tierStr.includes('caution')) tierClass = 'tier-high'
                    else if (tierStr.includes('medium')) tierClass = 'tier-medium'
                    return (
                      <div key={k} className="plan-card-item">
                        <span className="plan-card-label">Safety</span>
                        <span className={`plan-safety-tier ${tierClass}`}>{v}</span>
                      </div>
                    )
                  }
                  if (typeof v === 'string' || typeof v === 'number') {
                    return (
                      <div key={k} className="plan-card-item">
                        <span className="plan-card-label">{k.replace(/_/g, ' ')}</span>
                        <span className="plan-card-value">{v}</span>
                      </div>
                    )
                  }
                  if (Array.isArray(v) && v.every(x => typeof x === 'string')) {
                    return (
                      <div key={k} className="plan-card-item">
                        <span className="plan-card-label">{k.replace(/_/g, ' ')}</span>
                        <ul className="plan-list">
                          {v.map((str, idx) => <li key={idx} className="plan-list-item">{str}</li>)}
                        </ul>
                      </div>
                    )
                  }
                  return (
                    <div key={k} className="plan-card-item-complex">
                      <span className="plan-card-label">{k.replace(/_/g, ' ')}</span>
                      {renderValue(v)}
                    </div>
                  )
                })}
              </m.div>
            )
          })}
        </div>
      )
    }
    return (
      <ul className="plan-list">
        {val.map((item, i) => (
          <li key={i} className="plan-list-item">{String(item)}</li>
        ))}
      </ul>
    )
  }

  if (typeof val === 'object') {
    return (
      <div className="plan-nested-obj">
        {Object.entries(val).map(([k, v]) => (
          <div key={k}>
            <div className="plan-key-title">{k.replace(/_/g, ' ')}</div>
            {renderValue(v)}
          </div>
        ))}
      </div>
    )
  }

  return <span className="plan-string-val">{String(val)}</span>
}

// ── Diet dedicated renderer ───────────────────────────────────────────────────
