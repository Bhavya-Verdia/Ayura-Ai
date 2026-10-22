import React, { useState } from 'react'
import {
  Sun, Leaf, Sparkles, AlertTriangle, Droplets, Calendar, ShieldCheck, Flame, Beaker, ArrowRight,
  ChevronDown, ChevronUp, Pill,
} from 'lucide-react'
import { DOSHA_COLOR, doshaInk } from '../../constants/dosha'

import { tr } from '../../lib/tr'
import { Trans } from 'react-i18next'
const PHASE_ICON  = {
  purvakarma: Droplets, pradhana: Flame, paschat: Sparkles,
  deepana_pachana: Flame, shamana: Leaf, brimhana: Sparkles,
}


// A protocol section that opens on click. The view used to render all five
// inline — 4,462px of unbroken prose on a phone with not one control on the
// page. The clinical header and phase strip above stay open; everything below
// is disclosure, so the plan opens as a summary you can scan in one screen.
function PkSection({ icon: Icon, title, summary, children, open, onToggle }) {
  return (
    <div className={`pk-section pk-section-collapsible${open ? ' open' : ''}`}>
      <h3 className="pk-section-heading">
        <button
          type="button"
          className="pk-section-title pk-section-toggle"
          onClick={onToggle}
          aria-expanded={open}
        >
          <Icon size={14} />
          <span className="pk-section-title-text">{title}</span>
          {!open && summary && <span className="pk-section-summary">{summary}</span>}
          {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
      </h3>
      {open && <div className="pk-section-body">{children}</div>}
    </div>
  )
}


export function PanchakarmaView({ plan }) {
  const cd      = plan.clinical_decisions || {}
  const elig    = cd.shodhana_or_shamana || {}
  const pk      = cd.pradhana_karma_selected || {}
  const ritu    = cd.ritu_context || {}
  const bs      = cd.basti_subtype || null
  const ph      = plan.phase_breakdown || {}
  const unmapped = cd.unmapped_conditions || []
  const rareAssessment = plan.rare_disease_assessment || null
  // The safety triage for diagnoses outside the engine's vocabulary. Distinct from
  // `rare_disease_assessment`, which is narrative the enricher adds afterwards:
  // these findings ran BEFORE the plan and are the reason it looks as it does.
  const triage = cd.condition_triage || []
  // Which of those assessments actually steered the therapy pool. Shown beside the
  // condition, because a signal that changes the plan and is never stated is one the
  // patient and their Vaidya cannot argue with.
  const doshaInfluence = cd.triage_dosha_influence || []
  const secondaryDeferred = cd.secondary_karma_deferred || null
  const sn   = plan.snehana_protocol || {}
  const aus  = plan.aushadha || {}
  const sk   = plan.samsarjana_krama || []
  // Two answers the plan used to take and never mention. `diet_adherence_ability`
  // and `access_to_ayurvedic_herbs` reached the therapy pool and stopped there, so
  // a patient could decline the therapeutic diet and be handed a seven-stage Peya
  // ladder, or say they cannot obtain formulations and be prescribed three.
  const samsarjanaNotice = plan.samsarjana_notice || null
  const procurementNotice = plan.procurement_notice || null
  const sch  = plan.daily_schedule || []
  const us   = plan.user_summary || {}

  const vikritiDom = cd.vikriti_dominant || us.vikriti_dominant || '—'
  const doshaColor = DOSHA_COLOR[vikritiDom] || DOSHA_COLOR.default
  const doshaText = doshaInk(vikritiDom)
  // Three verdicts, not two. "Shamana" used to mean both "you are at home" and
  // "you are too depleted to purify", so the badge could not distinguish a mild
  // home cleanse from a withheld one — and read as reassurance either way.
  const isShamana  = elig.type === 'shamana'
  const isMridu    = elig.type === 'mridu_shodhana'
  const isShodhana = elig.type === 'shodhana'
  const isClinic = us.setting === 'clinic'
  const sp = plan.shamana_protocol || null
  const VERDICT = isShamana
    ? { cls: 'pk-shamana',  label: tr('ui.panchakarmaView.shamanaPurificationWithheld', 'Shamana (Purification Withheld)') }
    : isMridu
      ? { cls: 'pk-mridu',  label: tr('ui.panchakarmaView.mriduShodhanaMildPurification', 'Mridu Shodhana (Mild Purification)') }
      : { cls: 'pk-shodhana', label: tr('ui.panchakarmaView.shodhanaPurification', 'Shodhana (Purification)') }

  const phaseList = ph.phases?.length ? ph.phases : [
    { key: 'purvakarma', label: tr('ui.panchakarmaView.purvakarma', 'Purvakarma'), days: ph.purvakarma_days, sub: tr('ui.panchakarmaView.snehanaSwedanaPreparation', 'Snehana + Swedana (Preparation)') },
    { key: 'pradhana',   label: tr('ui.panchakarmaView.pradhanaKarma', 'Pradhana Karma'), days: ph.pradhana_karma_days, sub: (pk.primary || '').replace(/_/g, ' ') },
    { key: 'paschat',    label: tr('ui.panchakarmaView.paschatKarma', 'Paschat Karma'), days: ph.paschat_karma_days, sub: tr('ui.panchakarmaView.samsarjanaKramaRasayana', 'Samsarjana Krama + Rasayana') },
  ]

  // `withheld_aushadha` is a list of dropped formulations, rendered separately
  // below — it is not itself an Aushadha row.
  const aushadhaRows = Object.entries(aus).filter(
    ([k, v]) => v && !['withheld_aushadha', 'unverified_against'].includes(k)
  )

  // Which protocol sections are open. All closed on arrival — see PkSection.
  const [openSections, setOpenSections] = useState(new Set())
  const toggleSection = (key) => setOpenSections(prev => {
    const next = new Set(prev)
    next.has(key) ? next.delete(key) : next.add(key)
    return next
  })
  const sectionKeys = [
    sp && 'shamana',
    (sn.internal_ghrita || sn.abhyanga_oil) && 'snehana',
    aushadhaRows.length > 0 && 'aushadha',
    sk.length > 0 && 'samsarjana',
    sch.length > 0 && 'schedule',
    rareAssessment && Object.keys(rareAssessment).length > 0 && 'rare',
  ].filter(Boolean)
  const allSectionsOpen = sectionKeys.length > 0 && openSections.size === sectionKeys.length
  const toggleAllSections = () => setOpenSections(
    allSectionsOpen ? new Set() : new Set(sectionKeys)
  )
  const sec = (key) => ({ open: openSections.has(key), onToggle: () => toggleSection(key) })

  const AGNI_LABEL  = { sama: 'Sama Agni', vata: 'Vishama Agni', pitta: 'Tikshna Agni', kapha: 'Manda Agni' }
  const BALA_LABEL  = { uttama: 'Uttama Bala', madhyama: 'Madhyama Bala', manda: 'Manda Bala' }

  return (
    <div className="pk-view">

      {/* ── Clinic Vaidya Gate Banner ── */}
      {isClinic && (
        <div className="pk-vaidya-banner">
          <ShieldCheck size={16} className="pk-vaidya-icon" />
          <div className="pk-vaidya-text">
            <strong>{tr('ui.panchakarmaView.clinicalReferencePlanForVaidya', 'Clinical Reference Plan — For Vaidya Consultation')}</strong>
            <p>{tr('ui.panchakarmaView.thisPlanIsGeneratedUsing', 'This plan is generated using classical Ayurvedic protocols and is designed to be reviewed with a qualified Vaidya (BAMS/MD Ayurveda) before implementation. Do not self-administer Shodhana therapies (Vamana, Virechana, Niruha Basti). Share this plan at your next consultation.')}</p>
          </div>
        </div>
      )}

      {/* ── Deferral ── the one finding that postpones the plan rather than
          narrowing it. It sits above everything because it is an instruction not
          to start, and a plan the patient reads first is a plan they may begin. */}
      {cd.deferral && (
        <div className="pk-deferral-banner">
          <AlertTriangle size={16} className="pk-deferral-icon" />
          <div className="pk-deferral-text">
            <strong><Trans i18nKey="ui.panchakarmaView.doNotStartYet" defaults={"Do not start yet — {{reason}}"} values={{ reason: cd.deferral.reason }} /></strong>
            <p>{cd.deferral.notice}</p>
            <p className="pk-deferral-resume"><strong>{tr('ui.panchakarmaView.resumeWhen', 'Resume when:')}</strong> {cd.deferral.resume_when}</p>
          </div>
        </div>
      )}

      {/* ── Clinical Decision Header ── */}
      <div className="pk-decision-header">
        <div className="pk-header-top-row">
          <div className="pk-dosha-pill" style={{ background: `${doshaColor}18`, borderColor: `${doshaColor}55`, color: doshaText }}><Trans i18nKey="ui.panchakarmaView.vikriti" defaults={"Vikriti: {{value}} {{value2}}"} values={{ value: vikritiDom.toUpperCase(), value2: cd.vikriti_secondary ? ` + ${cd.vikriti_secondary.toUpperCase()}` : '' }} /></div>
          <div className={`pk-eligibility-badge ${VERDICT.cls}`}>
            <ShieldCheck size={13} />
            {VERDICT.label}
          </div>
        </div>

        {/* Agni + Bala + Ama + Ojas quick stats */}
        <div className="pk-vitals-row">
          {us.agni_type && (
            <div className="pk-vital-chip">
              <span className="pk-vital-k">{tr('ui.panchakarmaView.agni', 'Agni')}</span>
              <span className="pk-vital-v">{AGNI_LABEL[us.agni_type] || us.agni_name || us.agni_type}</span>
            </div>
          )}
          {(elig.bala || us.bala) && (
            <div className="pk-vital-chip">
              <span className="pk-vital-k">{tr('ui.panchakarmaView.bala', 'Bala')}</span>
              <span className="pk-vital-v">{BALA_LABEL[elig.bala || us.bala] || elig.bala_note || us.bala_note}</span>
            </div>
          )}
          {us.ama_indicator && us.ama_indicator !== 'none' && (
            <div className="pk-vital-chip pk-vital-warn">
              <span className="pk-vital-k">{tr('ui.panchakarmaView.ama', 'Ama')}</span>
              <span className="pk-vital-v">{us.ama_indicator}</span>
            </div>
          )}
          {us.ojas_level && (
            <div className="pk-vital-chip">
              <span className="pk-vital-k">{tr('ui.panchakarmaView.ojas', 'Ojas')}</span>
              <span className="pk-vital-v">{us.ojas_level}</span>
            </div>
          )}
          {us.koshtha && (
            <div className="pk-vital-chip">
              <span className="pk-vital-k">{tr('ui.panchakarmaView.koshtha', 'Koshtha')}</span>
              <span className="pk-vital-v">
                {us.koshtha === 'krura' ? tr('ui.panchakarmaView.kruraHard', 'Krura (Hard)') : us.koshtha === 'mridu' ? tr('ui.panchakarmaView.mriduLoose', 'Mridu (Loose)') : tr('ui.panchakarmaView.samaRegular', 'Sama (Regular)')}
              </span>
            </div>
          )}
        </div>

        {/* Every reason, not just the first. A patient blocked on three counts
            saw one of them, which made the verdict look like a technicality. */}
        {!isShodhana && elig.reasons?.length > 0 && (
          <>
            {/* Why purification was withheld, and by whom. The engine has always
                distinguished a clinical bar (a Vaidya has to clear it) from a
                verdict reached because the answers given leave no Karma to run —
                but it wrote `clinically_ineligible` five times and nothing, here
                or on the server, ever read it. A patient who could qualify by
                changing one answer was left reading the same wall as a patient
                who cannot. */}
            <div className="pk-shamana-kind">
              {elig.clinically_ineligible !== false
                ? tr('ui.panchakarmaView.purificationIsWithheldOnClinical', 'Purification is withheld on clinical grounds. A qualified Vaidya has to clear these before Shodhana.')
                : elig.unassessed_condition
                  ? tr('ui.panchakarmaView.nobodyHasFoundYouUnfit', 'Nobody has found you unfit for purification — a diagnosis you entered could not be assessed against the classical criteria. A Vaidya can settle it in one consultation.')
                  : tr('ui.panchakarmaView.purificationIsWithheldByThe', 'Purification is withheld by the preferences this plan was built from, not by a clinical bar — changing those answers may open it up.')}
            </div>
            <ul className="pk-shamana-reasons">
              {elig.reasons.map((r, i) => <li key={i} className="pk-shamana-reason">{r}</li>)}
            </ul>
          </>
        )}

        {elig.ama_correction_needed && (
          <div className="pk-ama-warning">
            <AlertTriangle size={13} />
            <span><Trans i18nKey="ui.panchakarmaView.amaCorrectionRequiredFirst" defaults={"Ama correction required first: {{value}} — {{ama_correction_duration}}"} values={{ value: (elig.ama_correction_herbs || []).slice(0, 3).join(', '), ama_correction_duration: elig.ama_correction_duration }} /></span>
          </div>
        )}

        {/* Kriya Kala. The stage was computed from the patient's own check-in
            answers, persisted, handed to the engine and read by nothing — while the
            enricher prompt required the narrative to justify the verdict "in
            classical terms (Bala, Agni, Ama, Ritu, Kriya Kala)", so that one term
            was the model's invention. It is ADVISORY: `shamana_only_criteria`,
            which is what decides eligibility, does not mention Kriya Kala at all.
            Rendered here rather than left to the narrative alone so it is not a
            second claim shown to nobody. */}
        {elig.kriya_kala && (
          <div className={elig.kriya_kala.alignment === 'in_window' ? 'pk-kriyakala' : 'pk-kriyakala pk-kriyakala-off'}>
            {elig.kriya_kala.alignment !== 'in_window' && <AlertTriangle size={13} />}
            <div>
              <span className="pk-kriyakala-stage"><Trans i18nKey="ui.panchakarmaView.diseaseStage" defaults={"Disease stage: {{governing_stage_label}}"} values={{ governing_stage_label: elig.kriya_kala.governing_stage_label }} /></span>
              <p className="pk-kriyakala-note">{elig.kriya_kala.note}</p>
              {elig.kriya_kala.out_of_window_conditions?.length > 1 && (
                <p className="pk-kriyakala-note"><Trans i18nKey="ui.panchakarmaView.alsoOutsideTheWindow" defaults={"Also outside the window: {{value}}"} values={{ value: elig.kriya_kala.out_of_window_conditions
                    .filter(c => c.condition !== elig.kriya_kala.governing_condition)
                    .map(c => `${c.condition} (${c.stage_label})`).join(', ') }} /></p>
              )}
            </div>
          </div>
        )}

        {/* Safety substitution alert */}
        {pk.safety_substitution && (
          <div className="pk-safety-sub">
            <AlertTriangle size={13} />
            <span>{pk.reason}</span>
          </div>
        )}

        {/* Per-karma safety warnings. Only the one-line summary of a substitution
            is dropped, because the alert above already states it. Hiding the whole
            list whenever a substitution happened hid every other caution with it —
            a hypertensive patient on insulin never saw the insulin warning. */}
        {(cd.safety_warnings || [])
          .filter(w => !(pk.safety_substitution && /^(SAFETY SUBSTITUTION|ROUTE RESTRICTED):/.test(w)))
          // Rendered item by item in the allergy block below.
          .filter(w => !(cd.allergen_review?.findings?.length && w.startsWith('ALLERGY:')))
          .map((w, i) => (
            <div key={i} className="pk-ama-warning"><AlertTriangle size={13} /><span>{w}</span></div>
          ))}

        {/* Medicines the patient takes, as the procedures see them. */}
        {cd.medication_review && (cd.medication_review.prescriber_notice || cd.medication_review.notice) && (
          <div className="pk-medication-review">
            <h3 className="pk-unmapped-title"><Pill size={13} />{' '}{tr('ui.panchakarmaView.yourMedicinesAndThisPlan', 'Your medicines and this plan')}</h3>
            {cd.medication_review.matched?.length > 0 && (
              <ul className="pk-medication-list">
                {cd.medication_review.matched.map(m => (
                  <li key={m.medication}><strong>{m.medication}</strong> — {m.classes.join(', ')}</li>
                ))}
              </ul>
            )}
            {cd.medication_review.prescriber_notice && (
              <p className="pk-unmapped-note">{cd.medication_review.prescriber_notice}</p>
            )}
            {cd.medication_review.notice && (
              <p className="pk-unmapped-note">{cd.medication_review.notice}</p>
            )}
          </div>
        )}

        {/* Narrative sentences the deterministic gate withheld. Shown as a count
            so a gap in the coaching reads as a decision, not an omission. */}
        {plan.coaching_withheld?.length > 0 && (
          <p className="pk-unmapped-note">{plan.coaching_withheld.length === 1
            ? tr('ui.panchakarmaView.withheldOne', '1 line of the AI coaching was withheld because it contradicted this plan ({{reasons}}).', { reasons: [...new Set(plan.coaching_withheld.map(w => w.reason))].join('; ') })
            : tr('ui.panchakarmaView.withheldMany', '{{count}} lines of the AI coaching were withheld because they contradicted this plan ({{reasons}}).', { count: plan.coaching_withheld.length, reasons: [...new Set(plan.coaching_withheld.map(w => w.reason))].join('; ') })}</p>
        )}

        {/* Declared allergies, screened against every substance the plan names. */}
        {cd.allergen_review && (cd.allergen_review.findings?.length > 0 || cd.allergen_review.unrecognised_notice) && (
          <div className="pk-medication-review pk-allergen-review">
            <h3 className="pk-unmapped-title"><AlertTriangle size={13} />{' '}{tr('ui.panchakarmaView.yourAllergiesAndThisPlan', 'Your allergies and this plan')}</h3>
            {cd.allergen_review.findings?.length > 0 && (
              <>
                <p className="pk-unmapped-note">
                  {tr('ui.panchakarmaView.doNotUseTheseAs', 'Do not use these as written. Each needs a preparation made without the allergen — ask the Vaidya before day 1.')}
                </p>
                <ul className="pk-medication-list">
                  {cd.allergen_review.findings.map(f => (
                    <li key={f.allergy}>
                      <strong>{f.allergy}</strong> — {f.items.join('; ')}
                      {f.substitute && <> <em><Trans i18nKey="ui.panchakarmaView.askFor" defaults={"(ask for {{substitute}})"} values={{ substitute: f.substitute }} /></em></>}
                    </li>
                  ))}
                </ul>
              </>
            )}
            {cd.allergen_review.unrecognised_notice && (
              <p className="pk-unmapped-note">{cd.allergen_review.unrecognised_notice}</p>
            )}
          </div>
        )}

        {/* Unmapped / rare disease notice */}
        {unmapped.length > 0 && (
          <div className="pk-unmapped-banner">
            <h3 className="pk-unmapped-title">
              <AlertTriangle size={13} />{' '}{tr('ui.panchakarmaView.rareUnmappedConditionsDetectedVaidya', 'Rare / Unmapped Conditions Detected — Vaidya Review Required')}
            </h3>
            <div className="pk-unmapped-chips">
              {unmapped.map(c => (
                <span key={c} className="pk-unmapped-chip">
                  {c.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </span>
              ))}
            </div>
            <p className="pk-unmapped-note">
              {tr('ui.panchakarmaView.theseConditionsAreNotIn', 'These conditions are not in the classical Ayurvedic disease database. The AI has reasoned about them using Nidana-Samprapti inference below. All decisions must be reviewed by a qualified Vaidya (BAMS/MD Ayurveda) before proceeding.')}
            </p>
          </div>
        )}
      </div>

      {/* What the chosen goal actually changed. The field used to be collected and
          then read by no engine code, so there was nothing to show. */}
      {cd.goal?.notes?.length > 0 && (
        <div className="pk-rationale">
          <span className="pk-rationale-label"><Trans i18nKey="ui.panchakarmaView.goal" defaults={"Goal — {{label}}"} values={{ label: cd.goal.label }} /></span>
          {cd.goal.notes.map((n, i) => <p key={i}>{n}</p>)}
        </div>
      )}

      {/* ── Pradhana Karma + Ritu row ── */}
      <div className="pk-info-row">
        <div className="pk-info-card">
          <div className="pk-info-label"><Beaker size={12} />{' '}{tr('ui.panchakarmaView.selectedTherapy', 'Selected Therapy')}</div>
          <div className="pk-info-value">
            {isShamana
              ? tr('ui.panchakarmaView.noneShamana', 'None — Shamana')
              : (pk.primary || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
          </div>
          {isShamana
            ? <div className="pk-info-sub">{tr('ui.panchakarmaView.noPradhanaKarma', 'No Pradhana Karma')}</div>
            : bs && <div className="pk-info-sub">{bs.name}</div>}
        </div>
        <div className="pk-info-card">
          <div className="pk-info-label"><Calendar size={12} />{' '}{tr('ui.panchakarmaView.seasonRitu', 'Season (Ritu)')}</div>
          <div className="pk-info-value">{ritu.ritu_name || ritu.ritu || '—'}</div>
          {/* The season's ideal Shodhana is reference data, not a recommendation.
              Printing "Ideal: VIRECHANA" on a plan that withholds Virechana names
              the therapy this plan just refused. */}
          {!isShamana && (
            <div className="pk-info-sub"><Trans i18nKey="ui.panchakarmaView.ideal" defaults={"Ideal: {{value}}"} values={{ value: (ritu.primary_shodhana || '—').toUpperCase() }} /></div>
          )}
        </div>
        <div className="pk-info-card">
          <div className="pk-info-label"><Sun size={12} />{' '}{tr('ui.panchakarmaView.duration', 'Duration')}</div>
          <div className="pk-info-value">{ph.total_days ? `${ph.total_days} ${ph.total_days === 1 ? 'day' : 'days'}` : '—'}</div>
          <div className="pk-info-sub">{ph.purvakarma_days}P · {ph.pradhana_karma_days}M · {ph.paschat_karma_days}R</div>
        </div>
      </div>

      {cd.ritu_warning && (
        <div className="pk-ritu-warning">
          <AlertTriangle size={13} /> {cd.ritu_warning}
        </div>
      )}

      {/* The course can run longer than requested; it may never do so silently. */}
      {ph.duration_notice && (
        <div className="pk-ritu-warning">
          <AlertTriangle size={13} /> {ph.duration_notice}
        </div>
      )}

      {pk.reason && (
        <div className="pk-rationale">
          <span className="pk-rationale-label">{tr('ui.panchakarmaView.clinicalRationale', 'Clinical Rationale')}</span>
          <p>{pk.reason}</p>
        </div>
      )}

      {/* The classical mapping names a SECOND Karma for this Vikriti — for Pitta,
          Raktamokshana. The engine computed it and dropped it, so a cited clinical
          claim never reached the person it was about. It is deliberately not
          scheduled (sequencing a second Pradhana Karma needs a Vaidya), which is
          exactly why it has to say so rather than simply be absent — and why the
          copy leads with "not part of this plan" instead of naming the procedure
          first. */}
      {secondaryDeferred && (
        <div className="pk-deferred">
          <span className="pk-deferred-label">{tr('ui.panchakarmaView.notPartOfThisPlan', 'Not part of this plan')}</span>
          <p><Trans i18nKey="ui.panchakarmaView.n00IsClassicallyIndicated" defaults={"<0>{{value}}</0> is classically indicated alongside your primary Karma for this Vikriti, and this plan does <1>not</1> include it."} values={{ value: (secondaryDeferred.karma || '').replace(/_/g, ' ') }} components={[<strong />, <strong />]} /></p>
          <p className="pk-deferred-why">{secondaryDeferred.deferral}</p>
          {secondaryDeferred.clinical_note && (
            <p className="pk-deferred-note">{secondaryDeferred.clinical_note}</p>
          )}
        </div>
      )}

      {/* ── Phase Timeline ── */}
      <div className="pk-phases">
        {/* Driven by the engine's own phase list. The Shamana arm has differently
            named phases (Deepana-Pachana → Shamana Chikitsa → Brimhana), and a
            hardcoded Purvakarma/Pradhana/Paschat strip could only mislabel them. */}
        {phaseList.map((phase, i) => {
          const Icon = PHASE_ICON[phase.key] || Sparkles
          return (
            <React.Fragment key={phase.key}>
              <div className="pk-phase-block">
                <div className="pk-phase-icon-wrap"><Icon size={15} /></div>
                <div className="pk-phase-days">{phase.days} {phase.days === 1 ? 'day' : 'days'}</div>
                <div className="pk-phase-name">{phase.label}</div>
                <div className="pk-phase-sub">{phase.sub}</div>
              </div>
              {i < phaseList.length - 1 && <ArrowRight size={16} className="pk-phase-arrow" />}
            </React.Fragment>
          )
        })}
      </div>

      {/* ── Snehana Protocol ── */}
      {sectionKeys.length > 0 && (
        <div className="plan-days-toolbar">
          <h3 className="plan-days-toolbar-title"><Trans i18nKey="ui.panchakarmaView.protocolDetailSections" defaults={"Protocol detail — {{length}} sections"} values={{ length: sectionKeys.length }} /></h3>
          <button type="button" className="plan-days-toolbar-btn" onClick={toggleAllSections}>
            {allSectionsOpen ? tr('ui.panchakarmaView.collapseAll', 'Collapse all') : tr('ui.panchakarmaView.expandAll', 'Expand all')}
          </button>
        </div>
      )}

      {sp && (
        <PkSection
          icon={Leaf}
          title={tr('ui.panchakarmaView.shamanaProtocolWhatReplacesThe', 'Shamana Protocol — what replaces the cleanse')}
          summary={sp.deepana_pachana?.needed ? 'Agni · pacification · Brimhana' : 'pacification · Brimhana'}
          {...sec('shamana')}
        >
          <p className="pk-shamana-why">{sp.why}</p>

          {sp.deepana_pachana?.needed && (
            <div className="pk-aus-card">
              <div className="pk-aus-label">{tr('ui.panchakarmaView.deepanaPachanaAgniCorrection', 'Deepana-Pachana (Agni correction)')}</div>
              <div className="pk-aus-name">{(sp.deepana_pachana.herbs || []).join(' · ')}</div>
              <div className="pk-aus-use">{sp.deepana_pachana.why}</div>
              <div className="pk-aus-use"><Trans i18nKey="ui.panchakarmaView.duration2" defaults={"Duration: {{duration}}"} values={{ duration: sp.deepana_pachana.duration }} /></div>
              {sp.deepana_pachana.signs_cleared?.length > 0 && (
                <div className="pk-aus-use"><Trans i18nKey="ui.panchakarmaView.clearedWhen" defaults={"Cleared when: {{value}}"} values={{ value: sp.deepana_pachana.signs_cleared.join('; ') }} /></div>
              )}
              {sp.deepana_pachana.diet && <div className="pk-aus-use">{sp.deepana_pachana.diet}</div>}
            </div>
          )}

          {sp.shamana_chikitsa && (
            <div className="pk-aus-card">
              <div className="pk-aus-label">{tr('ui.panchakarmaView.shamanaChikitsa', 'Shamana Chikitsa')}</div>
              <div className="pk-aus-name">{sp.shamana_chikitsa.principle}</div>
              <div className="pk-aus-use"><strong>{tr('ui.panchakarmaView.sneha', 'Sneha:')}</strong> {sp.shamana_chikitsa.sneha_matra}</div>
              <div className="pk-aus-use"><strong>{tr('ui.panchakarmaView.ahara', 'Ahara:')}</strong> {sp.shamana_chikitsa.ahara}</div>
              <div className="pk-aus-use"><strong>{tr('ui.panchakarmaView.vihara', 'Vihara:')}</strong> {sp.shamana_chikitsa.vihara}</div>
            </div>
          )}

          {sp.brimhana && (
            <div className="pk-aus-card">
              <div className="pk-aus-label">{tr('ui.panchakarmaView.brimhanaRasayana', 'Brimhana Rasayana')}</div>
              <div className="pk-aus-name">
                {sp.brimhana.rasayana?.herb || '—'}
                {sp.brimhana.rasayana?.dose ? ` — ${sp.brimhana.rasayana.dose}` : ''}
              </div>
              <div className="pk-aus-use">{sp.brimhana.why}</div>
            </div>
          )}

          <p className="pk-shamana-reassess">
            <AlertTriangle size={13} /> {sp.reassessment}
          </p>
        </PkSection>
      )}

      {(sn.internal_ghrita || sn.abhyanga_oil) && (
        <PkSection
          icon={Droplets}
          title={tr('ui.panchakarmaView.snehanaProtocolInternalExternalOleation', 'Snehana Protocol (Internal + External Oleation)')}
          summary={[sn.internal_ghrita && 'internal', sn.abhyanga_oil && 'abhyanga'].filter(Boolean).join(' · ')}
          {...sec('snehana')}
        >
          <div className="pk-aus-grid">
            {sn.internal_ghrita && (
              <div className="pk-aus-card">
                <div className="pk-aus-label">{tr('ui.panchakarmaView.internalSnehana', 'Internal Snehana')}</div>
                <div className="pk-aus-name">
                  {typeof sn.internal_ghrita === 'object'
                    ? (sn.internal_ghrita.primary || sn.internal_ghrita.name || JSON.stringify(sn.internal_ghrita))
                    : sn.internal_ghrita}
                </div>
                {sn.dose_schedule?.length > 0 && (
                  <>
                    {/* The last day is the step-down, so "first → last" hid the peak. */}
                    <div className="pk-aus-sub"><Trans i18nKey="ui.panchakarmaView.day1MlPeakMl" defaults={"Day 1: {{dose_ml}}ml → peak {{value}}ml {{value2}}"} values={{ dose_ml: sn.dose_schedule[0]?.dose_ml, value: Math.max(...sn.dose_schedule.map(d => d.dose_ml || 0)), value2: sn.dose_schedule.length >= 3 && <> → Day {sn.dose_schedule.length}: {sn.dose_schedule[sn.dose_schedule.length - 1]?.dose_ml}ml</> }} /></div>
                    {sn.matra?.basis && <div className="pk-aus-sub">{sn.matra.basis}</div>}
                  </>
                )}
              </div>
            )}
            {sn.abhyanga_oil && (
              <div className="pk-aus-card">
                <div className="pk-aus-label">{tr('ui.panchakarmaView.abhyangaOil', 'Abhyanga Oil')}</div>
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
              <div className="pk-signs-label">{tr('ui.panchakarmaView.signsOfAdequateSnehanaSamyak', 'Signs of Adequate Snehana (Samyak Snigdha Lakshana)')}</div>
              <ul className="pk-signs-list">
                {sn.signs_adequate.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
              {/* Snehapana is judged by these signs, not by the calendar. The
                  classical day count used to be printed as a bare number beside a
                  phase half its length — a card reading 7 above a 2-day schedule. */}
              {sn.adequacy?.instruction && (
                <p className={sn.adequacy.truncated ? 'pk-signs-warn' : 'pk-signs-note'}>
                  {sn.adequacy.truncated && <AlertTriangle size={12} />}
                  {' '}{sn.adequacy.instruction}
                </p>
              )}
            </div>
          )}
        </PkSection>
      )}

      {/* ── Aushadha ── */}
      {aushadhaRows.length > 0 && (
        <PkSection
          icon={Beaker}
          title={tr('ui.panchakarmaView.aushadhaMedicinesOils', 'Aushadha (Medicines & Oils)')}
          summary={aushadhaRows.length === 1 ? tr('ui.panchakarmaView.itemsOne', '1 item') : tr('ui.panchakarmaView.itemsMany', '{{count}} items', { count: aushadhaRows.length })}
          {...sec('aushadha')}
        >
          {procurementNotice && (
            <div className="pk-ritu-warning">
              <AlertTriangle size={13} /> {procurementNotice}
            </div>
          )}
          <div className="pk-aus-grid">
            {aushadhaRows.map(([k, v]) => {
              const name = typeof v === 'object' ? (v.name || v.herb || v.primary || '') : v
              const desc = typeof v === 'object' ? (v.use || v.dose || v.rationale || '') : ''
              const withheld = v?.components_withheld || []
              const cautions = v?.component_cautions || []
              const interactions = v?.drug_interactions || []
              // A formulation with no safe constituent left is reported rather than
              // omitted: an absent adjuvant looks identical to one that was never
              // indicated, and the Vaidya needs to know it was considered.
              if (!name) {
                if (k === 'rasayana' && v?.unavailable_reason) {
                  return (
                    <div key={k} className="pk-aus-card pk-aus-card-withheld">
                      <div className="pk-aus-label">{tr('ui.panchakarmaView.rasayana', 'Rasayana')}</div>
                      <div className="pk-aus-name">{tr('ui.panchakarmaView.notPrescribed', 'Not prescribed')}</div>
                      <div className="pk-aus-sub">{v.unavailable_reason}</div>
                    </div>
                  )
                }
                return null
              }
              return (
                <div key={k} className="pk-aus-card">
                  <div className="pk-aus-label">{k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</div>
                  <div className="pk-aus-name">{name}</div>
                  {desc && <div className="pk-aus-sub">{String(desc).slice(0, 80)}</div>}
                  {v?.substitution_note && (
                    <div className="pk-aus-note"><AlertTriangle size={11} /> {v.substitution_note}</div>
                  )}
                  {/* Which constituent was removed and why. Naming the formulation
                      without naming the omission would have the patient buy the
                      preparation off a shelf with the withheld herb still in it. */}
                  {withheld.map((w, i) => (
                    <div key={`w${i}`} className="pk-aus-withheld">
                      <AlertTriangle size={11} />
                      <span><strong><Trans i18nKey="ui.panchakarmaView.omit" defaults={"Omit {{herb}}"} values={{ herb: w.herb }} /></strong> — {w.reasons?.[0]?.mechanism}</span>
                    </div>
                  ))}
                  {cautions.map((c, i) => (
                    <div key={`c${i}`} className="pk-aus-note">
                      {c.herb}: {c.notes?.[0]?.mechanism}
                    </div>
                  ))}
                  {/* Already taking a constituent under another name — doubling the
                      dose. Flagged rather than withheld: the usual answer is to stop
                      the self-administered one, which is theirs to decide. */}
                  {(v?.already_taking || []).map((d, i) => (
                    <div key={`d${i}`} className="pk-aus-note">
                      <AlertTriangle size={11} />
                      <span><strong><Trans i18nKey="ui.panchakarmaView.alreadyTaking" defaults={"Already taking {{already_taking}}"} values={{ already_taking: d.already_taking }} /></strong> — {d.note}</span>
                    </div>
                  ))}
                  {interactions.map((x, i) => (
                    <div key={`i${i}`} className="pk-aus-withheld">
                      <AlertTriangle size={11} />
                      <span><strong><Trans i18nKey="ui.panchakarmaView.yourMedication" defaults={"{{herb}} × your medication"} values={{ herb: x.herb }} /></strong> — {x.effect || x.recommendation}</span>
                    </div>
                  ))}
                </div>
              )
            })}

            {/* Every Aushadha gate matches condition tokens, so an unmapped
                diagnosis passes all of them by never being seen. The plan says so
                rather than implying a clean check. */}
            {aus.unverified_against && (
              <div className="pk-aus-card pk-aus-card-withheld">
                <div className="pk-aus-label">{tr('ui.panchakarmaView.notVerifiedAgainst', 'Not verified against')}</div>
                <div className="pk-aus-name">
                  {aus.unverified_against.conditions.map(c => c.replace(/_/g, ' ')).join(', ')}
                </div>
                <div className="pk-aus-sub">{aus.unverified_against.notice}</div>
              </div>
            )}

            {(aus.withheld_aushadha || []).map((w, i) => (
              <div key={`dropped${i}`} className="pk-aus-card pk-aus-card-withheld">
                <div className="pk-aus-label">{w.id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</div>
                <div className="pk-aus-name"><Trans i18nKey="ui.panchakarmaView.withheld" defaults={"Withheld — {{name}}"} values={{ name: w.name }} /></div>
                <div className="pk-aus-sub">{w.reason}</div>
                {(w.withheld || []).map((h, j) => (
                  <div key={j} className="pk-aus-withheld">
                    <AlertTriangle size={11} />
                    <span><strong>{h.herb}</strong> — {h.reasons?.[0]?.mechanism}</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </PkSection>
      )}

      {/* ── Samsarjana Krama ── */}
      {sk.length > 0 && (
        <PkSection
          icon={Leaf}
          title={tr('ui.panchakarmaView.samsarjanaKramaDietaryReEntry', 'Samsarjana Krama (Dietary Re-entry)')}
          summary={`${sk.length} stages`}
          {...sec('samsarjana')}
        >
          <p className="pk-sk-intro">{tr('ui.panchakarmaView.criticalPostShodhanaReFeeding', 'Critical post-Shodhana re-feeding protocol. Skipping this risks Dhatu Kshaya.')}</p>
          {samsarjanaNotice && (
            <div className="pk-ritu-warning">
              <AlertTriangle size={13} /> {samsarjanaNotice}
            </div>
          )}
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
        </PkSection>
      )}

      {/* ── Daily Schedule ── */}
      {sch.length > 0 && (
        <PkSection
          icon={Calendar}
          title={tr('ui.panchakarmaView.dailySchedule', 'Daily Schedule')}
          summary={`${sch.length} ${sch.length === 1 ? 'day' : 'days'}`}
          {...sec('schedule')}
        >
          <div className="pk-schedule">
            {sch.map((day) => (
              <div key={day.day} className="pk-day-row">
                <div className="pk-day-num"><Trans i18nKey="ui.panchakarmaView.day" defaults={"Day {{day}}"} values={{ day: day.day }} /></div>
                <div className="pk-day-phase">{(day.phase || '').split(' (')[0]}</div>
                <div className="pk-day-therapies">
                  {/* The Snehapana ladder escalates 30 → 60 → 90 → 120ml. It lived
                      in a summary block while every Purvakarma day read the same,
                      so the day you were on never told you the dose you were due. */}
                  {day.snehapana && (
                    <span className="pk-day-dose"><Trans i18nKey="ui.panchakarmaView.n0SnehapanaMl" defaults={"<0/> Snehapana {{dose_ml}}ml {{value}} {{value2}}"} values={{ dose_ml: day.snehapana.dose_ml, value: day.snehapana.time ? ` · ${day.snehapana.time}` : '', value2: day.snehapana.vehicle ? ` · ${day.snehapana.vehicle}` : '' }} components={[<Droplets size={11} />]} /></span>
                  )}
                  {/* Deepana-Pachana and Brimhana are pinned day actions just as
                      the Pradhana Karma is; rendering only the Karma variant dropped
                      their instructions to a bare chip and lost the notes entirely. */}
                  {(day.therapies || []).map((t, i) =>
                    (t.is_pradhana_karma || t.is_deepana_pachana || t.is_brimhana || t.is_samsarjana) ? (
                      <div key={i} className="pk-pradhana-action">
                        <div className="pk-pradhana-action-header">
                          {(t.is_brimhana || t.is_samsarjana)
                            ? <Sparkles size={12} className="pk-pradhana-flame" />
                            : <Flame size={12} className="pk-pradhana-flame" />}
                          <span className="pk-pradhana-action-name">{t.name}</span>
                          {t.timing && <span className="pk-pradhana-timing">{t.timing}</span>}
                        </div>
                        {/* Steps are discrete now that the prose lives in the KB.
                            A procedure the patient performs on themselves — warm
                            the oil, lie on the left side, retain, watch for these
                            signs — is a sequence to follow, and a single paragraph
                            is the one shape that hides which step you are on. */}
                        {t.steps?.length > 0 ? (
                          <ol className="pk-pradhana-steps">
                            {t.steps.map((s, j) => <li key={j}>{s}</li>)}
                          </ol>
                        ) : t.pradhana_notes && (
                          <p className="pk-pradhana-action-notes">{t.pradhana_notes}</p>
                        )}
                      </div>
                    ) : (
                      <span key={i} className="pk-therapy-chip-wrap">
                        <span className={`pk-therapy-chip${t.cautions?.length ? ' pk-therapy-chip-caution' : ''}`}>
                          {t.name}{t.duration_minutes ? tr('ui.panchakarmaView.min', ' · {{duration_minutes}}min', { duration_minutes: t.duration_minutes }) : ''}
                        </span>
                        {/* A relative contraindication held in the engine and never
                            printed is the same defect as one never checked — the
                            patient does the therapy either way, without the
                            modification that made it safe for them. */}
                        {(t.cautions || []).map((c, j) => (
                          <span key={j} className="pk-therapy-caution">
                            <AlertTriangle size={11} /> {c.mechanism}
                          </span>
                        ))}
                      </span>
                    )
                  )}
                </div>
              </div>
            ))}
          </div>
        </PkSection>
      )}

      {/* ── Safety triage for unrecognised diagnoses ── */}
      {triage.length > 0 && (
        <PkSection
          icon={AlertTriangle}
          title={tr('ui.panchakarmaView.unrecognisedDiagnosisSafetyAssessment', 'Unrecognised Diagnosis — Safety Assessment')}
          summary={triage.length === 1 ? tr('ui.panchakarmaView.conditionsOne', '1 condition') : tr('ui.panchakarmaView.conditionsMany', '{{count}} conditions', { count: triage.length })}
          {...sec('triage')}
        >
          <p className="pk-sk-intro">
            {tr('ui.panchakarmaView.theseDiagnosesAreOutsideThe', 'These diagnoses are outside the engine’s classical vocabulary. Every contraindication check matches on recognised conditions, so an unrecognised one would otherwise pass every check by default rather than clearing it. Each was assessed before this plan was built. The assessments are AI-generated and clinically unreviewed — confirm with a Vaidya.')}
          </p>
          {triage.map((t) => (
            <div key={t.condition} className="pk-rare-card">
              <div className="pk-rare-name">
                {t.condition.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </div>
              {t.outcome === 'shodhana_withheld' ? (
                <div className="pk-rare-row">
                  <span className="pk-rare-k">{tr('ui.panchakarmaView.outcome', 'Outcome')}</span>
                  <span>{tr('ui.panchakarmaView.couldNotBeAssessedPurification', 'Could not be assessed — purification withheld rather than performed unchecked.')}</span>
                </div>
              ) : (
                <>
                  {t.classical_analogue && (
                    <div className="pk-rare-row"><span className="pk-rare-k">{tr('ui.panchakarmaView.classicalAnalogue', 'Classical Analogue')}</span><span>{t.classical_analogue}</span></div>
                  )}
                  {t.srotas && (
                    <div className="pk-rare-row"><span className="pk-rare-k">{tr('ui.panchakarmaView.srotas', 'Srotas')}</span><span>{t.srotas}</span></div>
                  )}
                  {doshaInfluence.filter(i => i.condition === t.condition).map((i, n) => (
                    <div key={n} className="pk-rare-row">
                      <span className="pk-rare-k">{tr('ui.panchakarmaView.effectOnThisPlan', 'Effect on this plan')}</span>
                      <span>{i.effect}</span>
                    </div>
                  ))}
                  <div className="pk-rare-row">
                    <span className="pk-rare-k">{tr('ui.panchakarmaView.shodhana', 'Shodhana')}</span>
                    <span>{String(t.outcome || '').replace(/_/g, ' ')}</span>
                  </div>
                  {Object.entries(t.karma_restrictions || {}).map(([karma, r]) => (
                    <div key={karma} className="pk-rare-row">
                      <span className="pk-rare-k">{karma.replace(/_/g, ' ')} &mdash; {r.severity}</span>
                      <span>{r.mechanism}</span>
                    </div>
                  ))}
                  {t.monitoring && (
                    <div className="pk-rare-row"><span className="pk-rare-k">{tr('ui.panchakarmaView.vaidyaMustMonitor', 'Vaidya must monitor')}</span><span>{t.monitoring}</span></div>
                  )}
                  {t.confidence && (
                    <div className="pk-rare-row"><span className="pk-rare-k">{tr('ui.panchakarmaView.confidence', 'Confidence')}</span><span>{t.confidence}</span></div>
                  )}
                </>
              )}
            </div>
          ))}
        </PkSection>
      )}

      {/* ── Rare Disease Assessment (LLM Nidana-Samprapti inference) ── */}
      {rareAssessment && Object.keys(rareAssessment).length > 0 && (
        <PkSection
          icon={Sparkles}
          title={tr('ui.panchakarmaView.rareDiseaseNidanaSampraptiAssessment', 'Rare Disease Nidana-Samprapti Assessment')}
          summary={Object.keys(rareAssessment).length === 1 ? tr('ui.panchakarmaView.conditionsOne', '1 condition') : tr('ui.panchakarmaView.conditionsMany', '{{count}} conditions', { count: Object.keys(rareAssessment).length })}
          {...sec('rare')}
        >
          <p className="pk-sk-intro">{tr('ui.panchakarmaView.aiInferredAyurvedicAnalysisFor', 'AI-inferred Ayurvedic analysis for conditions outside classical mapping. Verify with a qualified Vaidya.')}</p>
          {Object.entries(rareAssessment).map(([condition, data]) => (
            <div key={condition} className="pk-rare-card">
              <div className="pk-rare-name">{condition.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</div>
              {data.nidana_samprapti && (
                <div className="pk-rare-row"><span className="pk-rare-k">{tr('ui.panchakarmaView.nidanaSamprapti', 'Nidana-Samprapti')}</span><span>{data.nidana_samprapti}</span></div>
              )}
              {data.classical_analogue && (
                <div className="pk-rare-row"><span className="pk-rare-k">{tr('ui.panchakarmaView.classicalAnalogue', 'Classical Analogue')}</span><span>{data.classical_analogue}</span></div>
              )}
              {data.therapy_suitability && (
                <div className="pk-rare-row"><span className="pk-rare-k">{tr('ui.panchakarmaView.therapySuitability', 'Therapy Suitability')}</span><span>{data.therapy_suitability}</span></div>
              )}
              {data.suggested_aushadha && (
                <div className="pk-rare-row"><span className="pk-rare-k">{tr('ui.panchakarmaView.aushadha', 'Aushadha')}</span><span>{data.suggested_aushadha}</span></div>
              )}
              {data.vaidya_note && (
                <div className="pk-rare-row pk-rare-warn"><span className="pk-rare-k">{tr('ui.panchakarmaView.vaidyaMonitor', 'Vaidya Monitor')}</span><span>{data.vaidya_note}</span></div>
              )}
            </div>
          ))}
        </PkSection>
      )}
    </div>
  )
}

// ── Gym dedicated renderer ─────────────────────────────────────────────────────
