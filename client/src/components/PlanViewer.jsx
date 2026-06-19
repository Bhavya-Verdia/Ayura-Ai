import React from 'react'
import { motion } from 'framer-motion'
import {
  Sun, PersonStanding, Dumbbell, Leaf, Coffee, Pill,
  Sparkles, FlaskConical, AlertTriangle, ChevronRight, Star,
} from 'lucide-react'
import './PlanViewer.css'

const isObjectArray = (arr) =>
  Array.isArray(arr) && arr.length > 0 && typeof arr[0] === 'object' && arr[0] !== null

const getCardTitle = (obj) => {
  const titleKeys = ['day_name', 'pose', 'name', 'meal', 'remedy_name', 'medicine_name', 'focus', 'therapy']
  for (const key of titleKeys) {
    if (obj[key]) return obj[key]
  }
  for (const [, v] of Object.entries(obj)) {
    if (typeof v === 'string') return v
  }
  return 'Item'
}

const SECTION_ICONS = {
  routine_plan:     Sun,
  yoga_plan:        PersonStanding,
  gym_plan:         Dumbbell,
  diet_plan:        Leaf,
  panchakarma_plan: FlaskConical,
  home_remedies:    Coffee,
  medicines:        Pill,
}

const SECTION_KEY_MAP = {
  routine:     'routine_plan',
  yoga:        'yoga_plan',
  gym:         'gym_plan',
  diet:        'diet_plan',
  panchakarma: 'panchakarma_plan',
  remedies:    'home_remedies',
  medicines:   'medicines',
}

const SKIP_KEYS = [
  'user_summary', 'generated_at', 'generation_method', 'model_used', 'id',
  'ratings', 'safety_checks', 'daily_tip', 'disclaimer', 'medical_disclaimer',
  'plan_id', 'enrichment_model', 'enriched', 'type', 'phase_breakdown',
]

function renderValue(val) {
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
              <motion.div
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
              </motion.div>
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

export default function PlanViewer({ plan, planType }) {
  if (!plan) return <p className="plan-empty">No plan data available.</p>

  const sectionKey = planType ? SECTION_KEY_MAP[planType] : null
  const sections = sectionKey && plan[sectionKey]
    ? { [sectionKey]: plan[sectionKey] }
    : Object.fromEntries(Object.entries(plan).filter(([k]) => !SKIP_KEYS.includes(k) && plan[k]))

  return (
    <div className="plan-viewer-container">
      {/* ── Summary banner ── */}
      {plan.user_summary && (
        <motion.div
          className="plan-summary-banner"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="plan-summary-name">
            Good morning, {plan.user_summary.name?.split(' ')[0]}
          </div>
          {plan.user_summary.dominant_dosha && (
            <div className="plan-summary-dosha-row">
              <span>Your dominant dosha is</span>
              <span className="plan-dosha-badge">{plan.user_summary.dominant_dosha}</span>
            </div>
          )}
          {plan.daily_tip && (
            <div className="plan-daily-tip">
              <Star size={14} strokeWidth={2} />
              <span>{plan.daily_tip}</span>
            </div>
          )}
        </motion.div>
      )}

      {/* ── Plan sections ── */}
      {Object.entries(sections).map(([key, value], idx) => {
        const IconComponent = SECTION_ICONS[key] || Sparkles
        return value ? (
          <motion.div
            key={key}
            className="plan-section"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.42, delay: idx * 0.09, ease: [0.16, 1, 0.3, 1] }}
          >
            <h3 className="plan-section-title">
              <div className="plan-section-icon-wrap">
                <IconComponent size={17} strokeWidth={2} />
              </div>
              {key.replace(/_/g, ' ')}
            </h3>
            {renderValue(value)}
          </motion.div>
        ) : null
      })}

      {/* ── Safety & disclaimers ── */}
      {(plan.safety_checks?.warnings?.length > 0 || plan.disclaimer || plan.medical_disclaimer) && (
        <motion.div
          className="plan-safety-box"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="plan-safety-title">
            <AlertTriangle size={16} strokeWidth={2} />
            Important Safety & Medical Notes
          </div>
          {plan.safety_checks?.warnings?.length > 0 && (
            <ul className="plan-safety-list">
              {plan.safety_checks.warnings.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          )}
          {(plan.disclaimer || plan.medical_disclaimer) && (
            <p className="plan-safety-disclaimer">
              {plan.disclaimer || plan.medical_disclaimer}
            </p>
          )}
        </motion.div>
      )}
    </div>
  )
}
