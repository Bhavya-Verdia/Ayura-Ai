import React, { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { mealsAPI, plansAPI } from '../../api/client'
import {
  Sun, Leaf, Coffee, AlertTriangle, Star, Droplets, ShieldCheck, Flame, Moon, Timer, Target, ChevronDown, ChevronUp, Flower2, UtensilsCrossed, Clock, Soup, Apple, CupSoda, BookOpen, TriangleAlert, Languages,
  Shuffle, Undo2, Award, RefreshCw, ClipboardCheck, ShieldAlert, Check, CalendarCheck, X,
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

// Another dish from this plan in place of one meal — no regeneration, nothing billed
// (server/services/diet_meal_swap.py). The meal first written is kept and can be put back.
function MealReplaceBar({ meal, onReplace, onRestore }) {
  const { t } = useTranslation()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const run = async (fn) => {
    setBusy(true)
    setError(null)
    try {
      await fn()
    } catch (e) {
      setError(e?.response?.status === 409
        ? t('diet.noOtherDish', 'No other dish in your plan suits this meal.')
        : t('diet.replaceFailed', 'Could not change this meal — try again.'))
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="diet-replace-bar">
      <button type="button" className="diet-log-btn" disabled={busy} onClick={() => run(onReplace)}>
        <Shuffle size={11} /> {t('diet.anotherDish', 'Another dish')}
      </button>
      {meal.replaced_from && (
        <button type="button" className="diet-log-btn" disabled={busy} onClick={() => run(onRestore)}>
          <Undo2 size={11} /> {t('diet.putBack', 'Back to {{meal}}', { meal: meal.replaced_from.meal_name })}
        </button>
      )}
      {error && <span className="diet-log-note" role="status">{error}</span>}
    </div>
  )
}

function LLMMealCard({ mealName, meal, log, onLog, onReplace, onRestore }) {
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
      {onReplace && <MealReplaceBar meal={meal} onReplace={onReplace} onRestore={onRestore} />}

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

// ── Where the patient is in the plan ──────────────────────────────────────────
// The plan opened on week 1, Monday, whatever the date, so someone in week 3 had
// to find their place every time. Weeks are counted in sevens from the day the plan
// was written; a day is the weekday it names.
const PLAN_DAYS = 28
const DAY_MS = 864e5

function planToday(plan) {
  const start = Date.parse(plan?.generated_at || '')
  if (!Number.isFinite(start)) return null
  const first = new Date(start)
  first.setHours(0, 0, 0, 0)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const days = Math.round((today - first) / DAY_MS)
  if (days < 0) return null
  return { days, week: Math.min(4, Math.floor(days / 7) + 1), dayIndex: (today.getDay() + 6) % 7,
    over: days >= PLAN_DAYS }
}

// ── The end of the four weeks ─────────────────────────────────────────────────
// Week four was the last page and nothing came after it: the plan sat in week six,
// and the meal log meant to shape the next plan shaped nothing until the patient
// thought to regenerate. The server sends one notification too (diet_log.py).
function DietPlanComplete({ planId, onRegenerate }) {
  const { t } = useTranslation()
  const [adapt, setAdapt] = useState(null)
  useEffect(() => {
    if (!planId) return
    let live = true
    mealsAPI.getAdaptation().then(r => { if (live) setAdapt(r.data) }).catch(() => {})
    return () => { live = false }
  }, [planId])
  const s = adapt?.summary || {}
  return (
    <div className="gym-block-card over diet-plan-complete">
      <span className="gym-checkin-title"><Award size={16} /> {t('diet.planDone', 'Your four weeks are done')}</span>
      <p className="gym-block-line">
        {s.meals_logged
          ? t('diet.planDoneLogged', 'You logged {{meals}} meals, {{pct}}% eaten as planned. Your next four weeks will be built from them and from your weekly check-ins.',
            { meals: s.meals_logged, pct: Math.round((s.adherence || 0) * 100) })
          : t('diet.planDoneNoLog', 'Log meals as you go in the next four weeks, and the plan after that is built from what you actually ate.')}
      </p>
      {onRegenerate && (
        <button type="button" className="gym-log-save gym-checkin-rebuild" onClick={onRegenerate}>
          <RefreshCw size={12} /> {t('diet.buildNext', 'Build my next four weeks')}
        </button>
      )}
    </div>
  )
}

// ── Weekly check-in ───────────────────────────────────────────────────────────
// What a dietitian asks at each review and the meal log cannot know: hunger, how
// digestion went, which food disagreed, and the signs no menu answers. It proposes;
// the weeks still to come are rebuilt only when the patient asks
// (server/services/diet_checkin.py).
const HUNGER = [
  { value: 'hungry', label: 'Hungry between meals', i18n: 'diet.hungerHungry' },
  { value: 'right', label: 'About right', i18n: 'diet.hungerRight' },
  { value: 'too_much', label: 'More than I could eat', i18n: 'diet.hungerTooMuch' },
]
const DIGESTION = [
  { value: 'bloating', label: 'Bloating or gas', i18n: 'diet.digBloating' },
  { value: 'acidity', label: 'Acidity or heartburn', i18n: 'diet.digAcidity' },
  { value: 'constipation', label: 'Constipation', i18n: 'diet.digConstipation' },
  { value: 'loose_stools', label: 'Loose stools', i18n: 'diet.digLoose' },
]
const PROBLEMS = [
  { value: 'bloating', label: 'Bloating', i18n: 'diet.probBloating' },
  { value: 'acidity', label: 'Acidity', i18n: 'diet.probAcidity' },
  { value: 'loose_stools', label: 'Loose stools', i18n: 'diet.probLoose' },
  { value: 'nausea', label: 'Nausea', i18n: 'diet.probNausea' },
  { value: 'itching_rash', label: 'Itching or a rash', i18n: 'diet.probRash' },
  { value: 'did_not_like', label: 'Did not like it', i18n: 'diet.probDislike' },
]
// None of these is answered by a different menu.
const DIET_RED_FLAGS = [
  { value: 'swelling', label: 'Swelling of the lips, face or tongue', i18n: 'diet.flagSwelling' },
  { value: 'breathing', label: 'Wheezing or a tight throat', i18n: 'diet.flagBreathing' },
  { value: 'hives', label: 'Hives over much of the body', i18n: 'diet.flagHives' },
  { value: 'vomiting', label: 'Vomiting again and again', i18n: 'diet.flagVomiting' },
  { value: 'blood_in_stool', label: 'Blood in the stool, or black stool', i18n: 'diet.flagBlood' },
]
const ALLERGY_LABELS = [
  { value: 'dairy', label: 'Dairy', i18n: 'diet.allergyDairy' },
  { value: 'gluten', label: 'Gluten', i18n: 'diet.allergyGluten' },
  { value: 'nuts_tree', label: 'Tree nuts', i18n: 'diet.allergyTreeNuts' },
  { value: 'peanuts', label: 'Peanuts', i18n: 'diet.allergyPeanuts' },
  { value: 'soy', label: 'Soy', i18n: 'diet.allergySoy' },
  { value: 'sesame', label: 'Sesame', i18n: 'diet.allergySesame' },
]
const MAX_TROUBLE = 8
const toggle = (list, v) => (list.includes(v) ? list.filter(x => x !== v) : [...list, v])

function CheckinChanges({ proposal }) {
  const { t } = useTranslation()
  const lines = (proposal?.changes || []).map(c => {
    if (c.kind === 'exclude') return t('diet.ciExclude', '{{foods}} left out', { foods: c.foods.join(', ') })
    if (c.kind === 'digestion') {
      const d = DIGESTION.find(x => x.value === c.condition)
      return t('diet.ciDigestion', 'every meal built for {{condition}}', { condition: d ? t(d.i18n, d.label).toLowerCase() : c.condition })
    }
    if (c.kind === 'light_meals') return t('diet.ciLight', 'light, warm, well-cooked meals')
    if (c.kind === 'energy') return t('diet.ciEnergy', 'energy {{kcal}} kcal a day', { kcal: `${c.kcal > 0 ? '+' : ''}${c.kcal}` })
    return null
  }).filter(Boolean)
  if (!lines.length) return null
  return <ul className="diet-checkin-changes">{lines.map(l => <li key={l}>{l}</li>)}</ul>
}

function DietWeekCheckin({ planId, week, data, onSaved, onRebuilt }) {
  const { t } = useTranslation()
  const saved = (data?.checkins || []).find(c => c.week === week)
  const foods = data?.week_foods?.[week] || data?.week_foods?.[String(week)] || []
  const latest = (data?.checkins || []).reduce((a, c) => (!a || c.week > a.week ? c : a), null)
  const proposal = latest?.week === week ? data?.proposal : null
  const [open, setOpen] = useState(false)
  const [hunger, setHunger] = useState('right')
  const [digestion, setDigestion] = useState([])
  const [trouble, setTrouble] = useState([])
  const [flags, setFlags] = useState([])
  const [addAllergies, setAddAllergies] = useState([])
  const [state, setState] = useState('idle')

  if (!planId) return null

  const openForm = () => {
    setHunger(saved?.hunger || 'right')
    setDigestion(saved?.digestion || [])
    setTrouble(saved?.trouble_foods || [])
    setFlags(saved?.red_flags || [])
    setAddAllergies([])
    setState('idle')
    setOpen(true)
  }
  const nameOf = (id) => foods.find(f => f.id === id)?.name || id.replace(/_/g, ' ')
  // A reaction can go onto the allergy list — only when the patient ticks it, and
  // only as an allergy that would actually remove the food.
  const reacted = trouble.filter(x => x.problem === 'itching_rash' || flags.length > 0)
  const offerAllergies = [...new Set(reacted.flatMap(x => foods.find(f => f.id === x.food)?.allergies || []))]
  const save = async () => {
    setState('saving')
    try {
      await mealsAPI.checkin({ plan_id: planId, week, hunger, digestion, trouble_foods: trouble,
        red_flags: flags, add_allergies: addAllergies.filter(a => offerAllergies.includes(a)) })
      await onSaved?.()
      setState('idle')
      setOpen(false)
    } catch {
      setState('error')
    }
  }
  const rebuild = async () => {
    setState('rebuilding')
    try {
      const { data: plan } = await plansAPI.rebuildDiet(planId)
      onRebuilt?.(plan)
      setState('idle')
    } catch {
      setState('rebuildError')
    }
  }

  if (!open) {
    return (
      <div className="gym-checkin gym-checkin-closed diet-checkin">
        <span className="gym-checkin-title">
          <ClipboardCheck size={15} /> {saved
            ? t('diet.ciDone', 'Week {{n}} checked in', { n: week })
            : t('diet.ciAsk', 'How was week {{n}}?', { n: week })}
        </span>
        <span className="gym-checkin-sub">
          {saved
            ? (week < 4
              ? t('diet.ciSubDone', 'What you said shapes the weeks still to come.')
              : t('diet.ciSubDoneLast', 'What you said shapes your next plan.'))
            : t('diet.ciSub', 'Half a minute: hunger, digestion, and any food that disagreed with you.')}
        </span>
        {saved?.red_flags?.length > 0 && (
          <p className="gym-checkin-stop" role="alert">
            <ShieldAlert size={14} /> {t('diet.ciSeeDoctor', 'Please see a doctor about what you reported — a different menu does not answer it. If your lips, face or tongue swell or breathing is hard, call 112 now.')}
          </p>
        )}
        {proposal?.changes?.length > 0 && (
          <div className="diet-checkin-proposal">
            <span>{proposal.from_week <= 4
              ? t('diet.ciWould', 'Weeks {{from}}–4 would change:', { from: proposal.from_week })
              : t('diet.ciNext', 'Your next plan will change:')}</span>
            <CheckinChanges proposal={proposal} />
            {proposal.rebuild_available && (
              <button type="button" className="gym-log-save gym-checkin-rebuild" onClick={rebuild}
                disabled={state === 'rebuilding'}>
                <RefreshCw size={12} /> {state === 'rebuilding'
                  ? t('diet.ciRebuilding', 'Rebuilding…')
                  : t('diet.ciRebuild', 'Rebuild weeks {{from}}–4 around it', { from: proposal.from_week })}
              </button>
            )}
            {proposal.rebuild_available && (
              <span className="gym-checkin-sub">{t('diet.ciRebuildNote', 'The weeks you have eaten stay as they are. This uses one plan generation.')}</span>
            )}
            {state === 'rebuildError' && <p className="gym-log-error">{t('diet.ciRebuildFailed', 'Could not rebuild — your plan is unchanged. Try again in a minute.')}</p>}
          </div>
        )}
        <button type="button" className="gym-log-toggle" onClick={openForm}>
          {saved ? t('diet.ciEdit', 'Edit check-in') : t('diet.ciStart', 'Check in')}
        </button>
      </div>
    )
  }

  const unused = foods.filter(f => !trouble.some(x => x.food === f.id))
  return (
    <div className="gym-checkin diet-checkin" role="group" aria-label={t('diet.ciAsk', 'How was week {{n}}?', { n: week })}>
      <span className="gym-checkin-title"><ClipboardCheck size={15} /> {t('diet.ciAsk', 'How was week {{n}}?', { n: week })}</span>

      <p className="gym-checkin-q">{t('diet.ciHungerQ', 'The amount of food was')}</p>
      <div className="gym-log-effort" role="radiogroup" aria-label={t('diet.ciHungerQ', 'The amount of food was')}>
        {HUNGER.map(o => (
          <button key={o.value} type="button" role="radio" aria-checked={hunger === o.value}
            className={`gym-log-chip${hunger === o.value ? ' active' : ''}`}
            onClick={() => setHunger(o.value)}>{t(o.i18n, o.label)}</button>
        ))}
      </div>

      <p className="gym-checkin-q">{t('diet.ciDigestionQ', 'Did you have any of these this week?')}</p>
      <div className="gym-log-effort">
        {DIGESTION.map(o => (
          <button key={o.value} type="button" aria-pressed={digestion.includes(o.value)}
            className={`gym-log-chip${digestion.includes(o.value) ? ' active' : ''}`}
            onClick={() => setDigestion(d => toggle(d, o.value))}>{t(o.i18n, o.label)}</button>
        ))}
      </div>

      <p className="gym-checkin-q">{t('diet.ciFoodQ', 'Did a food from this week disagree with you?')}</p>
      {trouble.map((x, i) => (
        <div key={x.food} className="diet-checkin-food">
          <span>{nameOf(x.food)}</span>
          <select value={x.problem} aria-label={t('diet.ciWhatHappened', 'What happened')}
            onChange={e => setTrouble(tr => tr.map((y, j) => (j === i ? { ...y, problem: e.target.value } : y)))}>
            {PROBLEMS.map(p => <option key={p.value} value={p.value}>{t(p.i18n, p.label)}</option>)}
          </select>
          <button type="button" className="diet-checkin-remove" aria-label={t('diet.ciRemove', 'Remove')}
            onClick={() => setTrouble(tr => tr.filter((_, j) => j !== i))}><X size={12} /></button>
        </div>
      ))}
      {trouble.length < MAX_TROUBLE && unused.length > 0 && (
        <select className="diet-checkin-add" value="" aria-label={t('diet.ciAddFood', 'Add a food')}
          onChange={e => e.target.value && setTrouble(tr => [...tr, { food: e.target.value, problem: 'bloating' }])}>
          <option value="">{t('diet.ciAddFood', 'Add a food')}</option>
          {unused.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
        </select>
      )}
      {trouble.length > 0 && (
        <span className="gym-checkin-sub">{t('diet.ciFoodNote', 'A food you name here is left out of the coming weeks and your next plan.')}</span>
      )}

      <p className="gym-checkin-q">{t('diet.ciFlagsQ', 'After eating, did any of these happen?')}</p>
      <div className="gym-log-effort">
        {DIET_RED_FLAGS.map(o => (
          <button key={o.value} type="button" aria-pressed={flags.includes(o.value)}
            className={`gym-log-chip gym-checkin-flag${flags.includes(o.value) ? ' active' : ''}`}
            onClick={() => setFlags(f => toggle(f, o.value))}>{t(o.i18n, o.label)}</button>
        ))}
      </div>
      {flags.length > 0 && (
        <p className="gym-checkin-stop" role="alert">
          <ShieldAlert size={14} /> {t('diet.ciSeeDoctor', 'Please see a doctor about what you reported — a different menu does not answer it. If your lips, face or tongue swell or breathing is hard, call 112 now.')}
        </p>
      )}
      {offerAllergies.map(a => {
        const label = ALLERGY_LABELS.find(x => x.value === a)
        return (
          <label key={a} className="gym-checkin-check">
            <input type="checkbox" checked={addAllergies.includes(a)}
              onChange={() => setAddAllergies(l => toggle(l, a))} />
            {t('diet.ciAddAllergy', 'Add {{allergy}} to my allergies, so no plan includes it', { allergy: label ? t(label.i18n, label.label) : a })}
          </label>
        )
      })}

      <div className="gym-log-actions">
        <button type="button" className="gym-log-cancel" onClick={() => setOpen(false)}>{t('diet.cancel', 'Cancel')}</button>
        <button type="button" className="gym-log-save" onClick={save} disabled={state === 'saving'}>
          {state === 'saving' ? t('diet.saving', 'Saving…') : <><Check size={12} /> {t('diet.save', 'Save')}</>}
        </button>
      </div>
      {state === 'error' && <p className="gym-log-error">{t('diet.ciSaveFailed', 'Could not save — check your connection and try again.')}</p>}
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

export function DietView({ plan: incomingPlan, onRegenerate, onPlanChange }) {
  const { t, i18n } = useTranslation()
  // A swapped meal or rebuilt weeks change the plan in place; the dashboard is told
  // through `onPlanChange`, so reopening the plan does not show the old one.
  const [englishPlan, setEnglishPlan] = useState(incomingPlan)
  useEffect(() => { setEnglishPlan(incomingPlan) }, [incomingPlan])
  const changePlan = (next) => {
    setEnglishPlan(next)
    onPlanChange?.(next)
  }
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
  // Logs are keyed to the English plan's id: a translation is the same plan.
  const planId = englishPlan.plan_id
  const today = planToday(englishPlan)
  // Where the plan opens: today; once the four weeks are over, the last week, on
  // today's weekday — not back at week 1 Monday, which reads as starting again.
  const openAt = (p) => {
    const now = planToday(p)
    if (!now) return { week: 0, day: 0 }
    return { week: now.over ? Math.max(0, (p.diet_weeks?.length || 4) - 1) : now.week - 1, day: now.dayIndex }
  }
  const [activeDay, setActiveDay] = useState(() => openAt(englishPlan).day)
  const [activeWeek, setActiveWeek] = useState(() => openAt(englishPlan).week)
  useEffect(() => {
    const at = openAt(incomingPlan)
    setActiveWeek(at.week)
    setActiveDay(at.day)
  }, [incomingPlan?.plan_id]) // eslint-disable-line react-hooks/exhaustive-deps
  const goToday = () => { if (today) { setActiveWeek(today.week - 1); setActiveDay(today.dayIndex) } }
  const [checkins, setCheckins] = useState(null)
  const loadCheckins = () => (planId
    ? mealsAPI.getCheckins(planId).then(r => setCheckins(r.data)).catch(() => {})
    : Promise.resolve())
  useEffect(() => { loadCheckins() }, [planId]) // eslint-disable-line react-hooks/exhaustive-deps
  // One day of the plan replaced — a swapped meal. The overlay's lines for that day
  // are dropped, so a translated view never shows the old dish's name in its place.
  const applyDay = (week, dayName, day) => {
    const next = {
      ...englishPlan,
      diet_weeks: (englishPlan.diet_weeks || []).map(w => (w.week_number === week
        ? { ...w, daily_plan: { ...w.daily_plan, [dayName]: day } } : w)),
      weekly_plan: week === 1 && englishPlan.weekly_plan
        ? { ...englishPlan.weekly_plan, [dayName]: day } : englishPlan.weekly_plan,
    }
    const wi = (englishPlan.diet_weeks || []).findIndex(w => w.week_number === week)
    const prefix = `diet_weeks.${wi}.daily_plan.${dayName}.`
    setOverlay(o => (o ? { ...o, strings: Object.fromEntries(Object.entries(o.strings || {})
      .filter(([k]) => !k.startsWith(prefix))) } : o))
    changePlan(next)
  }
  const replaceMeal = (week, dayName, slot, undo = false) => async () => {
    const { data } = await mealsAPI.replace({ plan_id: planId, week, day: dayName, slot, undo })
    applyDay(week, dayName, data.day)
  }
  const onRebuilt = (plan) => {
    setOverlay(null)
    setShowTranslated(false)
    changePlan(plan)
    loadCheckins()
  }
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
  const viewingTodayWeek = !!today && !today.over && today.week === weekNumber
  const viewingToday = viewingTodayWeek && today.dayIndex === activeDay
  // Only plans whose meals are stated as components can be logged: the log records
  // which foods were eaten or left, and an older plan's meals name none.
  const canLog = !!planId && fullDetail && !!dayData.lunch?.components
  // A week can be checked in once it has started; the plan's last week too, for the
  // next plan.
  const canCheckin = canLog && !!today && (today.over || weekNumber <= today.week)

  // Fallback path: four_week_plan array
  const fallbackDays = (plan.four_week_plan?.[0]?.days) || []
  const fallbackDay = fallbackDays[activeDay] || {}
  const timing = plan.meal_timing || {}
  // The day's copy is the English; the plan-level one carries the translation.
  const ritualName = (r) => (plan.daily_rituals || []).find(x => x.slot === r.slot)?.name || r.name
  const withheldGuidance = plan.withheld_guidance || []

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

      {isMultiWeek && today?.over && <DietPlanComplete planId={planId} onRegenerate={onRegenerate} />}

      {/* ── Week tabs (LLM 4-week plan) ── */}
      {isMultiWeek && (
        <div className="diet-week-tabs">
          {dietWeeks.map((wk, idx) => (
            <button
              key={idx}
              className={`diet-week-tab${activeWeek === idx ? ' active' : ''}`}
              onClick={() => { setActiveWeek(idx); setActiveDay(0); }}
            >
              <span className="diet-week-num">
                {t('diet.week', 'Week {{n}}', { n: wk.week_number })}
                {today && !today.over && today.week === wk.week_number && <span className="diet-today-dot" aria-label={t('diet.thisWeek', 'this week')} />}
              </span>
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
          const isToday = viewingTodayWeek && today.dayIndex === i
          return (
            <button key={i}
              className={`diet-day-btn ${activeDay === i ? 'active' : ''} ${isFasting ? 'fasting' : ''}${isToday ? ' is-today' : ''}`}
              onClick={() => setActiveDay(i)}
              aria-current={isToday ? 'date' : undefined}
              title={theme || label}>
              {t(`diet.day_${label}`, label)}
              {isFasting && <span className="diet-fast-dot" />}
            </button>
          )
        })}
      </div>

      {/* ── Selected-day heading ── */}
      <div className="diet-day-heading-row">
        <h3 className="diet-day-heading">
          {t(`diet.dayFull_${DIET_DAY_FULL[activeDay]}`, DIET_DAY_FULL[activeDay])}{isMultiWeek ? ` · ${t('diet.week', 'Week {{n}}', { n: activeWeek + 1 })}` : ''}
          {viewingToday ? ` · ${t('diet.today', 'Today')}` : ''}
        </h3>
        {isMultiWeek && today && !today.over && !viewingToday && (
          <button type="button" className="diet-translate-btn diet-today-btn" onClick={goToday}>
            <CalendarCheck size={12} /> {t('diet.goToday', 'Go to today')}
          </button>
        )}
      </div>

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
                  onLog={canLog ? logMeal(weekNumber, currentDayName, meal) : null}
                  onReplace={canLog ? replaceMeal(weekNumber, currentDayName, meal) : null}
                  onRestore={canLog ? replaceMeal(weekNumber, currentDayName, meal, true) : null} />
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
                  {dayData.day_totals
                    ? (dayData.rituals?.length
                      ? t('diet.dayTotalsAllDrinks', 'Day totals (calculated, including every drink)')
                      : t('diet.dayTotalsCalc', 'Day totals (calculated, incl. drink)'))
                    : t('diet.dayTotalsApprox', 'Day totals (approx.)')}
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
                {dayData.rituals?.length > 0 && (
                  <ul className="diet-ritual-list">
                    {dayData.rituals.map(r => (
                      <li key={r.slot}>
                        {r.slot === 'bedtime' ? <Moon size={11} /> : <CupSoda size={11} />}
                        <span className="diet-ritual-k">
                          {r.slot === 'bedtime' ? t('diet.bedtimeDrink', 'Bedtime drink') : t('diet.wakeDrink', 'Wake-up drink')}
                        </span>
                        <span>{ritualName(r)}{r.macros_approx?.calories > 0 ? ` · ${Math.round(r.macros_approx.calories)} kcal` : ''}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )
          })()}
          {canCheckin && (
            <DietWeekCheckin planId={planId} week={weekNumber} data={checkins}
              onSaved={loadCheckins} onRebuilt={onRebuilt} />
          )}
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
              {timing.window_notice && <p className="diet-energy-note is-warn">{timing.window_notice}</p>}
              {timing.general_note && <p className="diet-timing-note">{timing.general_note}</p>}
              <div className="diet-timing-rows">
                {timing.eating_window && (
                  <div className="diet-timing-row special">
                    <Timer size={11} />
                    <span className="diet-timing-meal">{t('diet.eatingWindow', 'Eating window')}</span>
                    <span className="diet-timing-time">{timing.eating_window}</span>
                  </div>
                )}
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
                {timing.after_window && (
                  <div className="diet-timing-row special">
                    <Moon size={11} />
                    <span className="diet-timing-meal">{t('diet.afterWindow', 'After the window')}</span>
                    <span className="diet-timing-time">{timing.after_window}</span>
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
                  {s.note && <p className="diet-spice-guide-use diet-spice-guide-note">{s.note}</p>}
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
      {/* Drinks, spices and tips the standard guidance for this dosha would have
          given, left out because the patient's own food list rules them out. Saying
          so is the point: advice that vanishes silently looks like an oversight. */}
      {withheldGuidance.length > 0 && (
        <div className="diet-energy-note diet-withheld-guidance">
          <span>{t('diet.withheldGuidance', 'Left out of the guidance for you:')}</span>
          <ul>{withheldGuidance.map((w, i) => <li key={i}>{w.item} — {w.reason}</li>)}</ul>
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
