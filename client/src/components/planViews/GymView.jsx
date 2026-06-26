import React, { useState } from 'react'
import {
  Dumbbell, Leaf, Calendar, Flame, Moon, Timer, Zap, Target, Activity, ChevronDown, ChevronUp, Lightbulb,
} from 'lucide-react'
import { DOSHA_COLOR } from './shared'

const WEEK_THEMES = ['Foundation', 'Volume Build', 'Intensity Peak', 'Deload']


export function GymView({ plan }) {
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
          <span className="gym-week-banner-icon"><Lightbulb size={16} strokeWidth={2} /></span>
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

      {/* ── Vyayama Shakti (classical exercise-capacity principle) ── */}
      {plan.vyayama_shakti && (
        <div className="gym-vyayama-section">
          <div className="gym-tips-title"><Flame size={14} /> Vyayama Shakti — Exercise Capacity (Charaka Sutrasthana 7)</div>
          <p className="gym-vyayama-principle">{plan.vyayama_shakti.principle}</p>
          <p className="gym-vyayama-capacity">{plan.vyayama_shakti.your_capacity}</p>
          <div className="gym-vyayama-grid">
            <div className="gym-vyayama-card adequate">
              <div className="gym-vyayama-label">Signs of adequate exercise</div>
              <p>{plan.vyayama_shakti.signs_adequate}</p>
            </div>
            <div className="gym-vyayama-card over">
              <div className="gym-vyayama-label">Signs of over-exercise (Ativyayama)</div>
              <p>{plan.vyayama_shakti.signs_overexertion}</p>
            </div>
          </div>
          {plan.vyayama_shakti.bala_note && (
            <p className="gym-vyayama-bala">{plan.vyayama_shakti.bala_note}</p>
          )}
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
