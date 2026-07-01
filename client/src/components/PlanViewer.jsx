import React from 'react'
import { m } from 'framer-motion'
import {
  Sun, PersonStanding, Dumbbell, Leaf, Coffee, Pill, Sparkles, FlaskConical, AlertTriangle, Star, BookOpen,
} from 'lucide-react'
import './PlanViewer.css'
import { renderValue } from './planViews/shared'
import { PanchakarmaView } from './planViews/PanchakarmaView'
import { GymView } from './planViews/GymView'
import { YogaView } from './planViews/YogaView'
import { DietView } from './planViews/DietView'
import { RemedyView } from './planViews/RemedyView'
import { MedicineView } from './planViews/MedicineView'
import { RoutineView } from './planViews/RoutineView'

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
  // Routine raw fields — rendered by RoutineView instead
  'weekly_routine', 'dinacharya_protocol', 'seasonal_ritucharya', 'meal_guidance', 'weekly_summary',
]

// ── Panchakarma dedicated renderer ────────────────────────────────────────────

const PLAN_CITATIONS = {
  gym:         ['Charaka Samhita, Sutrasthana 7 — Vyayama (exercise)', 'Ashtanga Hridayam, Sutrasthana 2'],
  yoga:        ['Hatha Yoga Pradipika', 'Patanjali Yoga Sutras', 'Gheranda Samhita'],
  diet:        ['Charaka Samhita, Sutrasthana 5 & 27 — Aharavidhi & Annapanavidhi', 'Ashtanga Hridayam, Sutrasthana 8'],
  routine:     ['Ashtanga Hridayam, Sutrasthana 2 — Dinacharya', 'Charaka Samhita, Sutrasthana 5 — Matrashitiya'],
  panchakarma: ['Charaka Samhita, Kalpa & Siddhi Sthana', 'Sushruta Samhita, Chikitsa Sthana'],
  remedies:    ['Bhavaprakasha Nighantu', 'Charaka Samhita, Chikitsa Sthana'],
  medicines:   ['Ayurvedic Formulary of India (AFI)', 'Bhaishajya Ratnavali', 'Sharangdhara Samhita'],
}


function ClassicalBasis({ planType }) {
  const refs = PLAN_CITATIONS[planType]
  if (!refs) return null
  return (
    <m.div
      className="plan-classical-basis"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.35 }}
    >
      <div className="plan-classical-title">
        <BookOpen size={14} strokeWidth={2} /> Classical basis
      </div>
      <ul className="plan-classical-list">
        {refs.map((r, i) => <li key={i}>{r}</li>)}
      </ul>
      <p className="plan-classical-note">
        Recommendations are grounded in these classical Ayurvedic texts; individual items may cite a specific shloka. Wellness guidance, not a substitute for examination by a registered Vaidya.
      </p>
    </m.div>
  )
}


export default function PlanViewer({ plan: rawPlan, planType }) {
  if (!rawPlan) return <p className="plan-empty">No plan data available.</p>

  const sectionKey = planType ? SECTION_KEY_MAP[planType] : null

  // The per-feature endpoints wrap the plan in a `{feature}_plan` envelope
  // (e.g. { routine_plan: {…}, generated_at, id }). The dedicated views and the
  // section logic below expect the INNER plan object, so unwrap it when present —
  // otherwise plan.weekly_routine / four_week_plan / clinical_decisions never
  // resolve and every plan falls back to the raw key-value dump.
  const plan = (
    sectionKey && rawPlan[sectionKey] &&
    typeof rawPlan[sectionKey] === 'object' && !Array.isArray(rawPlan[sectionKey])
  ) ? rawPlan[sectionKey] : rawPlan

  const sections = sectionKey && plan[sectionKey]
    ? { [sectionKey]: plan[sectionKey] }
    : Object.fromEntries(Object.entries(plan).filter(([k]) => !SKIP_KEYS.includes(k) && plan[k]))

  return (
    <div className="plan-viewer-container">
      {/* ── Summary banner ── */}
      {plan.user_summary && (
        <m.div
          className="plan-summary-banner"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="plan-summary-name">
            {plan.user_summary.name
              ? `Good morning, ${plan.user_summary.name.split(' ')[0]}`
              : 'Good morning'}
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
        </m.div>
      )}

      {/* ── Panchakarma dedicated view ── */}
      {planType === 'panchakarma' && plan.clinical_decisions && (
        <m.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.42, ease: [0.16, 1, 0.3, 1] }}
        >
          <PanchakarmaView plan={plan} />
        </m.div>
      )}

      {/* ── Yoga dedicated view ── */}
      {planType === 'yoga' && plan.four_week_plan && (
        <m.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.42, ease: [0.16, 1, 0.3, 1] }}
        >
          <YogaView plan={plan} />
        </m.div>
      )}

      {/* ── Gym dedicated view ── */}
      {planType === 'gym' && (plan.weekly_schedule || plan.four_week_plan) && (
        <m.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.42, ease: [0.16, 1, 0.3, 1] }}
        >
          <GymView plan={plan} />
        </m.div>
      )}

      {/* ── Diet dedicated view ── */}
      {planType === 'diet' && (plan.four_week_plan || plan.weekly_plan) && (
        <m.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.42, ease: [0.16, 1, 0.3, 1] }}
        >
          <DietView plan={plan} />
        </m.div>
      )}

      {/* ── Remedies dedicated view ── */}
      {planType === 'remedies' && (plan.symptoms_addressed || plan.doctor_referrals) && (
        <m.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.42, ease: [0.16, 1, 0.3, 1] }}
        >
          <RemedyView plan={plan} />
        </m.div>
      )}

      {/* ── Medicines dedicated view ── */}
      {planType === 'medicines' && (plan.primary_formulations || plan.supporting_formulations) && (
        <m.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.42, ease: [0.16, 1, 0.3, 1] }}
        >
          <MedicineView plan={plan} />
        </m.div>
      )}

      {/* ── Routine dedicated view ── */}
      {planType === 'routine' && plan.weekly_routine && (
        <m.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.42, ease: [0.16, 1, 0.3, 1] }}
        >
          <RoutineView plan={plan} />
        </m.div>
      )}

      {/* ── Plan sections ── */}
      {Object.entries(sections).map(([key, value], idx) => {
        const IconComponent = SECTION_ICONS[key] || Sparkles
        return value ? (
          <m.div
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
          </m.div>
        ) : null
      })}

      {/* ── Safety & disclaimers ── */}
      {(plan.safety_checks?.warnings?.length > 0 || plan.disclaimer || plan.medical_disclaimer) && (
        <m.div
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
        </m.div>
      )}

      {/* ── Classical basis (citations) ── */}
      <ClassicalBasis planType={planType} />
    </div>
  )
}

