import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { mealsAPI, plansAPI } from '../../api/client'
import {
  Sun, Leaf, Droplets, ShieldCheck, Flame, Moon, Timer, Target, ChevronDown, ChevronUp, Flower2, UtensilsCrossed, Clock, CupSoda, BookOpen, Languages, Award, RefreshCw, CalendarCheck,
} from 'lucide-react'
import { DOSHA_COLOR, doshaInk } from '../../constants/dosha'
import { PathyaApathyaCard, DietSafetyBanner, EnergyPrescriptionCard, NutrientTargetsCard, ClinicalNotesCard, TargetsSummary } from './diet/DietCards'
import { MacroBar, MealLogSummary, LLMMealCard } from './diet/DietMeals'
import { DietWeekCheckin } from './diet/DietWeekCheckin'
import { DIET_MEAL_ICONS, DIET_DAY_LABELS, SLOT_LABEL, DIET_DAY_FULL } from './diet/dietConstants'

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

      {/* ── Targets, in one line ── the full cards are below the meals (see there). */}
      <TargetsSummary plan={plan} targetId="diet-targets" />
      {/* Medicine-food interactions stay above the meals: they change what to eat. */}
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

      {/* ── Condition coaching ── */}
      {plan.condition_coaching && (
        <div className="diet-coaching-card">
          <ShieldCheck size={13} className="diet-coaching-icon" />
          <p className="diet-coaching-text">{plan.condition_coaching}</p>
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

      {/* ── Energy prescription and daily targets ── below the meals so the day's
           food is the first thing on screen; TargetsSummary above counts the
           warnings in them and links here. The day totals above read against these. */}
      <div id="diet-targets" className="diet-targets-anchor">
        <EnergyPrescriptionCard plan={plan} />
        <NutrientTargetsCard plan={plan} />
      </div>

      {/* ── Pathya-Apathya (LLM only) ── */}
      {isLLM && <PathyaApathyaCard pa={plan.pathya_apathya} />}

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

