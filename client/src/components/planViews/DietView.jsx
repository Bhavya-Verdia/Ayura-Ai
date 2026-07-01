import React, { useState } from 'react'
import {
  Sun, Leaf, Coffee, AlertTriangle, Star, Droplets, ShieldCheck, Flame, Moon, Timer, Target, ChevronDown, ChevronUp, Flower2, UtensilsCrossed, Clock, Soup, Apple, CupSoda, BookOpen, TriangleAlert,
} from 'lucide-react'
import { DOSHA_COLOR } from '../../constants/dosha'
import { RemedyView } from './RemedyView'

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

// Deterministic Ahara safety banner — surfaces the post-LLM safety scan
// (Viruddha Ahara + allergens across ALL weeks, including compact weeks 2–4
// where per-meal flags can't be shown). Backend: services/ahara_safety.py.

function DietSafetyBanner({ plan }) {
  if (!plan?.ahara_safety_checked) return null
  const alerts = plan.safety_alerts || []
  const viruddha = plan.viruddha_ahara_detected || []

  if (!alerts.length && !viruddha.length) {
    return (
      <div className="diet-safety-ok">
        <ShieldCheck size={13} />
        <span>Checked for allergens &amp; incompatible food combinations (Viruddha Ahara) — none found.</span>
      </div>
    )
  }
  return (
    <div className="diet-safety-banner">
      {alerts.length > 0 && (
        <div className="diet-safety-card allergen">
          <div className="diet-safety-title">
            <TriangleAlert size={13} /> Allergen conflicts — substitute before following these meals
          </div>
          <ul className="diet-safety-list">
            {alerts.map((a, i) => (
              <li key={i}>
                <strong>{a.week} · {a.day} · {a.meal_slot}</strong>: contains {(a.matched_terms || []).join(', ')}
              </li>
            ))}
          </ul>
        </div>
      )}
      {viruddha.length > 0 && (
        <div className="diet-safety-card viruddha">
          <div className="diet-safety-title">
            <TriangleAlert size={13} /> Viruddha Ahara detected (Charaka Sutrasthana 26)
          </div>
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


export function DietView({ plan }) {
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
