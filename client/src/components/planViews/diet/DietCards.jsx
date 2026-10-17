// The diet screen's cards: Pathya-Apathya, the safety banner, the energy
// prescription, the daily nutrient targets, the clinical notes, and the one-line
// targets summary that stands in for the last two above the meals.

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  AlertTriangle, Star, ShieldCheck, Flame, Moon, Target, ChevronDown, ChevronUp, BookOpen, TriangleAlert, ArrowDown,
} from 'lucide-react'
import { SLOT_LABEL } from './dietConstants'

export function PathyaApathyaCard({ pa }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  if (!pa) return null
  const hasContent = pa.pathya?.length || pa.apathya?.length || pa.viruddha_ahara_warnings?.length
  if (!hasContent) return null
  return (
    <div className="diet-pa-card">
      <button className="diet-timing-toggle" onClick={() => setOpen(o => !o)}>
        <ShieldCheck size={13} className="diet-timing-icon" style={{ color: '#16a34a' }} />
        <span>{t('diet.paTitle', 'Pathya-Apathya — Classical Diet Protocol')}</span>
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
              <h3 className="diet-pa-section-title pathya">{t('diet.pathya', 'Pathya — Recommended')}</h3>
              <ul className="diet-pa-list">
                {pa.pathya.map((item, i) => <li key={i}>{item}</li>)}
              </ul>
            </div>
          )}
          {pa.apathya?.length > 0 && (
            <div className="diet-pa-section">
              <h3 className="diet-pa-section-title apathya">{t('diet.apathya', 'Apathya — Avoid')}</h3>
              <ul className="diet-pa-list apathya">
                {pa.apathya.map((item, i) => <li key={i}>{item}</li>)}
              </ul>
            </div>
          )}
          {pa.viruddha_ahara_warnings?.length > 0 && (
            <div className="diet-pa-section">
              <h3 className="diet-pa-section-title viruddha">{t('diet.viruddhaWarnings', 'Viruddha Ahara Warnings')}</h3>
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

// Deterministic Ahara safety banner — surfaces the post-LLM safety scan
// (Viruddha Ahara + allergens across ALL weeks, including compact weeks 2–4
// where per-meal flags can't be shown). Backend: services/ahara_safety.py.

export function DietSafetyBanner({ plan }) {
  const { t } = useTranslation()
  if (!plan?.ahara_safety_checked) return null
  const alerts = plan.safety_alerts || []
  const viruddha = plan.viruddha_ahara_detected || []
  const condAlerts = plan.condition_safety_alerts || []
  const dietTypeAlerts = plan.dietary_type_alerts || []

  const unscanned = plan.conditions_without_food_floor || []
  // Screened against a curated term list, but not against the food library food by
  // food. A thinner check than the one the badge below implies, so it says so.
  const termsOnly = plan.conditions_screened_by_terms_only || []
  // The plan's food-recommending prose, held to the same floor as its meals.
  // `withheld` was removed from the Pathya card before it reached this component;
  // saying so is the point — a recommendation that vanishes with no explanation
  // looks like an oversight, which is the lesson of the withheld Panchakarma Karma.
  const withheld = plan.withheld_recommendations || []
  const proseAlerts = plan.advisory_prose_alerts || []
  // Meals in a script the checks cannot read: never passed as checked.
  const unscannable = plan.unscannable_alerts || []

  if (!alerts.length && !viruddha.length && !condAlerts.length && !dietTypeAlerts.length
      && !withheld.length && !proseAlerts.length && !unscannable.length) {
    if (unscanned.length || termsOnly.length) {
      // "Everything checked" would be false here: these conditions reached no
      // curated rule, no library claim and no usable classification.
      return (
        <div className="diet-safety-ok is-partial">
          <TriangleAlert size={13} />
          <span>
            {t('diet.safetyPartialChecked', 'Checked for allergens, intolerances, incompatible combinations (Viruddha Ahara) and your dietary type — none found.')}
            {unscanned.length > 0 && (
              <> {t('diet.safetyNoRule', 'We could not derive a food-safety rule for {{conditions}}, so this plan has not been screened against them.',
                { conditions: unscanned.map(c => c.replace(/_/g, ' ')).join(', ') })}</>
            )}
            {termsOnly.length > 0 && (
              <> {t('diet.safetyTermsOnly', 'For {{conditions}} we screened against a curated list of foods to avoid, but our food library has not yet been reviewed food-by-food for them — a lighter check than the one we run for conditions like acidity or diabetes.',
                { conditions: termsOnly.map(c => c.replace(/_/g, ' ')).join(', ') })}</>
            )}
            {' '}{t('diet.reviewWithPractitioner', 'Please review this plan with your practitioner.')}
          </span>
        </div>
      )
    }
    return (
      <div className="diet-safety-ok">
        <ShieldCheck size={13} />
        <span>{t('diet.safetyAllClear', 'Every meal, daily drink and line of food guidance checked for allergens, intolerances, incompatible combinations (Viruddha Ahara), condition-contraindicated foods & your dietary type — none found.')}</span>
      </div>
    )
  }
  return (
    <div className="diet-safety-banner">
      {alerts.length > 0 && (
        <div className="diet-safety-card allergen">
          <h3 className="diet-safety-title">
            <TriangleAlert size={13} /> {t('diet.alertAllergenTitle', 'Allergen conflicts — substitute before following these meals')}
          </h3>
          <ul className="diet-safety-list">
            {alerts.map((a, i) => (
              <li key={i}>
                <strong>{a.week} · {a.day} · {a.meal_slot}</strong>: {t('diet.contains', 'contains {{what}}', { what: (a.matched_terms || []).join(', ') })}
              </li>
            ))}
          </ul>
        </div>
      )}
      {unscannable.length > 0 && (
        <div className="diet-safety-card allergen">
          <h3 className="diet-safety-title">
            <TriangleAlert size={13} /> {t('diet.alertScriptTitle', 'Not verified — written in a script our safety checks cannot read')}
          </h3>
          <ul className="diet-safety-list">
            {unscannable.map((u, i) => (
              <li key={i}><strong>{u.week} · {u.day} · {u.meal_slot}</strong>: {t('diet.scriptName', '{{script}} script', { script: u.script })}</li>
            ))}
          </ul>
        </div>
      )}
      {condAlerts.length > 0 && (
        <div className="diet-safety-card allergen">
          <h3 className="diet-safety-title">
            <TriangleAlert size={13} /> {t('diet.alertConditionTitle', 'Foods not advised for your conditions — substitute before following these meals')}
          </h3>
          <ul className="diet-safety-list">
            {condAlerts.map((c, i) => (
              <li key={i}>
                <strong>{c.week} · {c.day} · {c.meal_slot}</strong>: {t('diet.contains', 'contains {{what}}', { what: c.food })} — {c.condition}
              </li>
            ))}
          </ul>
        </div>
      )}
      {dietTypeAlerts.length > 0 && (
        <div className="diet-safety-card allergen">
          <h3 className="diet-safety-title">
            <TriangleAlert size={13} /> {t('diet.alertDietTypeTitle', 'Does not match your dietary type — substitute before following these meals')}
          </h3>
          <ul className="diet-safety-list">
            {dietTypeAlerts.map((d, i) => (
              <li key={i}>
                <strong>{d.week} · {d.day} · {d.meal_slot}</strong>: {t('diet.contains', 'contains {{what}}', { what: d.food })} — {t('diet.notDietType', 'not {{type}}', { type: (d.dietary_type || '').replace(/_/g, ' ') })}
              </li>
            ))}
          </ul>
        </div>
      )}
      {withheld.length > 0 && (
        <div className="diet-safety-card allergen">
          <h3 className="diet-safety-title">
            <TriangleAlert size={13} /> {t('diet.alertWithheldTitle', 'Withheld from your Pathya list — recommended in general, not for you')}
          </h3>
          <ul className="diet-safety-list">
            {withheld.map((w, i) => (
              <li key={i}>
                <strong>{w.item}</strong> — {t('diet.withheldLine', 'names {{food}}, Apathya for {{condition}}', { food: w.food, condition: w.condition })}
              </li>
            ))}
          </ul>
        </div>
      )}
      {proseAlerts.length > 0 && (
        <div className="diet-safety-card allergen">
          <h3 className="diet-safety-title">
            <TriangleAlert size={13} /> {t('diet.alertProseTitle', 'Guidance text that names a food you should avoid')}
          </h3>
          <ul className="diet-safety-list">
            {proseAlerts.map((a, i) => (
              <li key={i}>
                <strong>{(a.field || '').replace(/_/g, ' ')}</strong>: {t('diet.mentions', 'mentions {{food}}', { food: a.food })} — {a.condition}
              </li>
            ))}
          </ul>
        </div>
      )}
      {viruddha.length > 0 && (
        <div className="diet-safety-card viruddha">
          <h3 className="diet-safety-title">
            <TriangleAlert size={13} /> {t('diet.alertViruddhaTitle', 'Viruddha Ahara detected (Charaka Sutrasthana 26)')}
          </h3>
          <ul className="diet-safety-list">
            {viruddha.map((v, i) => (
              <li key={i}><strong>{v.combination}</strong> — {v.reason}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}


// The energy and nutrient cards sit below the meals: on a phone they were about two
// and a half screens, so today's meals started on the third. Their warnings are the
// part a patient must not miss, so this line counts them where the cards used to be
// and jumps to them. Nothing is collapsed.
export function TargetsSummary({ plan, targetId }) {
  const { t } = useTranslation()
  const rx = plan.energy_prescription
  if (!rx?.target_calories) return null
  const rec = plan.energy_reconciliation || {}
  const notes = (rec.residual_notes || []).slice(0, 3).length
    + ((rec.days_below_protein_floor || []).length > 0 ? 1 : 0)
    + (rec.micronutrients?.notices || []).length
  const protein = rx.protein_target_g || rx.protein_floor_g
  return (
    <a className={`diet-targets-summary${notes ? ' has-notes' : ''}`} href={`#${targetId}`}
      onClick={(e) => {
        e.preventDefault()
        document.getElementById(targetId)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }}>
      <Flame size={13} className="diet-vital-icon" />
      <span className="diet-targets-summary-main">
        {t('diet.kcalPerDay', '{{kcal}} kcal / day', { kcal: rx.target_calories })}
        {protein ? ` · ${t('diet.proteinG', '{{g}} g protein', { g: protein })}` : ''}
      </span>
      {notes > 0 && (
        <span className="diet-targets-summary-notes">
          <TriangleAlert size={12} /> {t('diet.targetNotes', '{{count}} notes on what food alone cannot cover', { count: notes })}
        </span>
      )}
      <span className="diet-targets-summary-link">
        {t('diet.dailyTargets', 'Your daily targets')} <ArrowDown size={12} />
      </span>
    </a>
  )
}

export function EnergyPrescriptionCard({ plan }) {
  const { t } = useTranslation()
  const rx = plan.energy_prescription
  if (!rx?.target_calories) return null
  const rec = plan.energy_reconciliation || {}
  const mb = rx.meal_budget || {}
  const adjusted = rec.days_adjusted > 0

  return (
    <div className="diet-energy-card">
      <div className="diet-energy-head">
        <Flame size={13} className="diet-vital-icon" />
        <span className="diet-energy-target">{t('diet.kcalPerDay', '{{kcal}} kcal / day', { kcal: rx.target_calories })}</span>
        {rx.protein_target_g ? (
          <span className="diet-energy-sub">
            {t('diet.proteinG', '{{g}} g protein', { g: rx.protein_target_g })}
            {rx.protein_floor_g && rx.protein_floor_g < rx.protein_target_g
              ? ` ${t('diet.neverUnder', '(never under {{g}} g)', { g: rx.protein_floor_g })}` : ''}
          </span>
        ) : rx.protein_floor_g ? (
          <span className="diet-energy-sub">{t('diet.atLeastProtein', 'at least {{g}} g protein', { g: rx.protein_floor_g })}</span>
        ) : null}
      </div>

      {rx.basis === 'measured' ? (
        <p className="diet-energy-basis">
          {t('diet.basisMeasured', 'From your own measurements: {{bmr}} kcal at rest, {{tdee}} kcal at your stated activity level.', { bmr: rx.bmr, tdee: rx.tdee })}
        </p>
      ) : (
        <p className="diet-energy-basis is-estimated">
          {t('diet.basisEstimated', 'Estimated — add your height and weight in your profile to make this exact.')}
        </p>
      )}

      <div className="diet-energy-split">
        {['breakfast', 'lunch', 'snack', 'dinner'].map(slot => (
          mb[slot] ? (
            <span key={slot} className="diet-energy-slot">
              <b>{t(`diet.slot_${slot}`, SLOT_LABEL[slot])}</b> {mb[slot]}
            </span>
          ) : null
        ))}
      </div>

      {(rx.notes || []).map((note, i) => (
        <p key={i} className="diet-energy-note">{note}</p>
      ))}

      {rec.method === 'computed_from_components' ? (
        <p className="diet-energy-note">
          {t('diet.computedNote', "Every day's figures are calculated from the foods and grams in its meals, using published food-composition data — not estimated.")}
          {adjusted ? ` ${t('diet.resizedComputed', 'Portions on {{count}} days were resized so the day meets your targets; the dishes are unchanged.', { count: rec.days_adjusted })}` : ''}
        </p>
      ) : adjusted ? (
        <p className="diet-energy-note">
          {t('diet.resizedLegacy', 'Portions on {{count}} days were resized to meet this target — the meals and their Ayurvedic reasoning are unchanged.', { count: rec.days_adjusted })}
        </p>
      ) : null}
      {/* Weeks 2-4 are meal names with no macros, so nothing there can be summed or
          corrected. The card showed a target and a clean tick over all four weeks
          regardless — "7 days checked" reads as a finished check unless the other 21
          are named. */}
      {rec.days_unquantified > 0 ? (
        <p className="diet-energy-note">
          {t('diet.unquantified', 'Checked against this target on {{checked}} days. Weeks 2-4 are given as meal names without portion figures, so {{rest}} further days are not measured — keep the week 1 portions as your guide.',
            { checked: rec.days_quantified, rest: rec.days_unquantified })}
        </p>
      ) : null}
      {(rec.residual_notes || []).slice(0, 3).map((note, i) => (
        <p key={`r${i}`} className="diet-energy-note is-warn">{note}</p>
      ))}
      {/* The reconciler checks protein on every non-fasting day and records the ones
          that fall short. A day's own view flags it, but only for the day being
          looked at — so a plan short on protein across several days read as fine
          unless you clicked through all of them. Energy shortfalls were summarised
          here and protein was not, which is the asymmetry rather than the check. */}
      {(rec.days_below_protein_floor || []).length > 0 ? (
        <p className="diet-energy-note is-warn">
          {t('diet.proteinShortDays', 'Protein is below your {{floor}} g floor on {{count}} days', { floor: rx.protein_floor_g, count: rec.days_below_protein_floor.length })}
          {rec.days_below_protein_floor.length <= 3
            ? ` (${rec.days_below_protein_floor.map(d => (typeof d === 'string' ? d : `${d.week} ${d.day}`)).join(', ')})`
            : ''}
          . {t('diet.addProtein', 'Add dal, paneer or curd to the meal that suits your Agni best.')}
        </p>
      ) : null}
    </div>
  )
}

// The figures a dietitian sets beside the energy target, each with its source.
export function NutrientTargetsCard({ plan }) {
  const [open, setOpen] = useState(false)
  const { t } = useTranslation()
  const nt = plan.nutrient_targets
  if (!nt) return null
  // What the 28 days deliver, beside each target. Computed from the components, so a
  // shortfall is stated rather than implied met.
  const micro = plan.energy_reconciliation?.micronutrients || {}
  const delivered = (key, unit) => {
    const m = micro[key]
    if (!m || m.average == null) return ''
    const days = micro.days_counted
    const hit = m.days_met ?? (m.days_over != null ? days - m.days_over : null)
    // B12 and vitamin D are a few micrograms: rounding 1.4 to 1 hides the figure.
    const avg = m.average < 10 ? Math.round(m.average * 10) / 10 : Math.round(m.average)
    return ` — ${t('diet.thisPlan', 'this plan: ~{{avg}} {{unit}} a day', { avg, unit })}${hit != null && days ? `, ${t('diet.onTarget', 'on target {{hit}} of {{days}} days', { hit, days })}` : ''}`
  }
  const atLeast = (v, unit) => t('diet.atLeast', 'at least {{v}} {{unit}}', { v, unit })
  const under = (v, unit) => t('diet.under', 'under {{v}} {{unit}}', { v, unit })
  const mineral = (key, label, unit) => nt[key] && [label, `${atLeast(nt[key].min, unit)}${delivered(key, unit)}`]
  const unmeasured = micro.unmeasured_foods || []
  const rows = [
    nt.carbs_g && [t('diet.carbs', 'Carbohydrate'), `~${nt.carbs_g.target} g (${t('diet.pctEnergy', '{{pct}}% of energy', { pct: nt.carbs_g.pct_energy })})${nt.carbs_g.basis ? ` — ${t('diet.availableCarbs', 'available, after fibre')}` : ''}`],
    nt.fat_g && [t('diet.fat', 'Fat'), `~${nt.fat_g.target} g (${nt.fat_g.pct_energy}%)`],
    nt.sat_fat_g && [t('diet.satFat', 'Saturated fat'), under(nt.sat_fat_g.max, 'g')],
    nt.fibre_g && [t('diet.fibre', 'Fibre'), atLeast(nt.fibre_g.min, 'g')],
    nt.sodium_mg && [t('diet.sodium', 'Sodium'), `${under(nt.sodium_mg.max, 'mg')} (${t('diet.aboutSalt', 'about {{g}} g salt', { g: (nt.sodium_mg.max * 2.54 / 1000).toFixed(1) })})${delivered('sodium_mg', 'mg')}`],
    mineral('potassium_mg', t('diet.potassium', 'Potassium'), 'mg'),
    mineral('iron_mg', t('diet.iron', 'Iron'), 'mg'),
    mineral('calcium_mg', t('diet.calcium', 'Calcium'), 'mg'),
    mineral('folate_ug', t('diet.folate', 'Folate'), 'µg'),
    mineral('zinc_mg', t('diet.zinc', 'Zinc'), 'mg'),
    mineral('b12_ug', t('diet.b12', 'Vitamin B12'), 'µg'),
    mineral('vitd_ug', t('diet.vitd', 'Vitamin D'), 'µg'),
    mineral('iodine_ug', t('diet.iodine', 'Iodine (from iodised salt)'), 'µg'),
    nt.added_sugar_g && [t('diet.addedSugar', 'Added sugar'), nt.added_sugar_g.max === 0 ? t('diet.none', 'none') : under(nt.added_sugar_g.max, 'g')],
    nt.water_ml && [t('diet.water', 'Water'), nt.water_ml.target ? t('diet.aboutLitres', 'about {{l}} L', { l: (nt.water_ml.target / 1000).toFixed(1) }) : t('diet.asDoctorAdvises', 'as your doctor advises')],
  ].filter(Boolean)
  return (
    <div className="diet-targets-card">
      <div className="diet-energy-head">
        <Target size={13} className="diet-vital-icon" />
        <span className="diet-energy-target">{t('diet.dailyTargets', 'Your daily targets')}</span>
      </div>
      <dl className="diet-targets-list">
        {rows.map(([k, v]) => (
          <div key={k} className="diet-targets-row"><dt>{k}</dt><dd>{v}</dd></div>
        ))}
      </dl>
      {(nt.notes || []).map((n, i) => <p key={i} className="diet-energy-note">{n}</p>)}
      {(micro.notices || []).map((n, i) => <p key={`m${i}`} className="diet-energy-note">{n}</p>)}
      {unmeasured.length > 0 && (
        <p className="diet-energy-note">
          {t('diet.unmeasured', 'Minerals and vitamins are not counted for {{foods}} — no reliable composition data — so the figures above may run a little low.',
            { foods: unmeasured.map(f => f.replace(/_/g, ' ')).join(', ') })}
        </p>
      )}
      <button type="button" className="diet-targets-toggle" onClick={() => setOpen(o => !o)} aria-expanded={open}>
        {open ? <ChevronUp size={11} /> : <ChevronDown size={11} />} {t('diet.sources', 'Where these numbers come from')}
      </button>
      {open && (
        <ul className="diet-targets-sources">
          {Object.entries(nt.sources || {}).map(([k, v]) => <li key={k}><b>{k.replace(/_/g, ' ')}:</b> {v}</li>)}
        </ul>
      )}
    </div>
  )
}

// Medicines, fasting and the condition notes — what a dietitian writes beside the
// meals. Each note carries its source.
export function ClinicalNotesCard({ plan }) {
  const { t } = useTranslation()
  const meds = plan.medication_interactions || []
  const notes = plan.clinical_notes || []
  const unchecked = plan.medications_not_checked || []
  if (!meds.length && !notes.length && !plan.fasting_notice && !unchecked.length) return null
  return (
    <div className="diet-clinical-card">
      {plan.fasting_notice && (
        <div className="diet-clinical-item is-warn">
          <Moon size={13} /> <div><strong>{t('diet.fasting', 'Fasting')}</strong><p>{plan.fasting_notice}</p></div>
        </div>
      )}
      {meds.map(m => (
        <div key={m.key} className="diet-clinical-item">
          <AlertTriangle size={13} />
          <div>
            <strong>{m.medication}</strong>
            <p>{m.advice}</p>
            <span className="diet-clinical-source">{m.source}</span>
          </div>
        </div>
      ))}
      {unchecked.length > 0 && (
        <p className="diet-energy-note">
          {t('diet.medsUnchecked', 'Not checked for food interactions: {{meds}}. Ask your pharmacist.', { meds: unchecked.join(', ') })}
        </p>
      )}
      {notes.map(n => (
        <div key={n.topic} className="diet-clinical-item">
          <BookOpen size={13} />
          <div>
            <strong>{n.topic}</strong>
            <p>{n.note}</p>
            <span className="diet-clinical-source">{n.source}</span>
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Where the patient is in the plan ──────────────────────────────────────────
// The plan opened on week 1, Monday, whatever the date, so someone in week 3 had
// to find their place every time. Weeks are counted in sevens from the day the plan
// was written; a day is the weekday it names.
