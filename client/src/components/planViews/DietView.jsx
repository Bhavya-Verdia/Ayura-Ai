import React, { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { mealsAPI, plansAPI } from '../../api/client'
import {
  Sun, Leaf, Coffee, AlertTriangle, Star, Droplets, ShieldCheck, Flame, Moon, Timer, Target, ChevronDown, ChevronUp, Flower2, UtensilsCrossed, Clock, Soup, Apple, CupSoda, BookOpen, TriangleAlert, Languages,
} from 'lucide-react'
import { DOSHA_COLOR, doshaInk } from '../../constants/dosha'
import { RemedyView } from './RemedyView'

const DIET_MEAL_ICONS = {
  breakfast: Coffee,
  lunch:     Soup,
  snack:     Apple,
  dinner:    UtensilsCrossed,
}

const DIET_DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
// Display names, translated; the English names above are the plan's own keys.
const SLOT_LABEL = { breakfast: 'Breakfast', lunch: 'Lunch', snack: 'Snack', dinner: 'Dinner', special_drink: 'Daily drink' }

const DIET_DAY_FULL   = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


function MacroBar({ macros }) {
  const { t } = useTranslation()
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
      {macros?.fiber_g > 0 && <div className="diet-macro-chip fib"><span>{t('diet.fibreShort', 'Fib')}</span>{macros.fiber_g}g</div>}
    </div>
  )
}

// ── LLM Meal Card (primary — for weekly_plan structure) ───────────────────────

// ── Meal log ──────────────────────────────────────────────────────────────────
// Eaten / partly / skipped / swapped, per meal. The next plan reads it: a slot that is
// usually skipped is kept light, foods left uneaten are used rarely, and with
// weigh-ins the energy target moves (server/services/diet_log.py).
const LOG_STATUSES = [
  { key: 'eaten', label: 'Ate it', i18n: 'diet.logEaten' },
  { key: 'partly', label: 'Some', i18n: 'diet.logPartly' },
  { key: 'skipped', label: 'Skipped', i18n: 'diet.logSkipped' },
  { key: 'swapped', label: 'Ate something else', i18n: 'diet.logSwapped' },
]

function MealLogBar({ log, onLog }) {
  const { t } = useTranslation()
  const [swapping, setSwapping] = useState(false)
  const [text, setText] = useState(log?.swapped_with || '')
  const status = log?.status
  const choose = (key) => {
    if (key === 'swapped') { setSwapping(true); return }
    setSwapping(false)
    onLog(status === key ? null : key)
  }
  return (
    <div className="diet-log-bar" role="group" aria-label={t('diet.logThisMeal', 'Log this meal')}>
      {LOG_STATUSES.map(s => (
        <button key={s.key} type="button" aria-pressed={status === s.key}
          className={`diet-log-btn${status === s.key ? ' is-on' : ''}`} onClick={() => choose(s.key)}>
          {t(s.i18n, s.label)}
        </button>
      ))}
      {swapping && (
        <form className="diet-log-swap" onSubmit={e => { e.preventDefault(); setSwapping(false); onLog('swapped', text) }}>
          <input value={text} onChange={e => setText(e.target.value)} maxLength={120}
            placeholder={t('diet.swapPlaceholder', 'What did you have instead? (optional)')}
            aria-label={t('diet.swapLabel', 'What you ate instead')} />
          <button type="submit" className="diet-log-btn">{t('diet.save', 'Save')}</button>
        </form>
      )}
      {status === 'swapped' && log?.swapped_with && !swapping && (
        <span className="diet-log-note">{t('diet.had', 'Had: {{food}}', { food: log.swapped_with })}</span>
      )}
    </div>
  )
}

