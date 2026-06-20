import React from 'react'
import { motion } from 'framer-motion'
import {
  Sun, PersonStanding, Dumbbell, Leaf, Coffee, Pill,
  Sparkles, FlaskConical, AlertTriangle, ChevronRight, Star,
  Droplets, Calendar, ShieldCheck, Flame, Beaker, ArrowRight,
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
  // Panchakarma raw fields — rendered by PanchakarmaView instead
  'clinical_decisions', 'snehana_protocol', 'aushadha', 'samsarjana_krama',
  'daily_schedule',
]

// ── Panchakarma dedicated renderer ────────────────────────────────────────────
const DOSHA_COLOR = { vata: '#a78bfa', pitta: '#f97316', kapha: '#34d399', default: '#2dd4bf' }
const PHASE_ICON  = { purvakarma: Droplets, pradhana: Flame, paschat: Sparkles }

function PanchakarmaView({ plan }) {
  const cd      = plan.clinical_decisions || {}
  const elig    = cd.shodhana_or_shamana || {}
  const pk      = cd.pradhana_karma_selected || {}
  const ritu    = cd.ritu_context || {}
  const bs      = cd.basti_subtype || null
  const ph      = plan.phase_breakdown || {}
  const unmapped = cd.unmapped_conditions || []
  const rareAssessment = plan.rare_disease_assessment || null
  const sn   = plan.snehana_protocol || {}
  const aus  = plan.aushadha || {}
  const sk   = plan.samsarjana_krama || []
  const sch  = plan.daily_schedule || []
  const us   = plan.user_summary || {}

  const vikritiDom = cd.vikriti_dominant || us.vikriti_dominant || '—'
  const doshaColor = DOSHA_COLOR[vikritiDom] || DOSHA_COLOR.default
  const isShodhana = elig.type === 'shodhana'
  const isClinic = us.setting === 'clinic'

  const aushadhaRows = Object.entries(aus).filter(([, v]) => v)

  const AGNI_LABEL  = { sama: 'Sama Agni', vata: 'Vishama Agni', pitta: 'Tikshna Agni', kapha: 'Manda Agni' }
  const BALA_LABEL  = { uttama: 'Uttama Bala', madhyama: 'Madhyama Bala', manda: 'Manda Bala' }

  return (
    <div className="pk-view">

      {/* ── Clinic Vaidya Gate Banner ── */}
      {isClinic && (
        <div className="pk-vaidya-banner">
          <ShieldCheck size={16} className="pk-vaidya-icon" />
          <div className="pk-vaidya-text">
            <strong>Clinical Reference Plan — For Vaidya Consultation</strong>
            <p>This plan is generated using classical Ayurvedic protocols and is designed to be reviewed with a qualified Vaidya (BAMS/MD Ayurveda) before implementation. Do not self-administer Shodhana therapies (Vamana, Virechana, Niruha Basti). Share this plan at your next consultation.</p>
          </div>
        </div>
      )}

      {/* ── Clinical Decision Header ── */}
      <div className="pk-decision-header">
        <div className="pk-header-top-row">
          <div className="pk-dosha-pill" style={{ background: `${doshaColor}18`, borderColor: `${doshaColor}55`, color: doshaColor }}>
            Vikriti: {vikritiDom.toUpperCase()}
            {cd.vikriti_secondary ? ` + ${cd.vikriti_secondary.toUpperCase()}` : ''}
          </div>
          <div className={`pk-eligibility-badge ${isShodhana ? 'pk-shodhana' : 'pk-shamana'}`}>
            <ShieldCheck size={13} />
            {isShodhana ? 'Shodhana (Purification)' : 'Shamana (Palliative)'}
          </div>
        </div>

        {/* Agni + Bala + Ama + Ojas quick stats */}
        <div className="pk-vitals-row">
          {us.agni_type && (
            <div className="pk-vital-chip">
              <span className="pk-vital-k">Agni</span>
              <span className="pk-vital-v">{AGNI_LABEL[us.agni_type] || us.agni_name || us.agni_type}</span>
            </div>
          )}
          {(elig.bala || us.bala) && (
            <div className="pk-vital-chip">
              <span className="pk-vital-k">Bala</span>
              <span className="pk-vital-v">{BALA_LABEL[elig.bala || us.bala] || elig.bala_note || us.bala_note}</span>
            </div>
          )}
          {us.ama_indicator && us.ama_indicator !== 'none' && (
            <div className="pk-vital-chip pk-vital-warn">
              <span className="pk-vital-k">Ama</span>
              <span className="pk-vital-v">{us.ama_indicator}</span>
            </div>
          )}
          {us.ojas_level && (
            <div className="pk-vital-chip">
              <span className="pk-vital-k">Ojas</span>
              <span className="pk-vital-v">{us.ojas_level}</span>
            </div>
          )}
          {us.koshtha && (
            <div className="pk-vital-chip">
              <span className="pk-vital-k">Koshtha</span>
              <span className="pk-vital-v">
                {us.koshtha === 'krura' ? 'Krura (Hard)' : us.koshtha === 'mridu' ? 'Mridu (Loose)' : 'Sama (Regular)'}
              </span>
            </div>
          )}
        </div>

        {!isShodhana && elig.reasons?.length > 0 && (
          <p className="pk-shamana-reason">{elig.reasons[0]}</p>
        )}

        {elig.ama_correction_needed && (
          <div className="pk-ama-warning">
            <AlertTriangle size={13} />
            <span>Ama correction required first: {(elig.ama_correction_herbs || []).slice(0, 3).join(', ')} — {elig.ama_correction_duration}</span>
          </div>
        )}

        {/* Safety substitution alert */}
        {pk.safety_substitution && (
          <div className="pk-safety-sub">
            <AlertTriangle size={13} />
            <span>{pk.reason}</span>
          </div>
        )}

        {/* Per-karma safety warnings */}
        {(cd.safety_warnings || []).filter(() => !pk.safety_substitution).map((w, i) => (
          <div key={i} className="pk-ama-warning"><AlertTriangle size={13} /><span>{w}</span></div>
        ))}

        {/* Unmapped / rare disease notice */}
        {unmapped.length > 0 && (
          <div className="pk-unmapped-banner">
            <div className="pk-unmapped-title">
              <AlertTriangle size={13} /> Rare / Unmapped Conditions Detected — Vaidya Review Required
            </div>
            <div className="pk-unmapped-chips">
              {unmapped.map(c => (
                <span key={c} className="pk-unmapped-chip">
                  {c.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </span>
              ))}
            </div>
            <p className="pk-unmapped-note">
              These conditions are not in the classical Ayurvedic disease database. The AI has reasoned about them using Nidana-Samprapti inference below. All decisions must be reviewed by a qualified Vaidya (BAMS/MD Ayurveda) before proceeding.
            </p>
          </div>
        )}
      </div>

      {/* ── Pradhana Karma + Ritu row ── */}
      <div className="pk-info-row">
        <div className="pk-info-card">
          <div className="pk-info-label"><Beaker size={12} /> Selected Therapy</div>
          <div className="pk-info-value">{(pk.primary || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</div>
          {bs && <div className="pk-info-sub">{bs.name}</div>}
        </div>
        <div className="pk-info-card">
          <div className="pk-info-label"><Calendar size={12} /> Season (Ritu)</div>
          <div className="pk-info-value">{ritu.ritu_name || ritu.ritu || '—'}</div>
          <div className="pk-info-sub">Ideal: {(ritu.primary_shodhana || '—').toUpperCase()}</div>
        </div>
        <div className="pk-info-card">
          <div className="pk-info-label"><Sun size={12} /> Duration</div>
          <div className="pk-info-value">{ph.total_days || '—'} days</div>
          <div className="pk-info-sub">{ph.purvakarma_days}P · {ph.pradhana_karma_days}M · {ph.paschat_karma_days}R</div>
        </div>
      </div>

      {cd.ritu_warning && (
        <div className="pk-ritu-warning">
          <AlertTriangle size={13} /> {cd.ritu_warning}
        </div>
      )}

      {pk.reason && (
        <div className="pk-rationale">
          <span className="pk-rationale-label">Clinical Rationale</span>
          <p>{pk.reason}</p>
        </div>
      )}

      {/* ── Phase Timeline ── */}
      <div className="pk-phases">
        {[
          { key: 'purvakarma', label: 'Purvakarma', days: ph.purvakarma_days, sub: 'Snehana + Swedana (Preparation)' },
          { key: 'pradhana',   label: 'Pradhana Karma', days: ph.pradhana_karma_days, sub: (pk.primary || '').replace(/_/g, ' ') },
          { key: 'paschat',    label: 'Paschat Karma', days: ph.paschat_karma_days, sub: 'Samsarjana Krama + Rasayana' },
        ].map((phase, i) => {
          const Icon = PHASE_ICON[phase.key] || Sparkles
          return (
            <React.Fragment key={phase.key}>
              <div className="pk-phase-block">
                <div className="pk-phase-icon-wrap"><Icon size={15} /></div>
                <div className="pk-phase-days">{phase.days} days</div>
                <div className="pk-phase-name">{phase.label}</div>
                <div className="pk-phase-sub">{phase.sub}</div>
              </div>
              {i < 2 && <ArrowRight size={16} className="pk-phase-arrow" />}
            </React.Fragment>
          )
        })}
      </div>

      {/* ── Snehana Protocol ── */}
      {(sn.internal_ghrita || sn.abhyanga_oil) && (
        <div className="pk-section">
          <div className="pk-section-title"><Droplets size={14} /> Snehana Protocol (Internal + External Oleation)</div>
          <div className="pk-aus-grid">
            {sn.internal_ghrita && (
              <div className="pk-aus-card">
                <div className="pk-aus-label">Internal Snehana</div>
                <div className="pk-aus-name">
                  {typeof sn.internal_ghrita === 'object'
                    ? (sn.internal_ghrita.primary || sn.internal_ghrita.name || JSON.stringify(sn.internal_ghrita))
                    : sn.internal_ghrita}
                </div>
                {sn.dose_schedule?.length > 0 && (
                  <div className="pk-aus-sub">Day 1: {sn.dose_schedule[0]?.dose_ml}ml → Day {sn.dose_schedule.length}: {sn.dose_schedule[sn.dose_schedule.length - 1]?.dose_ml}ml</div>
                )}
              </div>
            )}
            {sn.abhyanga_oil && (
              <div className="pk-aus-card">
                <div className="pk-aus-label">Abhyanga Oil</div>
                <div className="pk-aus-name">
                  {typeof sn.abhyanga_oil === 'object'
                    ? (sn.abhyanga_oil.primary || sn.abhyanga_oil.name || sn.abhyanga_oil.medicated || '—')
                    : sn.abhyanga_oil}
                </div>
                {typeof sn.abhyanga_oil === 'object' && sn.abhyanga_oil.temperature && (
                  <div className="pk-aus-sub">{sn.abhyanga_oil.temperature}</div>
                )}
              </div>
            )}
          </div>
          {sn.signs_adequate?.length > 0 && (
            <div className="pk-signs">
              <div className="pk-signs-label">Signs of Adequate Snehana (Samyak Snigdha Lakshana)</div>
              <ul className="pk-signs-list">
                {sn.signs_adequate.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* ── Aushadha ── */}
      {aushadhaRows.length > 0 && (
        <div className="pk-section">
          <div className="pk-section-title"><Beaker size={14} /> Aushadha (Medicines & Oils)</div>
          <div className="pk-aus-grid">
            {aushadhaRows.map(([k, v]) => {
              const name = typeof v === 'object' ? (v.name || v.herb || v.primary || '') : v
              const desc = typeof v === 'object' ? (v.use || v.dose || v.rationale || '') : ''
              if (!name) return null
              return (
                <div key={k} className="pk-aus-card">
                  <div className="pk-aus-label">{k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</div>
                  <div className="pk-aus-name">{name}</div>
                  {desc && <div className="pk-aus-sub">{String(desc).slice(0, 80)}</div>}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ── Samsarjana Krama ── */}
      {sk.length > 0 && (
        <div className="pk-section">
          <div className="pk-section-title"><Leaf size={14} /> Samsarjana Krama (Dietary Re-entry)</div>
          <p className="pk-sk-intro">Critical post-Shodhana re-feeding protocol. Skipping this risks Dhatu Kshaya.</p>
          <div className="pk-sk-stages">
            {sk.map((stage, i) => (
              <div key={i} className="pk-sk-stage">
                <div className="pk-sk-num">{stage.stage || i + 1}</div>
                <div className="pk-sk-body">
                  <div className="pk-sk-food">{stage.food}</div>
                  {stage.recipe && <div className="pk-sk-recipe">{stage.recipe}</div>}
                  {stage.note && <div className="pk-sk-note">{stage.note}</div>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Daily Schedule ── */}
      {sch.length > 0 && (
        <div className="pk-section">
          <div className="pk-section-title"><Calendar size={14} /> Daily Schedule</div>
          <div className="pk-schedule">
            {sch.map((day) => (
              <div key={day.day} className="pk-day-row">
                <div className="pk-day-num">Day {day.day}</div>
                <div className="pk-day-phase">{(day.phase || '').split(' (')[0]}</div>
                <div className="pk-day-therapies">
                  {(day.therapies || []).map((t, i) => (
                    <span key={i} className="pk-therapy-chip">{t.name} · {t.duration_minutes}min</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Rare Disease Assessment (LLM Nidana-Samprapti inference) ── */}
      {rareAssessment && Object.keys(rareAssessment).length > 0 && (
        <div className="pk-section pk-rare-section">
          <div className="pk-section-title"><Sparkles size={14} /> Rare Disease Nidana-Samprapti Assessment</div>
          <p className="pk-sk-intro">AI-inferred Ayurvedic analysis for conditions outside classical mapping. Verify with a qualified Vaidya.</p>
          {Object.entries(rareAssessment).map(([condition, data]) => (
            <div key={condition} className="pk-rare-card">
              <div className="pk-rare-name">{condition.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</div>
              {data.nidana_samprapti && (
                <div className="pk-rare-row"><span className="pk-rare-k">Nidana-Samprapti</span><span>{data.nidana_samprapti}</span></div>
              )}
              {data.classical_analogue && (
                <div className="pk-rare-row"><span className="pk-rare-k">Classical Analogue</span><span>{data.classical_analogue}</span></div>
              )}
              {data.therapy_suitability && (
                <div className="pk-rare-row"><span className="pk-rare-k">Therapy Suitability</span><span>{data.therapy_suitability}</span></div>
              )}
              {data.suggested_aushadha && (
                <div className="pk-rare-row"><span className="pk-rare-k">Aushadha</span><span>{data.suggested_aushadha}</span></div>
              )}
              {data.vaidya_note && (
                <div className="pk-rare-row pk-rare-warn"><span className="pk-rare-k">Vaidya Monitor</span><span>{data.vaidya_note}</span></div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

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

      {/* ── Panchakarma dedicated view ── */}
      {planType === 'panchakarma' && plan.clinical_decisions && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.42, ease: [0.16, 1, 0.3, 1] }}
        >
          <PanchakarmaView plan={plan} />
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
