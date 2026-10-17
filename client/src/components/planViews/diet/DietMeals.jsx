// A meal card and the controls on it: macros, the meal log and "another dish".

import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { mealsAPI } from '../../../api/client'
import {
  Leaf, Flame, ChevronDown, ChevronUp, UtensilsCrossed, Shuffle, Undo2,
} from 'lucide-react'
import { DIET_MEAL_ICONS, SLOT_LABEL } from './dietConstants'

export function MacroBar({ macros }) {
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

export function MealLogSummary({ planId, logs }) {
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

export function LLMMealCard({ mealName, meal, log, onLog, onReplace, onRestore }) {
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