function MealLogSummary({ planId, logs }) {
  const { t } = useTranslation()
  const [adapt, setAdapt] = useState(null)
  const count = Object.keys(logs).length
  useEffect(() => {
    if (!planId) return
    let live = true
    mealsAPI.getAdaptation().then(r => { if (live) setAdapt(r.data) }).catch(() => {})
    return () => { live = false }
  }, [planId, count])
  if (!count) {
    return (
      <p className="diet-energy-note">
        {t('diet.logIntro', 'Log each meal below — ate it, some, skipped, or something else. Your next plan is built from what you actually ate.')}
      </p>
    )
  }
  const a = adapt?.adaptation || {}
  const s = adapt?.summary || {}
  const changes = [
    ...(a.skipped_slots || []).map(slot => t('diet.changeSlot', '{{slot}} kept quick and light — you usually skip it',
      { slot: t(`diet.slot_${slot}`, SLOT_LABEL[slot] || slot.replace(/_/g, ' ')) })),
    a.avoided_foods?.length ? t('diet.changeFoods', '{{foods}} used rarely — often left uneaten',
      { foods: a.avoided_foods.map(f => f.replace(/_/g, ' ')).join(', ') }) : null,
    a.energy_adjust_kcal ? t('diet.changeEnergy', 'energy {{kcal}} kcal — {{reason}}',
      { kcal: `${a.energy_adjust_kcal > 0 ? '+' : ''}${a.energy_adjust_kcal}`, reason: a.energy_reason }) : null,
  ].filter(Boolean)
  return (
    <div className="diet-log-summary">
      <span>
        {t('diet.mealsLogged', '{{count}} meals logged', { count: s.meals_logged || count })}
        {s.adherence != null ? ` · ${t('diet.eatenAsPlanned', '{{pct}}% eaten as planned', { pct: Math.round(s.adherence * 100) })}` : ''}.
      </span>
      {changes.length > 0 ? (
        <ul>{changes.map(c => <li key={c}>{t('diet.nextPlan', 'Next plan: {{change}}.', { change: c })}</li>)}</ul>
      ) : (
        <span> {t('diet.nextPlanWaits', 'Your next plan changes once there are 14 logged meals and enough of a pattern to act on.')}</span>
      )}
    </div>
  )
}

