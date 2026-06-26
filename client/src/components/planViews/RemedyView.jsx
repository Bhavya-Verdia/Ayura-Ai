import React, { useState } from 'react'
import {
  Leaf, Sparkles, Calendar, ShieldCheck, Flame, Timer, Zap, ChevronDown, ChevronUp, Layers, TriangleAlert, BadgeCheck, HeartPulse,
} from 'lucide-react'
import { DOSHA_COLORS_R } from './shared'
import { MedicineView } from './MedicineView'

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


export function RemedyView({ plan }) {
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
