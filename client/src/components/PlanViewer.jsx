import React, { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Sun, PersonStanding, Dumbbell, Leaf, Coffee, Pill,
  Sparkles, FlaskConical, AlertTriangle, ChevronRight, Star,
  Droplets, Calendar, ShieldCheck, Flame, Beaker, ArrowRight,
  Moon, Timer, Zap, Target, Activity, ChevronDown, ChevronUp,
  Wind, Flower2, Brain, UtensilsCrossed, Clock, Soup, Apple,
  Cookie, Salad, CupSoda, BookOpen,
  Stethoscope, Layers, TestTube, Thermometer, Syringe, ListChecks,
  TriangleAlert, BadgeCheck, Repeat, HeartPulse,
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
  // Gym raw fields — rendered by GymView instead
  'weekly_schedule', 'four_week_plan', 'ayurvedic_tips', 'progressive_overload_note',
  'progressive_overload_guide', 'plan_title', 'plan_description', 'weekly_focus_notes',
  'nutrition_sync', 'recovery_protocol', 'progression_plan', 'ayurvedic_lifestyle_sync',
  'motivational_note',
  // Yoga raw fields — rendered by YogaView instead
  'daily_intention', 'breathing_guidance', 'lifestyle_sync',
  'condition_coaching', 'age_coaching', 'condition_protocols', 'seasonal_note',
  // Diet raw fields — rendered by DietView instead
  'meal_timing', 'spice_guide', 'daily_meal_ideas', 'hydration_guidance',
  'fasting_guidance', 'disclaimer', 'weekly_plan', 'pathya_apathya',
  'ahar_vidhi', 'condition_coaching', 'diet_weeks',
  // Remedy raw fields — rendered by RemedyView instead
  'symptoms_addressed', 'doctor_referrals', 'general_guidelines',
  'personalized_intro', 'synergy_note', 'recovery_timeline', 'prevention_tips',
  'when_to_escalate', 'ayurvedic_context', 'follow_up',
  'user_dosha', 'enrichment_error',
  // Medicine raw fields — rendered by MedicineView instead
  'primary_formulations', 'supporting_formulations', 'external_therapies',
  'dosage_schedule', 'lifestyle_guidance', 'blocked_medicines',
  'formulation_rationale', 'expected_timeline', 'dietary_guidelines',
  'when_to_stop', 'active_conditions', 'secondary_dosha',
  // New medicines fields
  'chikitsa_sutra', 'chikitsa_approach', 'vikriti_dominant', 'vikriti_secondary',
  'agni_type', 'ama_level', 'current_season', 'treatment_protocol',
  'expected_outcomes', 'pathya', 'apathya', 'viruddha_ahara_alerts',
  'dose_note', 'monitoring_signs', 'synergy_note',
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
                  {(day.therapies || []).map((t, i) =>
                    t.is_pradhana_karma ? (
                      <div key={i} className="pk-pradhana-action">
                        <div className="pk-pradhana-action-header">
                          <Flame size={12} className="pk-pradhana-flame" />
                          <span className="pk-pradhana-action-name">{t.name}</span>
                          {t.timing && <span className="pk-pradhana-timing">{t.timing}</span>}
                        </div>
                        {t.pradhana_notes && (
                          <p className="pk-pradhana-action-notes">{t.pradhana_notes}</p>
                        )}
                      </div>
                    ) : (
                      <span key={i} className="pk-therapy-chip">
                        {t.name}{t.duration_minutes ? ` · ${t.duration_minutes}min` : ''}
                      </span>
                    )
                  )}
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

// ── Gym dedicated renderer ─────────────────────────────────────────────────────
const WEEK_THEMES = ['Foundation', 'Volume Build', 'Intensity Peak', 'Deload']

function GymView({ plan }) {
  const [activeWeek, setActiveWeek] = useState(0)
  const [expandedEx, setExpandedEx] = useState(new Set())
  const [showAllActivities, setShowAllActivities] = useState(new Set())

  const us = plan.user_summary || {}
  const fourWeekPlan = plan.four_week_plan || []
  const fallbackDays = plan.weekly_schedule || []
  const activeWeekData = fourWeekPlan[activeWeek] || null
  const weekDays = activeWeekData?.days || (activeWeek === 0 ? fallbackDays : [])
  const weekPrescription = activeWeekData?.prescription || null
  const tips = plan.ayurvedic_tips || {}
  const overload = plan.progressive_overload_guide || plan.progressive_overload_note || null
  const nutrition = plan.nutrition_sync || {}
  const recovery = plan.recovery_protocol || {}

  const goalLabel = (us.gym_goal || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  const doshaColor = DOSHA_COLOR[us.dominant_dosha] || DOSHA_COLOR.default

  const toggleEx = (exId) => {
    setExpandedEx(prev => {
      const next = new Set(prev)
      next.has(exId) ? next.delete(exId) : next.add(exId)
      return next
    })
  }

  const toggleActivities = (dayIdx) => {
    setShowAllActivities(prev => {
      const next = new Set(prev)
      next.has(dayIdx) ? next.delete(dayIdx) : next.add(dayIdx)
      return next
    })
  }

  return (
    <div className="gym-view">

      {/* ── Motivational note ── */}
      {plan.motivational_note && (
        <div className="gym-motivational">{plan.motivational_note}</div>
      )}

      {/* ── Description ── */}
      {plan.plan_description && (
        <p className="gym-description">{plan.plan_description}</p>
      )}

      {/* ── Vitals summary bar ── */}
      <div className="gym-vitals">
        {goalLabel && (
          <div className="gym-vital-chip">
            <Target size={11} className="gym-vital-icon" />
            <span className="gym-vital-k">Goal</span>
            <span className="gym-vital-v">{goalLabel}</span>
          </div>
        )}
        {us.dominant_dosha && (
          <div className="gym-vital-chip" style={{ borderColor: `${doshaColor}44`, color: doshaColor }}>
            <span className="gym-vital-k">Dosha</span>
            <span className="gym-vital-v">{us.dominant_dosha.toUpperCase()}</span>
          </div>
        )}
        {us.fitness_level && (
          <div className="gym-vital-chip">
            <Activity size={11} className="gym-vital-icon" />
            <span className="gym-vital-k">Level</span>
            <span className="gym-vital-v">{us.fitness_level.replace(/\b\w/g, c => c.toUpperCase())}</span>
          </div>
        )}
        {us.strength_level && us.strength_level !== us.fitness_level && (
          <div className="gym-vital-chip">
            <Dumbbell size={11} className="gym-vital-icon" />
            <span className="gym-vital-k">Strength</span>
            <span className="gym-vital-v">{us.strength_level.replace(/\b\w/g, c => c.toUpperCase())}</span>
          </div>
        )}
        {us.workout_days && (
          <div className="gym-vital-chip">
            <Calendar size={11} className="gym-vital-icon" />
            <span className="gym-vital-k">Days</span>
            <span className="gym-vital-v">{us.workout_days}×/week</span>
          </div>
        )}
        {us.duration_per_session && (
          <div className="gym-vital-chip">
            <Timer size={11} className="gym-vital-icon" />
            <span className="gym-vital-k">Duration</span>
            <span className="gym-vital-v">{us.duration_per_session} min</span>
          </div>
        )}
      </div>

      {/* ── Week tabs ── */}
      <div className="gym-week-tabs">
        {WEEK_THEMES.map((theme, i) => (
          <button
            key={i}
            className={`gym-week-tab${activeWeek === i ? ' active' : ''}`}
            onClick={() => setActiveWeek(i)}
          >
            <span className="gym-tab-num">Week {i + 1}</span>
            <span className="gym-tab-theme">{theme}</span>
          </button>
        ))}
      </div>

      {/* ── Week coaching banner ── */}
      {weekPrescription?.note && (
        <div className="gym-week-banner">
          <span className="gym-week-banner-icon">💡</span>
          <span className="gym-week-banner-text">
            <strong>Week {activeWeek + 1} · {WEEK_THEMES[activeWeek]}:</strong> {weekPrescription.note}
          </span>
        </div>
      )}

      {/* ── Day cards ── */}
      <div className="gym-days-grid">
        {weekDays.map((day, dayIdx) => {
          const isRest = day.type === 'recovery' || !day.main_workout?.length
          const restRecovery = day.rest_day_recovery || null
          const showAllActs = showAllActivities.has(dayIdx)

          return (
            <div key={dayIdx} className={`gym-day-card${isRest ? ' rest' : ''}`}>
              <div className="gym-day-header">
                <div className="gym-day-name">
                  {isRest ? <Moon size={13} className="gym-rest-icon" /> : <Dumbbell size={13} className="gym-work-icon" />}
                  {day.day_name || `Day ${day.day}`}
                </div>
                <div className="gym-day-focus">{day.focus || 'Rest'}</div>
              </div>

              {isRest ? (
                restRecovery ? (
                  <div className="gym-rest-card rich">
                    <div className="gym-rest-title">{restRecovery.title}</div>
                    <ul className="gym-rest-activities">
                      {(showAllActs ? restRecovery.activities : restRecovery.activities?.slice(0, 3))
                        ?.map((act, k) => <li key={k}>{act}</li>)}
                    </ul>
                    {restRecovery.activities?.length > 3 && (
                      <button className="gym-show-more" onClick={() => toggleActivities(dayIdx)}>
                        {showAllActs ? '▲ Show less' : `▼ +${restRecovery.activities.length - 3} more`}
                      </button>
                    )}
                    {restRecovery.nutrition_note && (
                      <div className="gym-rest-meta-row">
                        <span className="gym-rest-meta-label">Nutrition:</span>
                        <span>{restRecovery.nutrition_note}</span>
                      </div>
                    )}
                    {restRecovery.sleep_note && (
                      <div className="gym-rest-meta-row">
                        <span className="gym-rest-meta-label">Sleep:</span>
                        <span>{restRecovery.sleep_note}</span>
                      </div>
                    )}
                    {restRecovery.ayurvedic_note && (
                      <p className="gym-rest-quote">{restRecovery.ayurvedic_note}</p>
                    )}
                  </div>
                ) : (
                  <p className="gym-rest-label">Rest & active recovery — let your body rebuild.</p>
                )
              ) : (
                <>
                  <div className="gym-day-meta">
                    {day.estimated_duration_minutes > 0 && (
                      <span className="gym-meta-chip"><Timer size={10} /> {day.estimated_duration_minutes} min</span>
                    )}
                    {day.calories_burned_estimate > 0 && (
                      <span className="gym-meta-chip"><Zap size={10} /> ~{day.calories_burned_estimate} kcal</span>
                    )}
                  </div>

                  {/* Warmup */}
                  {day.warmup?.length > 0 && (
                    <div className="gym-sub-section">
                      <div className="gym-section-label">Warmup</div>
                      <ul className="gym-sub-list">
                        {day.warmup.map((w, j) => <li key={j} className="gym-list-item">{w}</li>)}
                      </ul>
                    </div>
                  )}

                  {/* Exercises */}
                  {day.main_workout?.length > 0 && (
                    <div className="gym-sub-section">
                      <div className="gym-section-label">Exercises</div>
                      <div className="gym-exercise-list">
                        {day.main_workout.map((ex, j) => {
                          const exId = `${dayIdx}-${j}`
                          const isExpanded = expandedEx.has(exId)
                          const isBodyweight = (ex.weight_range || '').startsWith('Bodyweight') || (ex.weight_range || '').startsWith('Effort')
                          return (
                            <div key={j} className="gym-exercise-row">
                              <div className="gym-ex-top">
                                <span className="gym-ex-name">{ex.exercise_name || ex.name}</span>
                                <div className="gym-ex-chips">
                                  <span className="gym-ex-badge">{ex.sets} × {ex.reps}</span>
                                  {ex.rest_seconds && <span className="gym-ex-rest">{ex.rest_seconds}s rest</span>}
                                  {ex.equipment && ex.equipment !== 'bodyweight' && (
                                    <span className="gym-ex-equip">{ex.equipment}</span>
                                  )}
                                </div>
                              </div>
                              {ex.weight_range && (
                                <div className={`gym-weight-range${isBodyweight ? '' : ' kg'}`}>
                                  <Dumbbell size={10} style={{ display: 'inline', marginRight: '0.25rem', verticalAlign: 'middle' }} />
                                  {ex.weight_range}
                                </div>
                              )}
                              {ex.notes && <p className="gym-ex-notes">{ex.notes}</p>}
                              {ex.instructions?.length > 0 && (
                                <>
                                  <button className="gym-instructions-toggle" onClick={() => toggleEx(exId)}>
                                    {isExpanded ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
                                    {isExpanded ? 'Hide instructions' : 'How to perform'}
                                  </button>
                                  {isExpanded && (
                                    <ol className="gym-instructions-panel">
                                      {ex.instructions.map((step, s) => (
                                        <li key={s} className="gym-instructions-item">{step}</li>
                                      ))}
                                    </ol>
                                  )}
                                </>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}

                  {/* Cooldown */}
                  {day.cooldown?.length > 0 && (
                    <div className="gym-sub-section">
                      <div className="gym-section-label">Cooldown</div>
                      <ul className="gym-sub-list">
                        {day.cooldown.map((c, j) => <li key={j} className="gym-list-item">{c}</li>)}
                      </ul>
                    </div>
                  )}
                </>
              )}
            </div>
          )
        })}
      </div>

      {/* ── Ayurvedic Tips ── */}
      {Object.keys(tips).length > 0 && (
        <div className="gym-tips-section">
          <div className="gym-tips-title"><Leaf size={14} /> Ayurvedic Training Tips</div>
          <div className="gym-tips-grid">
            {[
              { key: 'best_time_to_workout', label: 'Best Time' },
              { key: 'pre_workout', label: 'Pre-Workout' },
              { key: 'post_workout', label: 'Post-Workout' },
              { key: 'recovery', label: 'Recovery' },
            ].map(({ key, label }) => tips[key] ? (
              <div key={key} className="gym-tip-card">
                <div className="gym-tip-label">{label}</div>
                <p className="gym-tip-text">{tips[key]}</p>
              </div>
            ) : null)}
          </div>
        </div>
      )}

      {/* ── Progressive overload guide ── */}
      {overload && (
        <div className="gym-progression-section">
          <div className="gym-tips-title"><Activity size={14} /> Progressive Overload Guide</div>
          {typeof overload === 'string' ? (
            <p className="gym-progression-note">{overload}</p>
          ) : (
            <table className="gym-progression-table">
              <thead>
                <tr><th>Week</th><th>Theme</th><th>Focus</th></tr>
              </thead>
              <tbody>
                {Object.entries(overload).map(([wk, desc], i) => (
                  <tr key={wk}>
                    <td>{i + 1}</td>
                    <td>{WEEK_THEMES[i] || wk}</td>
                    <td>{desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* ── Nutrition sync ── */}
      {Object.keys(nutrition).length > 0 && (
        <div className="gym-nutrition-section">
          <div className="gym-tips-title"><Flame size={14} /> Nutrition Sync</div>
          <div className="gym-nutrition-grid">
            {[
              { key: 'pre_workout_meal', label: 'Pre-Workout Meal' },
              { key: 'post_workout_meal', label: 'Post-Workout Meal' },
              { key: 'hydration', label: 'Hydration' },
            ].map(({ key, label }) => nutrition[key] ? (
              <div key={key} className="gym-nutrition-card">
                <div className="gym-tip-label">{label}</div>
                <p className="gym-tip-text">{nutrition[key]}</p>
              </div>
            ) : null)}
          </div>
        </div>
      )}

      {/* ── Recovery protocol ── */}
      {(recovery.sleep || recovery.active_recovery || recovery.signs_of_overtraining?.length) && (
        <div className="gym-recovery-section">
          <div className="gym-tips-title"><Moon size={14} /> Recovery Protocol</div>
          <div className="gym-tips-grid">
            {recovery.sleep && (
              <div className="gym-tip-card">
                <div className="gym-tip-label">Sleep</div>
                <p className="gym-tip-text">{recovery.sleep}</p>
              </div>
            )}
            {recovery.active_recovery && (
              <div className="gym-tip-card">
                <div className="gym-tip-label">Active Recovery</div>
                <p className="gym-tip-text">{recovery.active_recovery}</p>
              </div>
            )}
          </div>
          {recovery.signs_of_overtraining?.length > 0 && (
            <div className="gym-overtraining">
              <div className="gym-tip-label" style={{ marginBottom: '0.4rem' }}>Signs of Overtraining — Back Off</div>
              <ul className="gym-sub-list">
                {recovery.signs_of_overtraining.map((s, i) => <li key={i} className="gym-list-item">{s}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}


// ── Surya Namaskar card ───────────────────────────────────────────────────────
const SNS_BREATH_COLOR = { 'Inhale': '#3b82f6', 'Exhale': '#ef4444', 'Natural': '#6b7280', 'Exhale — hold 3-5 breaths': '#ef4444' }

function SuryaNamaskarCard({ sns }) {
  const [open, setOpen] = useState(false)
  const pace = (sns.pace || '').replace(/\b\w/g, c => c.toUpperCase())
  return (
    <div className="sns-card">
      <div className="sns-header">
        <div className="sns-title-row">
          <Sun size={14} className="sns-sun-icon" />
          <span className="sns-title">Surya Namaskar</span>
          <span className="sns-sanskrit">सूर्य नमस्कार</span>
        </div>
        <div className="sns-meta">
          <span className="sns-badge">{sns.rounds} round{sns.rounds > 1 ? 's' : ''}</span>
          <span className="sns-badge pace">{pace}</span>
          <span className="sns-badge dur">{sns.duration_minutes} min</span>
        </div>
      </div>

      <p className="sns-pace-note">{sns.pace_note}</p>

      {sns.senior_modification && (
        <div className="sns-senior-note">
          <ShieldCheck size={11} /> {sns.senior_modification}
        </div>
      )}

      {sns.safety_notes?.length > 0 && (
        <div className="sns-warnings">
          {sns.safety_notes.map((w, i) => (
            <div key={i} className="sns-warning-row">
              <AlertTriangle size={11} className="sns-warn-icon" />
              <span>{w}</span>
            </div>
          ))}
        </div>
      )}

      <button className="sns-toggle" onClick={() => setOpen(o => !o)}>
        {open ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
        {open ? 'Hide 12 steps' : 'Show 12 steps'}
      </button>

      {open && (
        <div className="sns-steps">
          {sns.steps.map((step) => {
            const breathColor = SNS_BREATH_COLOR[step.breath] || '#6b7280'
            return (
              <div key={step.step} className="sns-step-row">
                <div className="sns-step-num">{step.step}</div>
                <div className="sns-step-body">
                  <div className="sns-step-names">
                    <span className="sns-step-sanskrit">{step.sanskrit}</span>
                    <span className="sns-step-english">{step.english}</span>
                    {step.breath && step.breath !== 'Natural' && (
                      <span className="sns-breath-pill" style={{ color: breathColor, borderColor: `${breathColor}44`, background: `${breathColor}12` }}>
                        {step.breath.replace('Exhale — hold 3-5 breaths', 'Exhale + hold')}
                      </span>
                    )}
                  </div>
                  <p className="sns-step-cue">{step.cue}</p>
                  {step.modification && (
                    <p className="sns-step-mod">{step.modification}</p>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {sns.classical_reference && !open && (
        <p className="sns-classical-ref">{sns.classical_reference.split('.')[0]}.</p>
      )}
      {open && sns.classical_reference && (
        <p className="sns-classical-ref">{sns.classical_reference}</p>
      )}
    </div>
  )
}

// ── Yoga dedicated renderer ────────────────────────────────────────────────────
const YOGA_WEEK_THEMES = ['Foundation', 'Deepen', 'Challenge', 'Integration']

function YogaView({ plan }) {
  const [activeWeek, setActiveWeek] = useState(0)
  const [expandedPoses, setExpandedPoses] = useState(new Set())
  const [expandedWarmup, setExpandedWarmup] = useState(new Set())
  const [expandedCooldown, setExpandedCooldown] = useState(new Set())
  const [expandedPrana, setExpandedPrana] = useState(new Set())
  const [expandedDharana, setExpandedDharana] = useState(new Set())

  const us = plan.user_summary || {}
  const fourWeekPlan = plan.four_week_plan || []
  const activeWeekData = fourWeekPlan[activeWeek] || null
  const weekDays = activeWeekData?.days || []
  const weekNote = activeWeekData?.note || null
  const tips = plan.ayurvedic_tips || {}
  const dailyIntention = plan.daily_intention || {}

  const doshaColor = DOSHA_COLOR[us.dominant_dosha] || DOSHA_COLOR.default
  const goalLabel = (us.yoga_goal || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  const styleLabel = Array.isArray(us.style_preference)
    ? us.style_preference.join(', ')
    : (us.style_preference || '')

  const togglePose = (id) => setExpandedPoses(prev => {
    const next = new Set(prev); next.has(id) ? next.delete(id) : next.add(id); return next
  })
  const toggleWarmup = (dayIdx) => setExpandedWarmup(prev => {
    const next = new Set(prev); next.has(dayIdx) ? next.delete(dayIdx) : next.add(dayIdx); return next
  })
  const toggleCooldown = (dayIdx) => setExpandedCooldown(prev => {
    const next = new Set(prev); next.has(dayIdx) ? next.delete(dayIdx) : next.add(dayIdx); return next
  })
  const togglePrana = (dayIdx) => setExpandedPrana(prev => {
    const next = new Set(prev); next.has(dayIdx) ? next.delete(dayIdx) : next.add(dayIdx); return next
  })
  const toggleDharana = (dayIdx) => setExpandedDharana(prev => {
    const next = new Set(prev); next.has(dayIdx) ? next.delete(dayIdx) : next.add(dayIdx); return next
  })

  return (
    <div className="yoga-view">
      {plan.plan_description && (
        <p className="yoga-description">{plan.plan_description}</p>
      )}

      {/* ── Age group + medical conditions banner ── */}
      <div className="yoga-banners-row">
        {us.age_group && us.age_group !== 'adult' && (
          <div className={`yoga-age-badge ${us.age_group}`}>
            {us.age_group === 'senior' ? '🌿 Senior-Adapted Practice' : '⚡ Youth Practice'}
          </div>
        )}
        {us.medical_conditions?.length > 0 && (
          <div className="yoga-medical-banner">
            <span className="yoga-medical-label">Personalised for:</span>
            {us.medical_conditions.map(c => (
              <span key={c} className="yoga-medical-chip">{c.replace(/_/g, ' ')}</span>
            ))}
          </div>
        )}
      </div>

      {/* ── Seasonal note ── */}
      {plan.seasonal_note && (
        <div className="yoga-seasonal-note">
          <Leaf size={12} />
          <span>{plan.seasonal_note}</span>
        </div>
      )}

      {/* ── Vitals bar ── */}
      <div className="yoga-vitals">
        {goalLabel && (
          <div className="yoga-vital-chip">
            <Target size={11} /><span className="yoga-vital-k">Goal</span><span className="yoga-vital-v">{goalLabel}</span>
          </div>
        )}
        {us.dominant_dosha && (
          <div className="yoga-vital-chip" style={{ borderColor: `${doshaColor}44`, color: doshaColor }}>
            <span className="yoga-vital-k">Dosha</span><span className="yoga-vital-v">{us.dominant_dosha.toUpperCase()}</span>
          </div>
        )}
        {us.experience && (
          <div className="yoga-vital-chip">
            <Activity size={11} /><span className="yoga-vital-k">Level</span>
            <span className="yoga-vital-v">{us.experience.replace(/\b\w/g, c => c.toUpperCase())}</span>
          </div>
        )}
        {styleLabel && (
          <div className="yoga-vital-chip">
            <Flower2 size={11} /><span className="yoga-vital-k">Style</span><span className="yoga-vital-v">{styleLabel}</span>
          </div>
        )}
        {us.time_available && (
          <div className="yoga-vital-chip">
            <Timer size={11} /><span className="yoga-vital-k">Duration</span><span className="yoga-vital-v">{us.time_available} min</span>
          </div>
        )}
        {us.time_of_day && (
          <div className="yoga-vital-chip">
            <Sun size={11} /><span className="yoga-vital-k">Time</span>
            <span className="yoga-vital-v">{us.time_of_day.replace(/\b\w/g, c => c.toUpperCase())}</span>
          </div>
        )}
        {us.agni_type && (
          <div className="yoga-vital-chip yoga-vital-agni">
            <Flame size={11} /><span className="yoga-vital-k">Agni</span>
            <span className="yoga-vital-v">{us.agni_type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</span>
          </div>
        )}
        {us.ojas_level && (
          <div className="yoga-vital-chip yoga-vital-ojas">
            <Droplets size={11} /><span className="yoga-vital-k">Ojas</span>
            <span className="yoga-vital-v">{us.ojas_level.replace(/\b\w/g, c => c.toUpperCase())}</span>
          </div>
        )}
        {us.stress_level && us.stress_level !== 'low' && (
          <div className="yoga-vital-chip yoga-vital-stress">
            <Zap size={11} /><span className="yoga-vital-k">Stress</span>
            <span className="yoga-vital-v">{us.stress_level.replace(/\b\w/g, c => c.toUpperCase())}</span>
          </div>
        )}
      </div>

      {/* ── Condition protocol cards ── */}
      {plan.condition_protocols?.length > 0 && (
        <div className="yoga-protocols">
          {plan.condition_protocols.map((proto, pi) => (
            <details key={pi} className="yoga-protocol-card">
              <summary className="yoga-protocol-summary">
                <span className="yoga-protocol-condition">{proto.condition.replace(/_/g, ' ')}</span>
                <span className="yoga-protocol-name">{proto.protocol_name}</span>
              </summary>
              <div className="yoga-protocol-body">
                {proto.sequence_note && <p className="yoga-protocol-seq">{proto.sequence_note}</p>}
                {proto.lifestyle_note && <p className="yoga-protocol-life">{proto.lifestyle_note}</p>}
                {proto.research_note && <p className="yoga-protocol-research">{proto.research_note}</p>}
                {proto.classical_reference && (
                  <p className="yoga-protocol-ref">{proto.classical_reference}</p>
                )}
              </div>
            </details>
          ))}
        </div>
      )}

      {/* ── Age coaching (LLM-generated for senior/youth) ── */}
      {plan.age_coaching && (
        <div className="yoga-age-coaching">
          <p className="yoga-age-coaching-text">{plan.age_coaching}</p>
        </div>
      )}

      {/* ── Condition coaching (LLM-generated, only when user has conditions) ── */}
      {plan.condition_coaching && (
        <div className="yoga-condition-coaching">
          <p className="yoga-condition-coaching-text">{plan.condition_coaching}</p>
        </div>
      )}

      {/* ── Week tabs ── */}
      <div className="yoga-week-tabs">
        {YOGA_WEEK_THEMES.map((theme, i) => (
          <button
            key={i}
            className={`yoga-week-tab${activeWeek === i ? ' active' : ''}`}
            onClick={() => setActiveWeek(i)}
          >
            <span className="yoga-tab-num">Week {i + 1}</span>
            <span className="yoga-tab-theme">{theme}</span>
          </button>
        ))}
      </div>

      {/* ── Week note banner ── */}
      {weekNote && (
        <div className="yoga-week-banner">
          <span className="yoga-week-banner-icon">🌿</span>
          <span className="yoga-week-banner-text">
            <strong>Week {activeWeek + 1} · {YOGA_WEEK_THEMES[activeWeek]}:</strong> {weekNote}
          </span>
        </div>
      )}

      {/* ── Day cards ── */}
      <div className="yoga-days-grid">
        {weekDays.map((day, dayIdx) => {
          const isRest = day.rest || !day.session
          const session = day.session || {}
          const intention = dailyIntention[day.day_name] || null
          const warmupOpen = expandedWarmup.has(dayIdx)
          const cooldownOpen = expandedCooldown.has(dayIdx)

          return (
            <div key={dayIdx} className={`yoga-day-card${isRest ? ' rest' : ''}`}>
              <div className="yoga-day-header">
                <div className="yoga-day-name">
                  {isRest ? <Moon size={13} /> : <Flower2 size={13} />}
                  {day.day_name || `Day ${day.day}`}
                </div>
                {!isRest && session.total_duration_minutes && (
                  <span className="yoga-duration-badge-sm">{session.total_duration_minutes} min</span>
                )}
              </div>

              {isRest ? (
                <div className="yoga-rest-card">
                  <p className="yoga-rest-tip">Let your body absorb the week's practice. Gentle movement and stillness are welcome.</p>
                </div>
              ) : (
                <>
                  {session.dosha_theme && (
                    <p className="yoga-session-theme">{session.dosha_theme}</p>
                  )}
                  {intention && (
                    <div className="yoga-day-intention">&ldquo;{intention}&rdquo;</div>
                  )}

                  {/* Surya Namaskar flow */}
                  {session.surya_namaskar && (
                    <SuryaNamaskarCard sns={session.surya_namaskar} />
                  )}

                  {/* Warmup collapsible */}
                  {session.warmup?.length > 0 && (
                    <div className="yoga-section-block">
                      <button className="yoga-section-toggle" onClick={() => toggleWarmup(dayIdx)}>
                        <span className="yoga-section-label">Warmup ({session.warmup.length})</span>
                        {warmupOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                      </button>
                      {warmupOpen && (
                        <ul className="yoga-pose-list">
                          {session.warmup.map((p, pi) => (
                            <li key={pi} className="yoga-warmup-pose">
                              <span className="yoga-wp-name">{p.pose_name}</span>
                              {p.duration_seconds && <span className="yoga-wp-dur">{p.duration_seconds}s</span>}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}

                  {/* Main sequence */}
                  {session.main_sequence?.length > 0 && (
                    <div className="yoga-section-block">
                      <div className="yoga-section-label standalone">Main Practice ({session.main_sequence.length} poses)</div>
                      <div className="yoga-main-list">
                        {session.main_sequence.map((p, pi) => {
                          const poseId = `${dayIdx}-main-${pi}`
                          const isOpen = expandedPoses.has(poseId)
                          const hasValidImg = p.image_url && !p.image_url.startsWith('https://...')
                          return (
                            <div key={pi} className="yoga-pose-row">
                              <div className="yoga-pose-top">
                                <div className="yoga-pose-name-block">
                                  <span className="yoga-pose-name">{p.pose_name}</span>
                                  {p.sanskrit_name && (
                                    <span className="yoga-pose-sanskrit">{p.sanskrit_name}</span>
                                  )}
                                </div>
                                <div className="yoga-pose-chips">
                                  {p.duration_seconds && (
                                    <span className="yoga-duration-badge">{p.duration_seconds}s</span>
                                  )}
                                  {p.category && (
                                    <span className="yoga-category-chip">{p.category}</span>
                                  )}
                                </div>
                              </div>
                              {p.primary_benefits?.length > 0 && (
                                <ul className="yoga-pose-benefits">
                                  {p.primary_benefits.slice(0, 2).map((b, bi) => <li key={bi}>{b}</li>)}
                                </ul>
                              )}
                              {(p.instructions?.length > 0 || p.modification || p.ayurvedic_rationale) && (
                                <>
                                  <button className="yoga-pose-expand-toggle" onClick={() => togglePose(poseId)}>
                                    {isOpen ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
                                    {isOpen ? 'Less' : 'Details'}
                                  </button>
                                  {isOpen && (
                                    <div className="yoga-pose-expand">
                                      {hasValidImg && (
                                        <img src={p.image_url} alt={p.pose_name} className="yoga-pose-image" />
                                      )}
                                      {p.instructions?.length > 0 && (
                                        <ol className="yoga-pose-instructions">
                                          {p.instructions.map((step, si) => <li key={si}>{step}</li>)}
                                        </ol>
                                      )}
                                      {p.modification && (
                                        <p className="yoga-pose-modification">Modification: {p.modification}</p>
                                      )}
                                      {p.ayurvedic_rationale && (
                                        <p className="yoga-pose-rationale">{p.ayurvedic_rationale}</p>
                                      )}
                                    </div>
                                  )}
                                </>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}

                  {/* Cooldown collapsible */}
                  {session.cooldown?.length > 0 && (
                    <div className="yoga-section-block">
                      <button className="yoga-section-toggle" onClick={() => toggleCooldown(dayIdx)}>
                        <span className="yoga-section-label">Cooldown ({session.cooldown.length})</span>
                        {cooldownOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                      </button>
                      {cooldownOpen && (
                        <ul className="yoga-pose-list">
                          {session.cooldown.map((p, pi) => (
                            <li key={pi} className="yoga-warmup-pose">
                              <span className="yoga-wp-name">{p.pose_name}</span>
                              {p.duration_seconds && <span className="yoga-wp-dur">{p.duration_seconds}s</span>}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}

                  {/* Pranayama */}
                  {session.pranayama_section?.length > 0 && (() => {
                    const pr = session.pranayama_section[0]
                    const pranaOpen = expandedPrana.has(dayIdx)
                    const hasInstructions = pr.instructions?.length > 0
                    return (
                      <div className="yoga-prana-card">
                        <div className="yoga-prana-header">
                          <Wind size={12} className="yoga-prana-icon" />
                          <span className="yoga-prana-name">
                            {pr.technique_name}
                            {pr.sanskrit_name && (
                              <span className="yoga-prana-sanskrit"> · {pr.sanskrit_name}</span>
                            )}
                          </span>
                          {pr.duration_minutes && (
                            <span className="yoga-prana-dur">{pr.duration_minutes} min</span>
                          )}
                        </div>
                        {pr.dosha_note && (
                          <p className="yoga-prana-dosha-note">{pr.dosha_note}</p>
                        )}
                        {hasInstructions && (
                          <>
                            <button className="yoga-pose-expand-toggle" onClick={() => togglePrana(dayIdx)}>
                              {pranaOpen ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
                              {pranaOpen ? 'Less' : 'Instructions'}
                            </button>
                            {pranaOpen && (
                              <ol className="yoga-pose-instructions yoga-prana-instructions">
                                {pr.instructions.map((step, si) => <li key={si}>{step}</li>)}
                              </ol>
                            )}
                          </>
                        )}
                      </div>
                    )
                  })()}

                  {/* Dharana / Meditation slot */}
                  {session.dharana_section && (() => {
                    const dh = session.dharana_section
                    const dharanaOpen = expandedDharana.has(dayIdx)
                    return (
                      <div className="yoga-dharana-card">
                        <div className="yoga-dharana-header">
                          <Brain size={12} className="yoga-dharana-icon" />
                          <span className="yoga-dharana-name">
                            {dh.technique}
                            {dh.sanskrit_name && (
                              <span className="yoga-dharana-sanskrit"> · {dh.sanskrit_name}</span>
                            )}
                          </span>
                          {dh.duration_minutes && (
                            <span className="yoga-dharana-dur">{dh.duration_minutes} min</span>
                          )}
                        </div>
                        {dh.dosha_note && (
                          <p className="yoga-dharana-dosha-note">{dh.dosha_note}</p>
                        )}
                        {dh.instructions?.length > 0 && (
                          <>
                            <button className="yoga-pose-expand-toggle" onClick={() => toggleDharana(dayIdx)}>
                              {dharanaOpen ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
                              {dharanaOpen ? 'Less' : 'How to practice'}
                            </button>
                            {dharanaOpen && (
                              <>
                                <ol className="yoga-pose-instructions yoga-dharana-instructions">
                                  {dh.instructions.map((step, si) => <li key={si}>{step}</li>)}
                                </ol>
                                {dh.classical_reference && (
                                  <p className="yoga-dharana-ref">{dh.classical_reference}</p>
                                )}
                              </>
                            )}
                          </>
                        )}
                      </div>
                    )
                  })()}
                </>
              )}
            </div>
          )
        })}
      </div>

      {/* ── Ayurvedic Tips ── */}
      {Object.keys(tips).length > 0 && (
        <div className="yoga-tips-section">
          <div className="yoga-tips-title"><Leaf size={14} /> Ayurvedic Practice Tips</div>
          <div className="yoga-tips-grid">
            {[
              { key: 'best_time', label: 'Best Time' },
              { key: 'environment', label: 'Environment' },
              { key: 'what_to_wear', label: 'What to Wear' },
              { key: 'after_practice', label: 'After Practice' },
            ].map(({ key, label }) => tips[key] ? (
              <div key={key} className="yoga-tip-card">
                <div className="yoga-tip-label">{label}</div>
                <p className="yoga-tip-text">{tips[key]}</p>
              </div>
            ) : null)}
          </div>
          {tips.dosha_note && <p className="yoga-dosha-note">{tips.dosha_note}</p>}
        </div>
      )}

      {/* ── Enrichment cards ── */}
      {plan.breathing_guidance && (
        <div className="yoga-enrichment-card">
          <div className="yoga-enrichment-label"><Wind size={13} /> Breathing Guidance</div>
          <p className="yoga-enrichment-text">{plan.breathing_guidance}</p>
        </div>
      )}
      {plan.lifestyle_sync && (
        <div className="yoga-enrichment-card">
          <div className="yoga-enrichment-label"><Leaf size={13} /> Lifestyle Sync</div>
          <p className="yoga-enrichment-text">{plan.lifestyle_sync}</p>
        </div>
      )}
      {plan.motivational_note && (
        <div className="yoga-motivational">{plan.motivational_note}</div>
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

// ── Diet dedicated renderer ───────────────────────────────────────────────────
const DIET_MEAL_ICONS = {
  breakfast: Coffee,
  lunch:     Soup,
  snack:     Apple,
  dinner:    UtensilsCrossed,
}
const DIET_DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const DIET_DAY_FULL   = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

function MacroBar({ macros }) {
  const cal = macros?.calories || 0
  const pro = macros?.protein_g || 0
  const carb = macros?.carbs_g || 0
  const fat = macros?.fat_g || 0
  return (
    <div className="diet-macro-bar">
      {cal > 0 && <div className="diet-macro-chip cal"><Flame size={10} />{Math.round(cal)} kcal</div>}
      {pro > 0 && <div className="diet-macro-chip pro"><span>P</span>{pro}g</div>}
      {carb > 0 && <div className="diet-macro-chip carb"><span>C</span>{carb}g</div>}
      {fat > 0 && <div className="diet-macro-chip fat"><span>F</span>{fat}g</div>}
    </div>
  )
}

// ── LLM Meal Card (primary — for weekly_plan structure) ───────────────────────
function LLMMealCard({ mealName, meal }) {
  const [open, setOpen] = useState(false)
  const MealIcon = DIET_MEAL_ICONS[mealName] || UtensilsCrossed
  const label = mealName.charAt(0).toUpperCase() + mealName.slice(1)
  if (!meal?.meal_name) return null
  return (
    <div className={`diet-meal-card llm meal-${mealName}${meal.allergen_warning ? ' has-allergen' : ''}`}>
      {meal.allergen_warning && (
        <div className="diet-allergen-warning">
          Allergen detected: {meal.allergen_terms?.join(', ')}
        </div>
      )}
      <div className="diet-meal-header" onClick={() => setOpen(o => !o)}>
        <div className="diet-meal-title-row">
          <MealIcon size={13} className="diet-meal-icon" />
          <div className="diet-meal-title-stack">
            <span className="diet-meal-label">{label}</span>
            <span className="diet-meal-name-llm">{meal.meal_name}</span>
          </div>
        </div>
        <div className="diet-meal-meta">
          {meal.macros_approx?.calories > 0 && (
            <span className="diet-meal-cal-badge">{Math.round(meal.macros_approx.calories)} cal</span>
          )}
          {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </div>
      </div>

      {open && (
        <div className="diet-llm-body">
          {meal.description && (
            <p className="diet-llm-desc">{meal.description}</p>
          )}
          {meal.key_ingredients?.length > 0 && (
            <div className="diet-ing-chips">
              {meal.key_ingredients.map((ing, i) => (
                <span key={i} className="diet-ing-chip">{ing}</span>
              ))}
            </div>
          )}
          {meal.portion && (
            <div className="diet-llm-portion">
              <UtensilsCrossed size={11} /> {meal.portion}
            </div>
          )}
          {meal.ayurvedic_note && (
            <div className="diet-llm-ayur-note">
              <Leaf size={11} className="diet-llm-ayur-icon" />
              <p>{meal.ayurvedic_note}</p>
            </div>
          )}
          {meal.macros_approx && (
            <MacroBar macros={meal.macros_approx} />
          )}
        </div>
      )}
    </div>
  )
}

// ── Pathya-Apathya Card ───────────────────────────────────────────────────────
function PathyaApathyaCard({ pa }) {
  const [open, setOpen] = useState(false)
  if (!pa) return null
  const hasContent = pa.pathya?.length || pa.apathya?.length || pa.viruddha_ahara_warnings?.length
  if (!hasContent) return null
  return (
    <div className="diet-pa-card">
      <button className="diet-timing-toggle" onClick={() => setOpen(o => !o)}>
        <ShieldCheck size={13} className="diet-timing-icon" style={{ color: '#16a34a' }} />
        <span>Pathya-Apathya — Classical Diet Protocol</span>
        {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>
      {open && (
        <div className="diet-pa-body">
          {pa.classical_reference && (
            <div className="diet-pa-ref">
              <Star size={11} /> {pa.classical_reference}
            </div>
          )}
          {pa.pathya?.length > 0 && (
            <div className="diet-pa-section">
              <div className="diet-pa-section-title pathya">Pathya — Recommended</div>
              <ul className="diet-pa-list">
                {pa.pathya.map((item, i) => <li key={i}>{item}</li>)}
              </ul>
            </div>
          )}
          {pa.apathya?.length > 0 && (
            <div className="diet-pa-section">
              <div className="diet-pa-section-title apathya">Apathya — Avoid</div>
              <ul className="diet-pa-list apathya">
                {pa.apathya.map((item, i) => <li key={i}>{item}</li>)}
              </ul>
            </div>
          )}
          {pa.viruddha_ahara_warnings?.length > 0 && (
            <div className="diet-pa-section">
              <div className="diet-pa-section-title viruddha">Viruddha Ahara Warnings</div>
              <ul className="diet-pa-list viruddha">
                {pa.viruddha_ahara_warnings.map((item, i) => (
                  <li key={i}><AlertTriangle size={10} className="diet-pa-warn-icon" />{item}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function DietView({ plan }) {
  const [activeDay, setActiveDay] = useState(0)
  const [activeWeek, setActiveWeek] = useState(0)
  const [timingOpen, setTimingOpen] = useState(false)
  const [spiceOpen, setSpiceOpen] = useState(false)

  const us = plan.user_summary || {}
  const isLLM = !!plan.weekly_plan
  const doshaColor = DOSHA_COLOR[us.dominant_dosha] || DOSHA_COLOR.default
  const goalLabel = (us.diet_goal || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  const agniLabel = (us.agni_type || '').replace(/\b\w/g, c => c.toUpperCase())

  // Multi-week LLM path
  const dietWeeks = plan.diet_weeks || []
  const isMultiWeek = isLLM && dietWeeks.length > 0
  const currentWeek = dietWeeks[activeWeek] || null

  // LLM path: weekly_plan = week 1 daily for day-level access
  const weeklyPlan = isMultiWeek
    ? (currentWeek?.daily_plan || plan.weekly_plan || {})
    : (plan.weekly_plan || {})
  const currentDayName = DIET_DAY_FULL[activeDay] || 'Monday'
  const dayData = weeklyPlan[currentDayName] || {}

  // Fallback path: four_week_plan array
  const fallbackDays = (plan.four_week_plan?.[0]?.days) || []
  const fallbackDay = fallbackDays[activeDay] || {}
  const timing = plan.meal_timing || {}

  return (
    <div className="diet-view">

      {/* ── Header ── */}
      {plan.plan_title && (
        <h2 className="diet-plan-title">{plan.plan_title}</h2>
      )}
      {plan.motivational_note && (
        <div className="diet-motivational">{plan.motivational_note}</div>
      )}
      {plan.plan_description && (
        <p className="diet-description">{plan.plan_description}</p>
      )}

      {/* ── Vitals bar ── */}
      <div className="diet-vitals">
        {goalLabel && (
          <div className="diet-vital-chip">
            <Target size={11} className="diet-vital-icon" />
            <span className="diet-vital-k">Goal</span>
            <span className="diet-vital-v">{goalLabel}</span>
          </div>
        )}
        {us.dominant_dosha && (
          <div className="diet-vital-chip" style={{ borderColor: `${doshaColor}44`, color: doshaColor }}>
            <span className="diet-vital-k">Dosha</span>
            <span className="diet-vital-v">{us.dominant_dosha.toUpperCase()}</span>
          </div>
        )}
        {us.agni_type && (
          <div className="diet-vital-chip">
            <Flame size={11} className="diet-vital-icon" />
            <span className="diet-vital-k">Agni</span>
            <span className="diet-vital-v">{agniLabel}</span>
          </div>
        )}
        {us.dietary_type && (
          <div className="diet-vital-chip">
            <Leaf size={11} className="diet-vital-icon" />
            <span className="diet-vital-v">{us.dietary_type.replace(/\b\w/g, c => c.toUpperCase())}</span>
          </div>
        )}
        {us.gut_issue && us.gut_issue !== 'healthy' && (
          <div className="diet-vital-chip">
            <span className="diet-vital-k">Gut</span>
            <span className="diet-vital-v">{us.gut_issue.replace(/_/g, ' ')}</span>
          </div>
        )}
        {us.intermittent_fasting && us.intermittent_fasting !== 'no' && (
          <div className="diet-vital-chip">
            <Timer size={11} className="diet-vital-icon" />
            <span className="diet-vital-k">IF</span>
            <span className="diet-vital-v">{us.intermittent_fasting}</span>
          </div>
        )}
        {(us.active_condition_protocols || []).map(c => (
          <div key={c} className="diet-vital-chip cond">
            <ShieldCheck size={11} />
            <span>{c.replace(/_/g, ' ')}</span>
          </div>
        ))}
      </div>

      {/* ── Pathya-Apathya (LLM only) ── */}
      {isLLM && <PathyaApathyaCard pa={plan.pathya_apathya} />}

      {/* ── Condition coaching ── */}
      {plan.condition_coaching && (
        <div className="diet-coaching-card">
          <ShieldCheck size={13} className="diet-coaching-icon" />
          <p className="diet-coaching-text">{plan.condition_coaching}</p>
        </div>
      )}

      {/* ── Week tabs (LLM 4-week plan) ── */}
      {isMultiWeek && (
        <div className="diet-week-tabs">
          {dietWeeks.map((wk, idx) => (
            <button
              key={idx}
              className={`diet-week-tab${activeWeek === idx ? ' active' : ''}`}
              onClick={() => { setActiveWeek(idx); setActiveDay(0); }}
            >
              <span className="diet-week-num">Week {wk.week_number}</span>
              <span className="diet-week-phase">{wk.phase}</span>
            </button>
          ))}
        </div>
      )}
      {isMultiWeek && currentWeek?.phase_description && (
        <p className="diet-phase-desc">{currentWeek.phase_description}</p>
      )}

      {/* ── Day selector ── */}
      <div className="diet-day-strip">
        {DIET_DAY_LABELS.map((label, i) => {
          const isFasting = isLLM
            ? (weeklyPlan[DIET_DAY_FULL[i]]?.is_fasting ?? false)
            : (fallbackDays[i]?.is_fasting_day || false)
          const theme = isLLM ? (weeklyPlan[DIET_DAY_FULL[i]]?.theme || '') : ''
          return (
            <button key={i}
              className={`diet-day-btn ${activeDay === i ? 'active' : ''} ${isFasting ? 'fasting' : ''}`}
              onClick={() => setActiveDay(i)}
              title={theme || label}>
              {label}
              {isFasting && <span className="diet-fast-dot" />}
            </button>
          )
        })}
      </div>

      {/* ── Day theme badge (LLM) ── */}
      {isLLM && dayData.theme && (
        <div className="diet-day-theme-badge">{dayData.theme}</div>
      )}

      {/* ── LLM Meal cards ── */}
      {isLLM && (!isMultiWeek || activeWeek === 0) && (
        <>
          {dayData.is_fasting && (
            <div className="diet-fasting-banner">
              <Moon size={16} />
              <div>
                <strong>Fasting Day</strong>
                <p>Light fruits, dairy, nuts, and herbal beverages only. Rest the digestive fire.</p>
              </div>
            </div>
          )}
          <div className="diet-meals-section">
            {['breakfast', 'lunch', 'snack', 'dinner'].map(meal => (
              dayData[meal] && (
                <LLMMealCard key={meal} mealName={meal} meal={dayData[meal]} />
              )
            ))}
          </div>
          {/* Day total macros computed from per-meal macros_approx */}
          {(() => {
            const meals = ['breakfast', 'lunch', 'snack', 'dinner']
            const total = meals.reduce((acc, m) => {
              const ma = dayData[m]?.macros_approx || {}
              return {
                calories: acc.calories + (ma.calories || 0),
                protein_g: acc.protein_g + (ma.protein_g || 0),
                carbs_g: acc.carbs_g + (ma.carbs_g || 0),
                fat_g: acc.fat_g + (ma.fat_g || 0),
              }
            }, { calories: 0, protein_g: 0, carbs_g: 0, fat_g: 0 })
            return total.calories > 0 ? (
              <div className="diet-day-macros">
                <span className="diet-day-macros-label">Day totals (approx.)</span>
                <MacroBar macros={total} />
              </div>
            ) : null
          })()}
        </>
      )}

      {/* ── Compact meals (weeks 2-4) ── */}
      {isMultiWeek && activeWeek > 0 && (
        <div className="diet-compact-meals">
          {['breakfast', 'lunch', 'snack', 'dinner'].map(meal => {
            const val = dayData[meal]
            if (!val) return null
            const MealIcon = DIET_MEAL_ICONS[meal] || UtensilsCrossed
            const label = meal.charAt(0).toUpperCase() + meal.slice(1)
            return (
              <div key={meal} className="diet-compact-meal-row">
                <MealIcon size={13} className="diet-compact-meal-icon" />
                <span className="diet-compact-meal-label">{label}</span>
                <span className="diet-compact-meal-name">{typeof val === 'string' ? val : val.meal_name || ''}</span>
              </div>
            )
          })}
          {dayData.special_drink && (
            <div className="diet-compact-meal-row drink">
              <Droplets size={13} className="diet-compact-meal-icon" />
              <span className="diet-compact-meal-label">Drink</span>
              <span className="diet-compact-meal-name">{typeof dayData.special_drink === 'string' ? dayData.special_drink : dayData.special_drink.name || ''}</span>
            </div>
          )}
        </div>
      )}

      {/* ── Fallback meal cards (rule engine) ── */}
      {!isLLM && (
        <>
          {fallbackDay.is_fasting_day && (
            <div className="diet-fasting-banner">
              <Moon size={16} />
              <div>
                <strong>Fasting Day</strong>
                <p>Light fruits, dairy, nuts, and herbal beverages only. Rest the digestive fire.</p>
              </div>
            </div>
          )}
          <div className="diet-meals-section">
            {['breakfast', 'lunch', 'snack', 'dinner'].map(meal => {
              const items = fallbackDay.meals?.[meal] || []
              if (!items.length) return null
              const MealIcon = DIET_MEAL_ICONS[meal] || UtensilsCrossed
              return (
                <div key={meal} className={`diet-meal-card meal-${meal}`}>
                  <div className="diet-meal-header">
                    <div className="diet-meal-title-row">
                      <MealIcon size={13} className="diet-meal-icon" />
                      <span className="diet-meal-label">{meal.charAt(0).toUpperCase() + meal.slice(1)}</span>
                    </div>
                  </div>
                  <div className="diet-meal-foods">
                    {items.map((item, i) => (
                      <div key={i} className="diet-food-row">
                        <span className="diet-food-name">{item.name}</span>
                        <span className="diet-food-portion">{item.portion}</span>
                        {item.macros?.calories > 0 && (
                          <span className="diet-food-cal">{Math.round(item.macros.calories)} cal</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
          {fallbackDay.daily_macros && (
            <div className="diet-day-macros">
              <span className="diet-day-macros-label">Day totals (approx.)</span>
              <MacroBar macros={fallbackDay.daily_macros} />
            </div>
          )}
        </>
      )}

      {/* ── Special Ayurvedic drink (LLM, week 1 full detail only) ── */}
      {isLLM && dayData.special_drink && (!isMultiWeek || activeWeek === 0) && (
        <div className="diet-drink-card">
          <div className="diet-drink-header">
            <CupSoda size={13} className="diet-drink-icon" />
            <span className="diet-drink-name">{dayData.special_drink.name}</span>
            <span className="diet-drink-when">{dayData.special_drink.when}</span>
          </div>
          {dayData.special_drink.recipe && (
            <p className="diet-drink-recipe">{dayData.special_drink.recipe}</p>
          )}
          {dayData.special_drink.rationale && (
            <p className="diet-drink-rationale">{dayData.special_drink.rationale}</p>
          )}
        </div>
      )}

      {/* ── Ahar Vidhi (LLM) ── */}
      {isLLM && plan.ahar_vidhi && (
        <div className="diet-ahar-vidhi">
          <div className="diet-ahar-vidhi-title">
            <BookOpen size={13} /> Ahar Vidhi — Rules of Eating
          </div>
          <p>{plan.ahar_vidhi}</p>
        </div>
      )}

      {/* ── Meal timing (Dinacharya) — fallback / both ── */}
      {Object.keys(timing).length > 0 && (
        <div className="diet-timing-card">
          <button className="diet-timing-toggle" onClick={() => setTimingOpen(o => !o)}>
            <Clock size={13} className="diet-timing-icon" />
            <span>Meal Timing — Dinacharya</span>
            {timingOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>
          {timingOpen && (
            <div className="diet-timing-body">
              {timing.general_note && <p className="diet-timing-note">{timing.general_note}</p>}
              <div className="diet-timing-rows">
                {['breakfast', 'lunch', 'snack', 'dinner'].map(m => timing[m] && (
                  <div key={m} className="diet-timing-row">
                    <span className="diet-timing-meal">{m.charAt(0).toUpperCase() + m.slice(1)}</span>
                    <span className="diet-timing-time">{timing[m]}</span>
                  </div>
                ))}
                {timing.wake_up_drink && (
                  <div className="diet-timing-row special">
                    <CupSoda size={11} />
                    <span className="diet-timing-meal">Wake-up drink</span>
                    <span className="diet-timing-time">{timing.wake_up_drink}</span>
                  </div>
                )}
                {timing.bedtime_drink && (
                  <div className="diet-timing-row special">
                    <Moon size={11} />
                    <span className="diet-timing-meal">Bedtime drink</span>
                    <span className="diet-timing-time">{timing.bedtime_drink}</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Spice guide ── */}
      {plan.spice_guide?.length > 0 && (
        <div className="diet-spice-guide-card">
          <button className="diet-timing-toggle" onClick={() => setSpiceOpen(o => !o)}>
            <Flower2 size={13} className="diet-timing-icon" />
            <span>Dosha Spice Guide</span>
            {spiceOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>
          {spiceOpen && (
            <div className="diet-spice-guide-rows">
              {plan.spice_guide.map((s, i) => (
                <div key={i} className="diet-spice-guide-row">
                  <div className="diet-spice-guide-name">
                    {s.name}
                    {s.sanskrit && <span className="diet-spice-guide-sk">{s.sanskrit}</span>}
                  </div>
                  <p className="diet-spice-guide-use">{s.use}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Hydration + fasting guidance ── */}
      {(plan.hydration_guidance || plan.fasting_guidance) && (
        <div className="diet-guidance-row">
          {plan.hydration_guidance && (
            <div className="diet-guidance-card">
              <Droplets size={13} className="diet-guidance-icon hydration" />
              <div>
                <div className="diet-guidance-title">Hydration</div>
                <p className="diet-guidance-text">{plan.hydration_guidance}</p>
              </div>
            </div>
          )}
          {plan.fasting_guidance && (
            <div className="diet-guidance-card">
              <Moon size={13} className="diet-guidance-icon fasting" />
              <div>
                <div className="diet-guidance-title">Fasting Protocol</div>
                <p className="diet-guidance-text">{plan.fasting_guidance}</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Seasonal + Ayurvedic tips ── */}
      {plan.seasonal_note && (
        <div className="diet-seasonal-note">
          <Sun size={13} className="diet-seasonal-icon" />
          <p>{plan.seasonal_note}</p>
        </div>
      )}
      {plan.ayurvedic_tips && (
        <div className="diet-ayur-tips">
          <Leaf size={13} className="diet-ayur-icon" />
          <p>{plan.ayurvedic_tips}</p>
        </div>
      )}

      {/* ── Disclaimer ── */}
      <div className="diet-disclaimer">
        <ShieldCheck size={11} />
        <span>
          {plan.disclaimer ||
            'AI-generated wellness guidance. Consult a qualified Ayurvedic practitioner before starting a therapeutic diet, especially with existing medical conditions.'}
        </span>
      </div>

    </div>
  )
}

// ── RemedyView ────────────────────────────────────────────────────────────────
const DOSHA_COLORS_R = { vata: '#a78bfa', pitta: '#f97316', kapha: '#34d399', universal: '#2dd4bf' }
const SEV_COLOR  = { mild: '#22c55e', moderate: '#f59e0b', severe: '#ef4444' }
const SEV_LABEL  = { mild: 'Mild', moderate: 'Moderate', severe: 'Severe' }

function RemedyIngredient({ item }) {
  return (
    <div className="rv-ingredient">
      <span className="rv-ing-dot" />
      <span className="rv-ing-name">{item.item}</span>
      {item.amount && <span className="rv-ing-amount">{item.amount}</span>}
      {item.preparation && <span className="rv-ing-prep">— {item.preparation}</span>}
    </div>
  )
}

function RemedyCard({ result }) {
  const [open, setOpen] = useState(false)
  const { remedy, symptom_display, severity, dosha_cause, dosha_used, requires_practitioner, ayurvedic_rationale } = result
  if (!remedy) return null
  const doshaColor = DOSHA_COLORS_R[dosha_used] || DOSHA_COLORS_R.universal

  return (
    <div className="rv-card">
      <div className="rv-card-header" onClick={() => setOpen(o => !o)} role="button">
        <div className="rv-card-left">
          <div className="rv-symptom-name">{symptom_display}</div>
          <div className="rv-remedy-name">{remedy.name}</div>
        </div>
        <div className="rv-card-right">
          <span className="rv-sev-badge" style={{ background: SEV_COLOR[severity] + '22', color: SEV_COLOR[severity] }}>
            {SEV_LABEL[severity] || severity}
          </span>
          <span className="rv-dosha-chip" style={{ background: doshaColor + '22', color: doshaColor }}>
            {dosha_used}
          </span>
          {open ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
        </div>
      </div>

      {open && (
        <div className="rv-card-body">
          {dosha_cause && (
            <div className="rv-dosha-cause">
              <Flame size={13} style={{ color: doshaColor }} />
              <span>Dosha cause ({dosha_used}): {dosha_cause}</span>
            </div>
          )}
          {ayurvedic_rationale && (
            <div className="rv-rationale">{ayurvedic_rationale}</div>
          )}
          {remedy.ingredients?.length > 0 && (
            <div className="rv-section">
              <div className="rv-section-label">Ingredients</div>
              <div className="rv-ingredients">
                {remedy.ingredients.map((ing, i) => <RemedyIngredient key={i} item={ing} />)}
              </div>
            </div>
          )}
          {remedy.preparation && (
            <div className="rv-section">
              <div className="rv-section-label">Preparation</div>
              <p className="rv-preparation">{remedy.preparation}</p>
            </div>
          )}
          <div className="rv-meta-row">
            {remedy.dosage     && <div className="rv-meta-chip"><Timer size={11} />{remedy.dosage}</div>}
            {remedy.duration   && <div className="rv-meta-chip"><Calendar size={11} />{remedy.duration}</div>}
            {remedy.expected_relief && <div className="rv-meta-chip"><Zap size={11} />Relief in {remedy.expected_relief}</div>}
          </div>
          {requires_practitioner && (
            <div className="rv-practitioner-note">
              <TriangleAlert size={13} />
              Chronic/long-duration symptom — follow up with an Ayurvedic practitioner
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function RemedyView({ plan }) {
  const symptoms   = plan.symptoms_addressed || []
  const referrals  = plan.doctor_referrals || []
  const guidelines = plan.general_guidelines || {}
  const prevention = plan.prevention_tips || []

  return (
    <div className="rv-view">

      {/* Intro */}
      {plan.personalized_intro && (
        <div className="rv-intro-card">
          <HeartPulse size={18} className="rv-intro-icon" />
          <p>{plan.personalized_intro}</p>
        </div>
      )}

      {/* Symptom remedy cards */}
      {symptoms.length > 0 && (
        <div className="rv-section-block">
          <div className="rv-block-title">
            <Leaf size={16} />
            Remedies for Your Symptoms
          </div>
          {symptoms.map((res, i) => <RemedyCard key={i} result={res} />)}
        </div>
      )}

      {/* Doctor referrals */}
      {referrals.length > 0 && (
        <div className="rv-section-block rv-referrals">
          <div className="rv-block-title"><TriangleAlert size={16} style={{ color: '#ef4444' }} />Doctor Referrals</div>
          {referrals.map((r, i) => (
            <div key={i} className="rv-referral-card">
              <span className="rv-referral-sym">{r.symptom_id || r.symptom_display || 'Symptom'}</span>
              <span className="rv-referral-msg">{r.message}</span>
            </div>
          ))}
        </div>
      )}

      {/* Recovery timeline */}
      {plan.recovery_timeline && (
        <div className="rv-info-card">
          <div className="rv-info-label"><Calendar size={14} />Recovery Timeline</div>
          <p className="rv-info-body">{plan.recovery_timeline}</p>
        </div>
      )}

      {/* Synergy note */}
      {plan.synergy_note && (
        <div className="rv-info-card">
          <div className="rv-info-label"><Sparkles size={14} />Synergy Note</div>
          <p className="rv-info-body">{plan.synergy_note}</p>
        </div>
      )}

      {/* Prevention tips */}
      {prevention.length > 0 && (
        <div className="rv-info-card">
          <div className="rv-info-label"><BadgeCheck size={14} />Prevention Tips</div>
          <ul className="rv-tip-list">
            {prevention.map((tip, i) => <li key={i}>{tip}</li>)}
          </ul>
        </div>
      )}

      {/* When to escalate */}
      {plan.when_to_escalate && (
        <div className="rv-info-card rv-escalate">
          <div className="rv-info-label"><TriangleAlert size={14} />When to See a Doctor</div>
          <p className="rv-info-body">{plan.when_to_escalate}</p>
        </div>
      )}

      {/* General guidelines */}
      {(guidelines.diet_during_recovery || guidelines.lifestyle_notes || guidelines.what_to_avoid?.length > 0) && (
        <div className="rv-info-card">
          <div className="rv-info-label"><Layers size={14} />Recovery Guidelines ({plan.user_dosha} dosha)</div>
          {guidelines.diet_during_recovery && <p className="rv-info-body">{guidelines.diet_during_recovery}</p>}
          {guidelines.lifestyle_notes && <p className="rv-info-body" style={{ marginTop: 6 }}>{guidelines.lifestyle_notes}</p>}
          {guidelines.what_to_avoid?.length > 0 && (
            <div className="rv-avoid-row">
              {guidelines.what_to_avoid.map((a, i) => (
                <span key={i} className="rv-avoid-chip">{a}</span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Disclaimer */}
      {plan.disclaimer && (
        <div className="rv-disclaimer">
          <ShieldCheck size={12} />
          <span>{plan.disclaimer}</span>
        </div>
      )}
    </div>
  )
}

// ── MedicineView ──────────────────────────────────────────────────────────────
// ── MedicineView constants ────────────────────────────────────────────────────
const TIER_LABEL = { 1: 'OTC Safe', 2: 'Practitioner Advised' }
const TIER_COLOR = { 1: '#22c55e', 2: '#f59e0b' }
const TYPE_COLOR = {
  'churna (powder)':                     '#a78bfa',
  'avaleha (jam)':                       '#fb923c',
  'arishta (fermented decoction)':       '#34d399',
  'asava (fermented)':                   '#34d399',
  'vati (tablet)':                       '#60a5fa',
  'vati/guggulu (tablet)':               '#60a5fa',
  'kashayam (decoction)':                '#2dd4bf',
  'ghrita (medicated ghee)':             '#fde68a',
  'taila (oil)':                         '#fbbf24',
  'satva (extract)':                     '#e879f9',
  'bhasma (ash)':                        '#94a3b8',
  'pishti (powder of gems/minerals)':    '#c4b5fd',
  'pak (confection)':                    '#f97316',
}
const RASA_COLOR = {
  madhura: '#22c55e',
  amla:    '#f59e0b',
  lavana:  '#60a5fa',
  katu:    '#ef4444',
  tikta:   '#a78bfa',
  kashaya: '#6b7280',
}
const KARMA_COLOR = {
  'Deepana':     '#f59e0b',
  'Pachana':     '#fb923c',
  'Vatahara':    '#60a5fa',
  'Pittahara':   '#34d399',
  'Kaphahara':   '#a78bfa',
  'Tridoshahara':'#e879f9',
  'Rasayana':    '#22c55e',
  'Balya':       '#2dd4bf',
  'Medhya':      '#818cf8',
  'Brimhana':    '#fde68a',
  'Shodhana':    '#f97316',
  'Anulomana':   '#94a3b8',
}

function MedCard({ med, rationale }) {
  const [open, setOpen] = useState(false)
  const typeKey   = (med.type || '').toLowerCase()
  const color     = TYPE_COLOR[typeKey] || '#94a3b8'
  const tierColor = TIER_COLOR[med.safety_tier] || '#94a3b8'
  const isExternal = med.application_type === 'external'
  const hasRasa    = med.rasa?.length > 0
  const hasKarma   = med.karma?.length > 0
  const hasDhatu   = med.dhatu_affected?.length > 0
  const durMin     = med.duration_min_weeks
  const durMax     = med.duration_max_weeks

  return (
    <div className="mv-card" style={{ '--mv-accent': color }}>
      {/* ── Header ── */}
      <div className="mv-card-header" onClick={() => setOpen(o => !o)} role="button" tabIndex={0}>
        <div className="mv-card-left">
          <div className="mv-med-name">
            {med.name}
            {med.previously_tried && <span className="mv-tried-badge">Tried before</span>}
          </div>
          <div className="mv-type-chip" style={{ background: color + '22', color }}>{med.type}</div>
        </div>
        <div className="mv-card-right">
          {durMin && <span className="mv-duration-badge">{durMin}–{durMax || durMin} wk</span>}
          <span className="mv-tier-badge" style={{ background: tierColor + '22', color: tierColor }}>
            {TIER_LABEL[med.safety_tier] || 'Consult Vaidya'}
          </span>
          {isExternal && <span className="mv-external-badge">External</span>}
          {open ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
        </div>
      </div>

      {/* ── Panchakosha pharmacology strip (always visible) ── */}
      {(hasRasa || med.virya || med.vipaka) && (
        <div className="mv-pharma-strip">
          {hasRasa && (
            <div className="mv-pharma-group">
              <span className="mv-pharma-label">Rasa</span>
              <div className="mv-rasa-chips">
                {med.rasa.map((r, i) => (
                  <span key={i} className="mv-rasa-chip" style={{ background: (RASA_COLOR[r] || '#94a3b8') + '22', color: RASA_COLOR[r] || '#94a3b8' }}>
                    {r.charAt(0).toUpperCase() + r.slice(1)}
                  </span>
                ))}
              </div>
            </div>
          )}
          {med.virya && (
            <div className="mv-pharma-group">
              <span className="mv-pharma-label">Virya</span>
              <span className={`mv-virya-badge ${med.virya === 'ushna' ? 'ushna' : 'sheeta'}`}>
                {med.virya === 'ushna' ? '🔥 Heating' : '❄️ Cooling'}
              </span>
            </div>
          )}
          {med.vipaka && (
            <div className="mv-pharma-group">
              <span className="mv-pharma-label">Vipaka</span>
              <span className="mv-vipaka-badge">{med.vipaka.charAt(0).toUpperCase() + med.vipaka.slice(1)}</span>
            </div>
          )}
        </div>
      )}

      {/* ── Expanded body ── */}
      {open && (
        <div className="mv-card-body">
          {/* Rationale (from enricher) */}
          {rationale && (
            <div className="mv-rationale-block">
              {typeof rationale === 'object' ? (
                <>
                  {rationale.rasa_guna_reasoning && <p className="mv-rationale">{rationale.rasa_guna_reasoning}</p>}
                  {rationale.classical_basis && (
                    <div className="mv-classical-basis">
                      <BookOpen size={11} />
                      <span>{rationale.classical_basis}</span>
                    </div>
                  )}
                  {rationale.anupana_reason && (
                    <div className="mv-anupana-reason">
                      <Droplets size={11} />
                      <span>{rationale.anupana_reason}</span>
                    </div>
                  )}
                </>
              ) : (
                <p className="mv-rationale">{rationale}</p>
              )}
            </div>
          )}

          {/* Classical action */}
          {med.classical_action && (
            <div className="mv-action-row">
              <BookOpen size={12} />
              <span>{med.classical_action}</span>
            </div>
          )}

          {/* Karma pills */}
          {hasKarma && (
            <div className="mv-section">
              <div className="mv-section-label">Karma (Actions)</div>
              <div className="mv-karma-row">
                {med.karma.map((k, i) => (
                  <span key={i} className="mv-karma-pill" style={{
                    background: (KARMA_COLOR[k] || '#64748b') + '22',
                    color: KARMA_COLOR[k] || '#94a3b8',
                  }}>{k}</span>
                ))}
              </div>
            </div>
          )}

          {/* Dhatu affected */}
          {hasDhatu && (
            <div className="mv-section">
              <div className="mv-section-label">Dhatu Affected</div>
              <div className="mv-karma-row">
                {med.dhatu_affected.map((d, i) => (
                  <span key={i} className="mv-dhatu-chip">{d.charAt(0).toUpperCase() + d.slice(1)}</span>
                ))}
              </div>
            </div>
          )}

          {/* Guna */}
          {med.guna?.length > 0 && (
            <div className="mv-section">
              <div className="mv-section-label">Guna (Qualities)</div>
              <div className="mv-karma-row">
                {med.guna.map((g, i) => (
                  <span key={i} className="mv-guna-chip">{g.charAt(0).toUpperCase() + g.slice(1)}</span>
                ))}
              </div>
            </div>
          )}

          {/* Ingredients */}
          {med.ingredients?.length > 0 && (
            <div className="mv-section">
              <div className="mv-section-label">Key Ingredients</div>
              <div className="mv-ingredients">
                {med.ingredients.map((ing, i) => (
                  <span key={i} className="mv-ing-chip">{ing}</span>
                ))}
              </div>
            </div>
          )}

          {/* Dosage */}
          <div className="mv-dosage-block">
            <div className="mv-section-label">Dosage & Administration</div>
            <p className="mv-dosage-text">{med.dosage}</p>
            {(med.selected_anupana || med.anupana) && (med.selected_anupana || med.anupana) !== 'External use only' && (
              <div className="mv-anupana">
                <Droplets size={12} />
                <span>Anupana: <strong>{med.selected_anupana || med.anupana}</strong></span>
              </div>
            )}
            {med.dosage_pediatric && (
              <div className="mv-anupana" style={{ color: '#a78bfa' }}>
                <span>Paediatric dose: {med.dosage_pediatric}</span>
              </div>
            )}
          </div>

          {/* Contraindications */}
          {med.contraindications?.length > 0 && (
            <div className="mv-section">
              <div className="mv-section-label" style={{ color: '#f97316' }}>Contraindications</div>
              <div className="mv-contra-chips">
                {med.contraindications.map((c, i) => (
                  <span key={i} className="mv-contra-chip">{c.replace(/_/g, ' ')}</span>
                ))}
              </div>
            </div>
          )}

          {/* AFI / Classical reference */}
          {(med.afi_reference || med.classical_text_reference) && (
            <div className="mv-afi-ref">
              <BookOpen size={11} />
              <div>
                {med.afi_reference && <div><strong>AFI:</strong> {med.afi_reference}</div>}
                {med.classical_text_reference && <div>{med.classical_text_reference}</div>}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function MedicineView({ plan }) {
  const primary    = plan.primary_formulations || []
  const supporting = plan.supporting_formulations || []
  const external   = plan.external_therapies || []
  const schedule   = plan.dosage_schedule || []
  const protocol   = plan.treatment_protocol || {}
  const outcomes   = plan.expected_outcomes || {}
  const lifestyle  = plan.lifestyle_guidance || {}
  const blocked    = plan.blocked_medicines || []
  const rationale  = plan.formulation_rationale || {}
  const pathya     = plan.pathya || []
  const apathya    = plan.apathya || []
  const viruddha   = plan.viruddha_ahara_alerts || []

  const doshaColor = DOSHA_COLORS_R[plan.vikriti_dominant || plan.user_dosha] || DOSHA_COLORS_R.universal

  return (
    <div className="mv-view">

      {/* ── Intro ── */}
      {plan.personalized_intro && (
        <div className="rv-intro-card">
          <Stethoscope size={18} className="rv-intro-icon" />
          <p>{plan.personalized_intro}</p>
        </div>
      )}

      {/* ── Chikitsa Sutra ── */}
      {plan.chikitsa_sutra && (
        <div className="mv-chikitsa-card">
          <div className="mv-chikitsa-label">
            <BookOpen size={14} />
            Chikitsa Sutra
            <span className="mv-approach-badge" style={{ background: plan.chikitsa_approach === 'Shodhana' ? '#f9731622' : '#22c55e22', color: plan.chikitsa_approach === 'Shodhana' ? '#f97316' : '#22c55e' }}>
              {plan.chikitsa_approach || 'Shamana'}
            </span>
          </div>
          <p className="mv-chikitsa-text">{plan.chikitsa_sutra}</p>
          {plan.agni_type && plan.vikriti_dominant && (
            <div className="mv-vitals-chips">
              <span className="mv-vital-chip"><Flame size={10} />{plan.vikriti_dominant} vikriti</span>
              {plan.vikriti_secondary && <span className="mv-vital-chip">{plan.vikriti_secondary} secondary</span>}
              <span className="mv-vital-chip"><Droplets size={10} />{plan.agni_type} agni</span>
              {plan.ama_level && plan.ama_level !== 'low' && <span className="mv-vital-chip" style={{ color: '#f59e0b' }}>ama: {plan.ama_level}</span>}
              {plan.current_season && <span className="mv-vital-chip"><Leaf size={10} />{plan.current_season}</span>}
            </div>
          )}
        </div>
      )}

      {/* ── Conditions banner ── */}
      {plan.active_conditions?.length > 0 && (
        <div className="mv-conditions-row">
          {plan.active_conditions.map((c, i) => (
            <span key={i} className="mv-cond-chip">{c.replace(/_/g, ' ')}</span>
          ))}
        </div>
      )}

      {/* ── Primary formulations ── */}
      {primary.length > 0 && (
        <div className="rv-section-block">
          <div className="rv-block-title"><Pill size={16} />Primary Formulations</div>
          {primary.map((med, i) => <MedCard key={i} med={med} rationale={rationale[med.name]} />)}
        </div>
      )}

      {/* ── Supporting formulations ── */}
      {supporting.length > 0 && (
        <div className="rv-section-block">
          <div className="rv-block-title"><Layers size={16} />Supporting Formulations</div>
          {supporting.map((med, i) => <MedCard key={i} med={med} rationale={rationale[med.name]} />)}
        </div>
      )}

      {/* ── External therapies ── */}
      {external.length > 0 && (
        <div className="rv-section-block">
          <div className="rv-block-title"><Droplets size={16} />External Therapies (Taila)</div>
          {external.map((med, i) => <MedCard key={i} med={med} rationale={rationale[med.name]} />)}
        </div>
      )}

      {/* ── Daily dosage schedule ── */}
      {schedule.length > 0 && (
        <div className="rv-section-block">
          <div className="rv-block-title"><Clock size={16} />Daily Dosage Schedule</div>
          {schedule.map((slot, i) => (
            <div key={i} className="mv-schedule-slot">
              <div className="mv-schedule-time">{slot.time}</div>
              {slot.medicines.map((m, j) => (
                <div key={j} className="mv-schedule-med">{m}</div>
              ))}
            </div>
          ))}
        </div>
      )}

      {/* ── Treatment protocol grid ── */}
      {(protocol.week_1_2 || protocol.week_3_4 || protocol.week_5_plus) && (
        <div className="mv-protocol-section">
          <div className="rv-block-title"><Calendar size={16} />Treatment Protocol</div>
          {protocol.dose_note && (
            <div className="mv-dose-note"><Flame size={12} />{protocol.dose_note}</div>
          )}
          <div className="mv-protocol-grid">
            {protocol.week_1_2 && (
              <div className="mv-protocol-col">
                <div className="mv-protocol-week">Week 1–2</div>
                <p className="mv-protocol-text">{protocol.week_1_2}</p>
              </div>
            )}
            {protocol.week_3_4 && (
              <div className="mv-protocol-col">
                <div className="mv-protocol-week">Week 3–4</div>
                <p className="mv-protocol-text">{protocol.week_3_4}</p>
              </div>
            )}
            {protocol.week_5_plus && (
              <div className="mv-protocol-col">
                <div className="mv-protocol-week">Week 5+</div>
                <p className="mv-protocol-text">{protocol.week_5_plus}</p>
              </div>
            )}
          </div>
          {protocol.total_duration && (
            <div className="mv-total-duration"><Clock size={11} />Total duration: <strong>{protocol.total_duration}</strong></div>
          )}
        </div>
      )}

      {/* ── Expected outcomes timeline ── */}
      {(outcomes.week_2 || outcomes.week_4 || outcomes.week_8) && (
        <div className="rv-section-block">
          <div className="rv-block-title"><Sparkles size={16} />Expected Outcomes</div>
          <div className="mv-outcomes-timeline">
            {outcomes.week_2 && (
              <div className="mv-outcome-milestone">
                <div className="mv-milestone-marker">Week 2</div>
                <p className="mv-milestone-text">{outcomes.week_2}</p>
              </div>
            )}
            {outcomes.week_4 && (
              <div className="mv-outcome-milestone">
                <div className="mv-milestone-marker">Week 4</div>
                <p className="mv-milestone-text">{outcomes.week_4}</p>
              </div>
            )}
            {outcomes.week_8 && (
              <div className="mv-outcome-milestone">
                <div className="mv-milestone-marker">Week 8</div>
                <p className="mv-milestone-text">{outcomes.week_8}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Synergy note ── */}
      {plan.synergy_note && (
        <div className="rv-info-card">
          <div className="rv-info-label"><Sparkles size={14} />Synergy of Formulations</div>
          <p className="rv-info-body">{plan.synergy_note}</p>
        </div>
      )}

      {/* ── Pathya-Apathya (structured lists) ── */}
      {(pathya.length > 0 || apathya.length > 0) && (
        <div className="mv-pathya-section">
          <div className="rv-block-title"><UtensilsCrossed size={16} />Pathya & Apathya</div>
          <div className="mv-pathya-grid">
            {pathya.length > 0 && (
              <div className="mv-pathya-col">
                <div className="mv-pathya-col-label do">✓ Pathya (Do)</div>
                {pathya.map((p, i) => <div key={i} className="mv-pathya-row do">{p}</div>)}
              </div>
            )}
            {apathya.length > 0 && (
              <div className="mv-pathya-col">
                <div className="mv-pathya-col-label dont">✗ Apathya (Avoid)</div>
                {apathya.map((p, i) => <div key={i} className="mv-pathya-row dont">{p}</div>)}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Viruddha Ahara alerts ── */}
      {viruddha.length > 0 && (
        <div className="mv-viruddha-card">
          <div className="mv-viruddha-label"><TriangleAlert size={13} />Viruddha Ahara — Incompatible Combinations</div>
          {viruddha.map((v, i) => (
            <div key={i} className="mv-viruddha-row">{v}</div>
          ))}
        </div>
      )}

      {/* ── Lifestyle guidance (Dosha base) ── */}
      {(lifestyle.dietary_note || lifestyle.routine_note || lifestyle.avoid?.length > 0) && (
        <div className="rv-info-card">
          <div className="rv-info-label" style={{ color: doshaColor }}>
            <Leaf size={14} />Lifestyle — {(plan.vikriti_dominant || plan.user_dosha)?.charAt(0).toUpperCase() + (plan.vikriti_dominant || plan.user_dosha)?.slice(1)} Vikriti
          </div>
          {lifestyle.dietary_note && <p className="rv-info-body">{lifestyle.dietary_note}</p>}
          {lifestyle.routine_note && <p className="rv-info-body" style={{ marginTop: 6 }}>{lifestyle.routine_note}</p>}
          {lifestyle.avoid?.length > 0 && (
            <div className="rv-avoid-row">
              {lifestyle.avoid.map((a, i) => <span key={i} className="rv-avoid-chip">{a}</span>)}
            </div>
          )}
        </div>
      )}

      {/* ── Monitoring signs ── */}
      {plan.monitoring_signs && (
        <div className="rv-info-card">
          <div className="rv-info-label"><Stethoscope size={14} />Monitoring & Follow-Up</div>
          <p className="rv-info-body">{plan.monitoring_signs}</p>
        </div>
      )}

      {/* ── When to stop ── */}
      {plan.when_to_stop && (
        <div className="rv-info-card rv-escalate">
          <div className="rv-info-label"><TriangleAlert size={14} />When to Stop & Consult Immediately</div>
          <p className="rv-info-body">{plan.when_to_stop}</p>
        </div>
      )}

      {/* ── Blocked medicines ── */}
      {blocked.length > 0 && (
        <div className="mv-blocked-section">
          <div className="rv-info-label"><TriangleAlert size={14} style={{ color: '#ef4444' }} />Medicines Excluded for Your Safety</div>
          {blocked.map((b, i) => (
            <div key={i} className="mv-blocked-item">
              <span className="mv-blocked-name">{b.name}</span>
              <span className="mv-blocked-reason">{b.reason}</span>
            </div>
          ))}
        </div>
      )}

      {/* ── Disclaimer ── */}
      {plan.disclaimer && (
        <div className="rv-disclaimer">
          <ShieldCheck size={12} />
          <span>{plan.disclaimer}</span>
        </div>
      )}
    </div>
  )
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

      {/* ── Yoga dedicated view ── */}
      {planType === 'yoga' && plan.four_week_plan && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.42, ease: [0.16, 1, 0.3, 1] }}
        >
          <YogaView plan={plan} />
        </motion.div>
      )}

      {/* ── Gym dedicated view ── */}
      {planType === 'gym' && (plan.weekly_schedule || plan.four_week_plan) && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.42, ease: [0.16, 1, 0.3, 1] }}
        >
          <GymView plan={plan} />
        </motion.div>
      )}

      {/* ── Diet dedicated view ── */}
      {planType === 'diet' && (plan.four_week_plan || plan.weekly_plan) && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.42, ease: [0.16, 1, 0.3, 1] }}
        >
          <DietView plan={plan} />
        </motion.div>
      )}

      {/* ── Remedies dedicated view ── */}
      {planType === 'remedies' && (plan.symptoms_addressed || plan.doctor_referrals) && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.42, ease: [0.16, 1, 0.3, 1] }}
        >
          <RemedyView plan={plan} />
        </motion.div>
      )}

      {/* ── Medicines dedicated view ── */}
      {planType === 'medicines' && (plan.primary_formulations || plan.supporting_formulations) && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.42, ease: [0.16, 1, 0.3, 1] }}
        >
          <MedicineView plan={plan} />
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