function LLMMealCard({ mealName, meal, log, onLog }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const MealIcon = DIET_MEAL_ICONS[mealName] || UtensilsCrossed
  const label = t(`diet.slot_${mealName}`, SLOT_LABEL[mealName] || mealName)
  if (!meal?.meal_name) return null
  return (
    <div className={`diet-meal-card llm meal-${mealName}${meal.allergen_warning ? ' has-allergen' : ''}`}>
      {meal.allergen_warning && (
        <div className="diet-allergen-warning">
          {t('diet.allergenDetected', 'Allergen detected: {{terms}}', { terms: meal.allergen_terms?.join(', ') })}
        </div>
      )}
      {meal.dietary_type_warnings?.length > 0 && (
        <div className="diet-allergen-warning">
          {t('diet.dietTypeMismatch', 'Does not match your dietary type: {{foods}}', { foods: meal.dietary_type_warnings.join(', ') })}
        </div>
      )}
      <h3 className="diet-meal-heading">
        <button
          type="button"
          className="diet-meal-header"
          onClick={() => setOpen(o => !o)}
          aria-expanded={open}
        >
          <div className="diet-meal-title-row">
            <MealIcon size={13} className="diet-meal-icon" />
            <div className="diet-meal-title-stack">
              <span className="diet-meal-label">{label}</span>
              <span className="diet-meal-name-llm">{meal.meal_name}</span>
            </div>
          </div>
          <div className="diet-meal-meta">
            {meal.macros_approx?.calories > 0 && (
              <span className="diet-meal-cal-badge">{t('diet.cal', '{{n}} cal', { n: Math.round(meal.macros_approx.calories) })}</span>
            )}
            {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </div>
        </button>
      </h3>
      {onLog && <MealLogBar log={log} onLog={onLog} />}

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
          {meal.substituted && (
            <p className="diet-llm-note-plain">
              {t('diet.substituted', 'The meal first written here broke one of your rules, so it was replaced with this plain plate from your allowed foods.')}
            </p>
          )}
          {meal.nutrition_basis === 'partial' && (
            <p className="diet-llm-note-plain">
              {t('diet.partialNutrition', "Some of this meal's ingredients have no nutrition data, so its figures are lower than the real meal.")}
            </p>
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

function DietSafetyBanner({ plan }) {
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


function EnergyPrescriptionCard({ plan }) {
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
function NutrientTargetsCard({ plan }) {
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
function ClinicalNotesCard({ plan }) {
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

// Languages the plan can be READ in. The plan is generated and safety-checked in
// English; a translation is an overlay of its display text (services/diet_translate.py)
// and never what the checks read, because they cannot read other scripts.
const PLAN_LANGUAGES = { hi: 'हिंदी', kn: 'ಕನ್ನಡ', ta: 'தமிழ்', sa: 'संस्कृतम्', es: 'Español', fr: 'Français', zh: '中文' }

function withOverlay(plan, strings) {
  if (!strings) return plan
  const out = structuredClone(plan)
  for (const [path, text] of Object.entries(strings)) {
    const keys = path.split('.')
    let node = out
    for (const k of keys.slice(0, -1)) {
      node = node?.[/^\d+$/.test(k) && Array.isArray(node) ? Number(k) : k]
      if (node == null) break
    }
    const last = keys[keys.length - 1]
    if (node != null && typeof node === 'object') node[Array.isArray(node) ? Number(last) : last] = text
  }
  return out
}

export function DietView({ plan: englishPlan }) {
  const { t, i18n } = useTranslation()
  const lang = (i18n.language || 'en').slice(0, 2)
  const translatable = lang in PLAN_LANGUAGES && !!englishPlan.plan_id
  const [showTranslated, setShowTranslated] = useState(false)
  const [overlay, setOverlay] = useState(null)
  const [translating, setTranslating] = useState(false)
  const [translateError, setTranslateError] = useState(false)
  const translated = showTranslated && overlay?.lang === lang
  const plan = useMemo(
    () => (translated ? withOverlay(englishPlan, overlay.strings) : englishPlan),
    [translated, englishPlan, overlay],
  )
  const requestTranslation = async () => {
    if (overlay?.lang === lang) { setShowTranslated(true); return }
    setTranslating(true)
    setTranslateError(false)
    try {
      const { data } = await plansAPI.translateDiet(englishPlan.plan_id, lang)
      setOverlay(data)
      setShowTranslated(true)
    } catch {
      setTranslateError(true)
    } finally {
      setTranslating(false)
    }
  }
  const [activeDay, setActiveDay] = useState(0)
  const [activeWeek, setActiveWeek] = useState(0)
  // Logs are keyed to the English plan's id: a translation is the same plan.
  const planId = englishPlan.plan_id
  const [logs, setLogs] = useState({})
  useEffect(() => {
    if (!planId) return
    let live = true
    mealsAPI.getLogs(planId).then(r => {
      if (!live) return
      const map = {}
      for (const l of r.data.logs || []) map[`${l.week}:${l.day}:${l.slot}`] = l
      setLogs(map)
    }).catch(() => {})
    return () => { live = false }
  }, [planId])
  const logMeal = (week, day, slot) => async (status, swappedWith) => {
    const k = `${week}:${day}:${slot}`
    const prev = logs[k]
    setLogs(m => {
      const next = { ...m }
      if (status) next[k] = { week, day, slot, status, swapped_with: swappedWith }
      else delete next[k]
      return next
    })
    try {
      await mealsAPI.log({ plan_id: planId, week, day, slot, status, swapped_with: swappedWith || null })
    } catch {
      setLogs(m => { const next = { ...m }; if (prev) next[k] = prev; else delete next[k]; return next })
    }
  }
  const [timingOpen, setTimingOpen] = useState(false)
  const [spiceOpen, setSpiceOpen] = useState(false)

  const us = plan.user_summary || {}
  const isLLM = !!plan.weekly_plan
  const doshaColor = DOSHA_COLOR[us.dominant_dosha] || DOSHA_COLOR.default
  const doshaText = doshaInk(us.dominant_dosha)
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
  // Every week of a current plan is full detail. Plans generated before that carry
  // meal NAMES in weeks 2-4, and keep their compact rows.
  const fullDetail = typeof dayData.lunch === 'object' || typeof dayData.breakfast === 'object'
  const weekNumber = currentWeek?.week_number || activeWeek + 1
  // Only plans whose meals are stated as components can be logged: the log records
  // which foods were eaten or left, and an older plan's meals name none.
  const canLog = !!planId && fullDetail && !!dayData.lunch?.components

  // Fallback path: four_week_plan array
  const fallbackDays = (plan.four_week_plan?.[0]?.days) || []
  const fallbackDay = fallbackDays[activeDay] || {}
  const timing = plan.meal_timing || {}

  return (
    <div className="diet-view">
      {translatable && (
        <div className="diet-translate-bar">
          <Languages size={13} />
          {translated ? (
            <>
              <span>
                {t('diet.translatedNote', 'Translated into {{lang}} from your English plan. The food-safety checks were run on the English version.', { lang: PLAN_LANGUAGES[lang] })}
                {overlay.kept_english > 0 ? ` ${t('diet.keptEnglish', '{{count}} lines that could not be verified are left in English.', { count: overlay.kept_english })}` : ''}
              </span>
              <button type="button" className="diet-translate-btn" onClick={() => setShowTranslated(false)}>{t('diet.showEnglish', 'Show English')}</button>
            </>
          ) : (
            <>
              <span>{translateError ? t('diet.translateFailed', 'Translation failed — the English plan is shown.') : t('diet.planInEnglish', 'This plan is in English.')}</span>
              <button type="button" className="diet-translate-btn" onClick={requestTranslation} disabled={translating}>
                {translating ? t('diet.translating', 'Translating…') : t('diet.readIn', 'Read in {{lang}}', { lang: PLAN_LANGUAGES[lang] })}
              </button>
            </>
          )}
        </div>
      )}

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

      {/* ── Energy prescription ── the target the plan was built against, and how
           it was arrived at. Day totals were previously shown with nothing to read
           them against. */}
      <EnergyPrescriptionCard plan={plan} />
      <NutrientTargetsCard plan={plan} />
      <ClinicalNotesCard plan={plan} />

      {/* ── Vitals bar ── */}
      <div className="diet-vitals">
        {goalLabel && (
          <div className="diet-vital-chip">
            <Target size={11} className="diet-vital-icon" />
            <span className="diet-vital-k">{t('diet.goal', 'Goal')}</span>
            <span className="diet-vital-v">{goalLabel}</span>
          </div>
        )}
        {us.dominant_dosha && (
          <div className="diet-vital-chip" style={{ borderColor: `${doshaColor}44`, color: doshaText }}>
            <span className="diet-vital-k">{t('diet.dosha', 'Dosha')}</span>
            <span className="diet-vital-v">{us.dominant_dosha.toUpperCase()}</span>
          </div>
        )}
        {us.agni_type && (
          <div className="diet-vital-chip">
            <Flame size={11} className="diet-vital-icon" />
            <span className="diet-vital-k">{t('diet.agni', 'Agni')}</span>
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
            <span className="diet-vital-k">{t('diet.gut', 'Gut')}</span>
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

      {/* ── Deterministic Ahara safety (Viruddha + allergens, all weeks) ── */}
      <DietSafetyBanner plan={plan} />

      {/* ── Pathya-Apathya (LLM only) ── */}
      {isLLM && <PathyaApathyaCard pa={plan.pathya_apathya} />}

      {/* ── Condition coaching ── */}
      {plan.condition_coaching && (
        <div className="diet-coaching-card">
          <ShieldCheck size={13} className="diet-coaching-icon" />
          <p className="diet-coaching-text">{plan.condition_coaching}</p>
        </div>
      )}

      {/* ── Therapeutic arc ── which progression this patient was given, and why.
           The sequence used to be the same four phases for everyone. */}
      {plan.therapeutic_arc?.arc && (
        <div className="diet-arc-card">
          <div className="diet-arc-head">
            <Flower2 size={13} className="diet-vital-icon" />
            <span className="diet-arc-name">{plan.therapeutic_arc.arc}</span>
          </div>
          <p className="diet-arc-basis">{plan.therapeutic_arc.basis}</p>
          {(plan.therapeutic_arc.withheld || []).map((note, i) => (
            <p key={i} className="diet-arc-withheld">{note}</p>
          ))}
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
              <span className="diet-week-num">{t('diet.week', 'Week {{n}}', { n: wk.week_number })}</span>
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
              {t(`diet.day_${label}`, label)}
              {isFasting && <span className="diet-fast-dot" />}
            </button>
          )
        })}
      </div>

      {/* ── Selected-day heading ── */}
      <h3 className="diet-day-heading">
        {t(`diet.dayFull_${DIET_DAY_FULL[activeDay]}`, DIET_DAY_FULL[activeDay])}{isMultiWeek ? ` · ${t('diet.week', 'Week {{n}}', { n: activeWeek + 1 })}` : ''}
      </h3>

      {/* ── Day theme badge (LLM) ── */}
      {isLLM && dayData.theme && (
        <div className="diet-day-theme-badge">{dayData.theme}</div>
      )}

      {/* ── LLM Meal cards ── */}
      {isLLM && (!isMultiWeek || activeWeek === 0 || fullDetail) && (
        <>
          {dayData.is_fasting && (
            <div className="diet-fasting-banner">
              <Moon size={16} />
              <div>
                <strong>{t('diet.fastingDay', 'Fasting Day')}</strong>
                <p>
                  {t('diet.phalahar', 'Phalahar — fruit, milk or plant milk, nuts and herbal drinks, kept light on purpose')}
                  {plan.energy_reconciliation?.fasting_day_target_kcal
                    ? ` ${t('diet.aboutKcal', '(about {{kcal}} kcal)', { kcal: plan.energy_reconciliation.fasting_day_target_kcal })}` : ''}
                  . {t('diet.restAgni', 'Rest the digestive fire.')}
                </p>
              </div>
            </div>
          )}
          {canLog && <MealLogSummary planId={planId} logs={logs} />}
          <div className="diet-meals-section">
            {['breakfast', 'lunch', 'snack', 'dinner'].map(meal => (
              dayData[meal] && (
                <LLMMealCard key={meal} mealName={meal} meal={dayData[meal]}
                  log={logs[`${weekNumber}:${currentDayName}:${meal}`]}
                  onLog={canLog ? logMeal(weekNumber, currentDayName, meal) : null} />
              )
            ))}
          </div>
          {/* Day total macros computed from per-meal macros_approx */}
          {(() => {
            const meals = ['breakfast', 'lunch', 'snack', 'dinner']
            const total = dayData.day_totals || meals.reduce((acc, m) => {
              const ma = dayData[m]?.macros_approx || {}
              return {
                calories: acc.calories + (ma.calories || 0),
                protein_g: acc.protein_g + (ma.protein_g || 0),
                carbs_g: acc.carbs_g + (ma.carbs_g || 0),
                fat_g: acc.fat_g + (ma.fat_g || 0),
              }
            }, { calories: 0, protein_g: 0, carbs_g: 0, fat_g: 0 })
            if (!(total.calories > 0)) return null
            // The day total used to be shown alone, so a day delivering 600 kcal
            // against a 1490 kcal prescription read as a fact rather than a miss.
            const rx = plan.energy_prescription
            const target = rx?.target_calories
            const band = rx?.band
            const offBand = band && (total.calories < band[0] || total.calories > band[1])
            const lowProtein = rx?.protein_floor_g && total.protein_g < rx.protein_floor_g * 0.9
            return (
              <div className="diet-day-macros">
                <span className="diet-day-macros-label">
                  {dayData.day_totals ? t('diet.dayTotalsCalc', 'Day totals (calculated, incl. drink)') : t('diet.dayTotalsApprox', 'Day totals (approx.)')}
                  {target ? (
                    <span className={`diet-day-target${offBand ? ' is-off' : ''}`}>
                      {t('diet.targetKcal', 'target {{kcal}} kcal', { kcal: target })}
                    </span>
                  ) : null}
                </span>
                <MacroBar macros={total} />
                {lowProtein ? (
                  <p className="diet-day-flag">
                    {t('diet.proteinShortToday', 'Protein is below your {{floor}} g daily floor on this day — add dal, paneer or curd to the meal that suits your Agni best.', { floor: rx.protein_floor_g })}
                  </p>
                ) : null}
              </div>
            )
          })()}
        </>
      )}

      {/* ── Compact meals (weeks 2-4) ── */}
      {isMultiWeek && activeWeek > 0 && !fullDetail && (
        <div className="diet-compact-meals">
          {['breakfast', 'lunch', 'snack', 'dinner'].map(meal => {
            const val = dayData[meal]
            if (!val) return null
            const MealIcon = DIET_MEAL_ICONS[meal] || UtensilsCrossed
            const label = t(`diet.slot_${meal}`, SLOT_LABEL[meal])
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
              <span className="diet-compact-meal-label">{t('diet.drink', 'Drink')}</span>
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
                <strong>{t('diet.fastingDay', 'Fasting Day')}</strong>
                <p>{t('diet.fastingLegacy', 'Light fruits, dairy, nuts, and herbal beverages only. Rest the digestive fire.')}</p>
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
                  {/* Static card — nothing to disclose, so a plain heading. */}
                  <h3 className="diet-meal-header">
                    <div className="diet-meal-title-row">
                      <MealIcon size={13} className="diet-meal-icon" />
                      <span className="diet-meal-label">{t(`diet.slot_${meal}`, SLOT_LABEL[meal])}</span>
                    </div>
                  </h3>
                  <div className="diet-meal-foods">
                    {items.map((item, i) => (
                      <div key={i} className="diet-food-row">
                        <span className="diet-food-name">{item.name}</span>
                        <span className="diet-food-portion">{item.portion}</span>
                        {item.macros?.calories > 0 && (
                          <span className="diet-food-cal">{t('diet.cal', '{{n}} cal', { n: Math.round(item.macros.calories) })}</span>
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
              <span className="diet-day-macros-label">{t('diet.dayTotalsApprox', 'Day totals (approx.)')}</span>
              <MacroBar macros={fallbackDay.daily_macros} />
            </div>
          )}
        </>
      )}

      {/* ── Special Ayurvedic drink (LLM, week 1 full detail only) ── */}
      {isLLM && dayData.special_drink && typeof dayData.special_drink === 'object' && (!isMultiWeek || activeWeek === 0 || fullDetail) && (
        <div className={`diet-drink-card${dayData.special_drink.allergen_warning || dayData.special_drink.requires_substitution ? ' has-allergen' : ''}`}>
          {/* The drink is consumed like any meal and is scanned like one. Its
              warnings were invisible here while the scans could not see it. */}
          {dayData.special_drink.allergen_warning && (
            <div className="diet-allergen-warning">
              {t('diet.allergenDetected', 'Allergen detected: {{terms}}', { terms: dayData.special_drink.allergen_terms?.join(', ') })}
            </div>
          )}
          {dayData.special_drink.condition_warnings?.length > 0 && (
            <div className="diet-allergen-warning">
              {t('diet.notAdvised', 'Not advised for your conditions: {{foods}}', { foods: dayData.special_drink.condition_warnings.map(w => w.food).join(', ') })}
            </div>
          )}
          {dayData.special_drink.dietary_type_warnings?.length > 0 && (
            <div className="diet-allergen-warning">
              {t('diet.notDietType', 'not {{type}}', { type: us.dietary_type?.replace(/_/g, ' ') })}: {dayData.special_drink.dietary_type_warnings.join(', ')}
            </div>
          )}
          <div className="diet-drink-header">
            <CupSoda size={13} className="diet-drink-icon" />
            <span className="diet-drink-name">{dayData.special_drink.name}</span>
            <span className="diet-drink-when">{dayData.special_drink.when}</span>
          </div>
          {dayData.special_drink.recipe && (
            <p className="diet-drink-recipe">{dayData.special_drink.recipe}</p>
          )}
          {dayData.special_drink.portion && (
            <div className="diet-llm-portion">
              <UtensilsCrossed size={11} /> {dayData.special_drink.portion}
              {dayData.special_drink.macros_approx?.calories > 0
                ? ` · ${Math.round(dayData.special_drink.macros_approx.calories)} kcal` : ''}
            </div>
          )}
          {dayData.special_drink.rationale && (
            <p className="diet-drink-rationale">{dayData.special_drink.rationale}</p>
          )}
        </div>
      )}

      {/* ── Ahar Vidhi (LLM) ── */}
      {isLLM && plan.ahar_vidhi && (
        <div className="diet-ahar-vidhi">
          <h3 className="diet-ahar-vidhi-title">
            <BookOpen size={13} /> {t('diet.aharVidhi', 'Ahar Vidhi — Rules of Eating')}
          </h3>
          <p>{plan.ahar_vidhi}</p>
        </div>
      )}

      {/* ── Meal timing (Dinacharya) — fallback / both ── */}
      {Object.keys(timing).length > 0 && (
        <div className="diet-timing-card">
          <button className="diet-timing-toggle" onClick={() => setTimingOpen(o => !o)}>
            <Clock size={13} className="diet-timing-icon" />
            <span>{t('diet.mealTiming', 'Meal Timing — Dinacharya')}</span>
            {timingOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>
          {timingOpen && (
            <div className="diet-timing-body">
              {timing.general_note && <p className="diet-timing-note">{timing.general_note}</p>}
              <div className="diet-timing-rows">
                {['breakfast', 'lunch', 'snack', 'dinner'].map(m => timing[m] && (
                  <div key={m} className="diet-timing-row">
                    <span className="diet-timing-meal">{t(`diet.slot_${m}`, SLOT_LABEL[m])}</span>
                    <span className="diet-timing-time">{timing[m]}</span>
                  </div>
                ))}
                {timing.wake_up_drink && (
                  <div className="diet-timing-row special">
                    <CupSoda size={11} />
                    <span className="diet-timing-meal">{t('diet.wakeDrink', 'Wake-up drink')}</span>
                    <span className="diet-timing-time">{timing.wake_up_drink}</span>
                  </div>
                )}
                {timing.bedtime_drink && (
                  <div className="diet-timing-row special">
                    <Moon size={11} />
                    <span className="diet-timing-meal">{t('diet.bedtimeDrink', 'Bedtime drink')}</span>
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
            <span>{t('diet.spiceGuide', 'Dosha Spice Guide')}</span>
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
                <h3 className="diet-guidance-title">{t('diet.hydration', 'Hydration')}</h3>
                <p className="diet-guidance-text">{plan.hydration_guidance}</p>
              </div>
            </div>
          )}
          {plan.fasting_guidance && (
            <div className="diet-guidance-card">
              <Moon size={13} className="diet-guidance-icon fasting" />
              <div>
                <h3 className="diet-guidance-title">{t('diet.fastingProtocol', 'Fasting Protocol')}</h3>
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
            t('diet.disclaimer', 'AI-generated wellness guidance. Consult a qualified Ayurvedic practitioner before starting a therapeutic diet, especially with existing medical conditions.')}
        </span>
      </div>

    </div>
  )
}

// ── RemedyView ────────────────────────────────────────────────────────────────
