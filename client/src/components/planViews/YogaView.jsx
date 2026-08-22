import React, { useState } from 'react'
import {
  Sun, Leaf, AlertTriangle, Droplets, ShieldCheck, Flame, Moon, Timer, Zap, Target, Activity, ChevronDown, ChevronUp, Wind, Flower2, Brain, Play, Info,
} from 'lucide-react'
import { DOSHA_COLOR, doshaInk } from '../../constants/dosha'
import { PoseFigure } from './PoseFigure'
import { SessionPlayer } from './SessionPlayer'
import { WeekFeedbackCard } from './WeekFeedbackCard'
import { primaryName, secondaryName } from './poseNames'
import { useTranslation } from 'react-i18next'

const SNS_BREATH_COLOR = { 'Inhale': '#3b82f6', 'Exhale': '#ef4444', 'Natural': '#6b7280', 'Exhale — hold 3-5 breaths': '#ef4444' }


function SuryaNamaskarCard({ sns }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const pace = (sns.pace || '').replace(/\b\w/g, c => c.toUpperCase())
  return (
    <div className="sns-card">
      <div className="sns-header">
        <div className="sns-title-row">
          <Sun size={14} className="sns-sun-icon" />
          <span className="sns-title">{t('yoga.suryaNamaskar', 'Surya Namaskar')}</span>
          <span className="sns-sanskrit">सूर्य नमस्कार</span>
        </div>
        <div className="sns-meta">
          <span className="sns-badge">{t('yoga.rounds', '{{count}} rounds', { count: sns.rounds })}</span>
          <span className="sns-badge pace">{pace}</span>
          <span className="sns-badge dur">{sns.duration_minutes} min</span>
        </div>
      </div>

      <p className="sns-pace-note">{sns.pace_note}</p>

      {sns.senior_modification && (
        <div className="sns-senior-note">
          <ShieldCheck size={11} /> {sns.senior_modification}
        </div>
      )}

      {sns.safety_notes?.length > 0 && (
        <div className="sns-warnings">
          {sns.safety_notes.map((w, i) => (
            <div key={i} className="sns-warning-row">
              <AlertTriangle size={11} className="sns-warn-icon" />
              <span>{w}</span>
            </div>
          ))}
        </div>
      )}

      <button className="sns-toggle" onClick={() => setOpen(o => !o)}>
        {open ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
        {open ? t('yoga.hideSteps', 'Hide 12 steps') : t('yoga.showSteps', 'Show 12 steps')}
      </button>

      {open && (
        <div className="sns-steps">
          {sns.steps.map((step) => {
            const breathColor = SNS_BREATH_COLOR[step.breath] || '#6b7280'
            return (
              <div key={step.step} className="sns-step-row">
                <div className="sns-step-num">{step.step}</div>
                <div className="sns-step-body">
                  <div className="sns-step-names">
                    <span className="sns-step-sanskrit">{step.sanskrit}</span>
                    <span className="sns-step-english">{step.english}</span>
                    {step.breath && step.breath !== 'Natural' && (
                      <span className="sns-breath-pill" style={{ color: breathColor, borderColor: `${breathColor}44`, background: `${breathColor}12` }}>
                        {step.breath.replace('Exhale — hold 3-5 breaths', 'Exhale + hold')}
                      </span>
                    )}
                  </div>
                  <p className="sns-step-cue">{step.cue}</p>
                  {step.modification && (
                    <p className="sns-step-mod">{step.modification}</p>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {sns.classical_reference && !open && (
        <p className="sns-classical-ref">{sns.classical_reference.split('.')[0]}.</p>
      )}
      {open && sns.classical_reference && (
        <p className="sns-classical-ref">{sns.classical_reference}</p>
      )}
    </div>
  )
}

// ── Yoga dedicated renderer ────────────────────────────────────────────────────

const YOGA_WEEK_THEMES = ['Foundation', 'Deepen', 'Challenge', 'Integration']


export function YogaView({ plan: planProp }) {
  const { t } = useTranslation()
  // Generating the next week returns the whole updated plan; hold it locally so
  // the new week appears immediately rather than waiting on a refetch.
  const [livePlan, setLivePlan] = useState(null)
  const plan = livePlan || planProp
  const [activeWeek, setActiveWeek] = useState(0)
  const [expandedPoses, setExpandedPoses] = useState(new Set())
  const [expandedWarmup, setExpandedWarmup] = useState(new Set())
  const [expandedCooldown, setExpandedCooldown] = useState(new Set())
  const [expandedPrana, setExpandedPrana] = useState(new Set())
  const [expandedDharana, setExpandedDharana] = useState(new Set())
  // Which day cards are open. Every day used to render fully expanded, so one
  // week was ~5,400px — six screens. Days now start closed and open only on
  // click, so a week is one scannable list of seven rows.
  const [expandedDays, setExpandedDays] = useState(new Set())
  // Which session, if any, is currently being practised in the guided player.
  const [activeSession, setActiveSession] = useState(null)

  const us = plan.user_summary || {}
  const fourWeekPlan = plan.four_week_plan || []
  const totalWeeks = plan.total_weeks || 4
  // `next_week` is absent on plans generated before the week-by-week change —
  // those already contain all four weeks and need no continuation affordance.
  const nextWeek = plan.next_week || null
  const latestWeek = fourWeekPlan.length ? fourWeekPlan[fourWeekPlan.length - 1] : null
  const showFeedback = Boolean(nextWeek && latestWeek)
  const activeWeekData = fourWeekPlan[activeWeek] || null
  const weekDays = activeWeekData?.days || []
  const weekNote = activeWeekData?.note || null
  const tips = plan.ayurvedic_tips || {}
  const dailyIntention = plan.daily_intention || {}

  // Day indices mean a different day's content once the week changes, so a
  // week switch starts closed rather than carrying the old week's open rows.
  const selectWeek = (i) => {
    setActiveWeek(i)
    setExpandedDays(new Set())
  }

  const toggleDay = (i) => setExpandedDays(prev => {
    const next = new Set(prev)
    next.has(i) ? next.delete(i) : next.add(i)
    return next
  })

  // Expand/collapse all — the escape hatch from per-day clicking when you want
  // to read (or print) the whole week at once.
  const allDaysOpen = weekDays.length > 0 && expandedDays.size === weekDays.length
  const toggleAllDays = () => setExpandedDays(
    allDaysOpen ? new Set() : new Set(weekDays.map((_, i) => i))
  )

  const doshaColor = DOSHA_COLOR[us.dominant_dosha] || DOSHA_COLOR.default
  const doshaText = doshaInk(us.dominant_dosha)
  const goalLabel = (us.yoga_goal || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  const styleLabel = Array.isArray(us.style_preference)
    ? us.style_preference.join(', ')
    : (us.style_preference || '')

  const togglePose = (id) => setExpandedPoses(prev => {
    const next = new Set(prev); next.has(id) ? next.delete(id) : next.add(id); return next
  })
  const toggleWarmup = (dayIdx) => setExpandedWarmup(prev => {
    const next = new Set(prev); next.has(dayIdx) ? next.delete(dayIdx) : next.add(dayIdx); return next
  })
  const toggleCooldown = (dayIdx) => setExpandedCooldown(prev => {
    const next = new Set(prev); next.has(dayIdx) ? next.delete(dayIdx) : next.add(dayIdx); return next
  })
  // Keyed by day AND technique: the stack is three breaths (four when a Pitta
  // earns a cooling chaser), so a per-day key would open all of them at once.
  const togglePrana = (key) => setExpandedPrana(prev => {
    const next = new Set(prev); next.has(key) ? next.delete(key) : next.add(key); return next
  })
  const toggleDharana = (dayIdx) => setExpandedDharana(prev => {
    const next = new Set(prev); next.has(dayIdx) ? next.delete(dayIdx) : next.add(dayIdx); return next
  })

  return (
    <div className="yoga-view">
      {plan.plan_description && (
        <p className="yoga-description">{plan.plan_description}</p>
      )}

      {/* ── Age group + medical conditions banner ── */}
      <div className="yoga-banners-row">
        {us.age_group && us.age_group !== 'adult' && (
          <div className={`yoga-age-badge ${us.age_group}`} style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            {us.age_group === 'senior'
              ? <><Leaf size={14} strokeWidth={2} /> {t('yoga.seniorAdapted', 'Senior-Adapted Practice')}</>
              : <><Zap size={14} strokeWidth={2} /> {t('yoga.youthPractice', 'Youth Practice')}</>}
          </div>
        )}
        {us.medical_conditions?.length > 0 && (
          <div className="yoga-medical-banner">
            <span className="yoga-medical-label">{t('yoga.personalisedFor', 'Personalised for:')}</span>
            {us.medical_conditions.map(c => (
              <span key={c} className="yoga-medical-chip">{c.replace(/_/g, ' ')}</span>
            ))}
          </div>
        )}
      </div>

      {/* ── Pranayama safety exclusions (forceful breaths removed for safety) ── */}
      {plan.pranayama_safety_exclusions?.length > 0 && (
        <div className="yoga-prana-exclusions">
          <h3 className="yoga-prana-excl-title">
            <ShieldCheck size={13} /> {t('yoga.excludedForSafety', 'Excluded for your safety')}
          </h3>
          <ul className="yoga-prana-excl-list">
            {plan.pranayama_safety_exclusions.map((ex, i) => (
              <li key={i}><strong>{ex.name}</strong> — {ex.reason}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Why a breath the practitioner did not ask for is in the stack: the
          condition chose it, or it cools a heating one that the condition
          chose. Both notes were written by the engine and never rendered. */}
      {plan.pranayama_protocol_note && (
        <div className="yoga-pool-notice">
          <Wind size={12} />
          <span>{plan.pranayama_protocol_note}</span>
        </div>
      )}
      {plan.pranayama_cooling_note && (
        <div className="yoga-pool-notice">
          <Wind size={12} />
          <span>{plan.pranayama_cooling_note}</span>
        </div>
      )}

      {/* ── Seasonal note ── */}
      {plan.seasonal_note && (
        <div className="yoga-seasonal-note">
          <Leaf size={12} />
          <span>{plan.seasonal_note}</span>
        </div>
      )}

      {/* Why this plan is narrower than usual — the engine has written this for a
          heavily filtered pool since the safety pass, and nothing rendered it. */}
      {plan.practice_pool_notice && (
        <div className="yoga-pool-notice">
          <Info size={12} />
          <span>{plan.practice_pool_notice}</span>
        </div>
      )}

      {/* A limitation the user typed that no filter could act on. It sits with the
          pool notice rather than lower down because it changes whether the sequence
          below is safe for them, and a plan they scroll past is a plan they practise. */}
      {plan.unrecognised_limitations && (
        <div className="yoga-pool-notice yoga-unrecognised-notice">
          <AlertTriangle size={12} />
          <span>{plan.unrecognised_limitations.notice}</span>
        </div>
      )}

      {/* ── Vitals bar ── */}
      <div className="yoga-vitals">
        {goalLabel && (
          <div className="yoga-vital-chip">
            <Target size={11} /><span className="yoga-vital-k">{t('yoga.vital.goal', 'Goal')}</span><span className="yoga-vital-v">{goalLabel}</span>
          </div>
        )}
        {us.dominant_dosha && (
          <div className="yoga-vital-chip" style={{ borderColor: `${doshaColor}44`, color: doshaText }}>
            <span className="yoga-vital-k">{t('yoga.vital.dosha', 'Dosha')}</span><span className="yoga-vital-v">{us.dominant_dosha.toUpperCase()}</span>
          </div>
        )}
        {us.experience && (
          <div className="yoga-vital-chip">
            <Activity size={11} /><span className="yoga-vital-k">{t('yoga.vital.level', 'Level')}</span>
            <span className="yoga-vital-v">{us.experience.replace(/\b\w/g, c => c.toUpperCase())}</span>
          </div>
        )}
        {styleLabel && (
          <div className="yoga-vital-chip">
            <Flower2 size={11} /><span className="yoga-vital-k">{t('yoga.vital.style', 'Style')}</span><span className="yoga-vital-v">{styleLabel}</span>
          </div>
        )}
        {us.time_available && (
          <div className="yoga-vital-chip">
            <Timer size={11} /><span className="yoga-vital-k">{t('yoga.vital.duration', 'Duration')}</span><span className="yoga-vital-v">{t('yoga.minutes', '{{count}} min', { count: us.time_available })}</span>
          </div>
        )}
        {us.time_of_day && (
          <div className="yoga-vital-chip">
            <Sun size={11} /><span className="yoga-vital-k">{t('yoga.vital.time', 'Time')}</span>
            <span className="yoga-vital-v">{us.time_of_day.replace(/\b\w/g, c => c.toUpperCase())}</span>
          </div>
        )}
        {us.agni_type && (
          <div className="yoga-vital-chip yoga-vital-agni">
            <Flame size={11} /><span className="yoga-vital-k">{t('yoga.vital.agni', 'Agni')}</span>
            <span className="yoga-vital-v">{us.agni_type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</span>
          </div>
        )}
        {us.ojas_level && (
          <div className="yoga-vital-chip yoga-vital-ojas">
            <Droplets size={11} /><span className="yoga-vital-k">{t('yoga.vital.ojas', 'Ojas')}</span>
            <span className="yoga-vital-v">{us.ojas_level.replace(/\b\w/g, c => c.toUpperCase())}</span>
          </div>
        )}
        {us.stress_level && us.stress_level !== 'low' && (
          <div className="yoga-vital-chip yoga-vital-stress">
            <Zap size={11} /><span className="yoga-vital-k">{t('yoga.vital.stress', 'Stress')}</span>
            <span className="yoga-vital-v">{us.stress_level.replace(/\b\w/g, c => c.toUpperCase())}</span>
          </div>
        )}
      </div>

      {/* ── Condition protocol cards ── */}
      {plan.condition_protocols?.length > 0 && (
        <div className="yoga-protocols">
          {plan.condition_protocols.map((proto, pi) => (
            <details key={pi} className="yoga-protocol-card">
              <summary className="yoga-protocol-summary">
                <span className="yoga-protocol-condition">{proto.condition.replace(/_/g, ' ')}</span>
                <span className="yoga-protocol-name">{proto.protocol_name}</span>
              </summary>
              <div className="yoga-protocol-body">
                {proto.sequence_note && <p className="yoga-protocol-seq">{proto.sequence_note}</p>}
                {proto.lifestyle_note && <p className="yoga-protocol-life">{proto.lifestyle_note}</p>}
                {proto.research_note && <p className="yoga-protocol-research">{proto.research_note}</p>}
                {proto.classical_reference && (
                  <p className="yoga-protocol-ref">{proto.classical_reference}</p>
                )}
              </div>
            </details>
          ))}
        </div>
      )}

      {/* ── Age coaching (LLM-generated for senior/youth) ── */}
      {plan.age_coaching && (
        <div className="yoga-age-coaching">
          <p className="yoga-age-coaching-text">{plan.age_coaching}</p>
        </div>
      )}

      {/* ── Condition coaching (LLM-generated, only when user has conditions) ── */}
      {plan.condition_coaching && (
        <div className="yoga-condition-coaching">
          <p className="yoga-condition-coaching-text">{plan.condition_coaching}</p>
        </div>
      )}

      {/* ── Week tabs ── */}
      <div className="yoga-week-tabs">
        {fourWeekPlan.map((wk, i) => {
          const theme = wk.theme || YOGA_WEEK_THEMES[i] || ''
          return (
            <button
              key={wk.week ?? i}
              className={`yoga-week-tab${activeWeek === i ? ' active' : ''}`}
              onClick={() => selectWeek(i)}
            >
              <span className="yoga-tab-num">{t('yoga.week', 'Week {{n}}', { n: wk.week ?? i + 1 })}</span>
              <span className="yoga-tab-theme">{t(`yoga.weekTheme.${theme.toLowerCase()}`, theme)}</span>
            </button>
          )
        })}
        {nextWeek && Array.from({ length: totalWeeks - fourWeekPlan.length }, (_, i) => {
          const weekNum = fourWeekPlan.length + i + 1
          return (
            <div key={`pending-${weekNum}`} className="yoga-week-tab pending" aria-disabled="true">
              <span className="yoga-tab-num">{t('yoga.week', 'Week {{n}}', { n: weekNum })}</span>
              <span className="yoga-tab-theme">
                {weekNum === nextWeek
                  ? t('yoga.weekNext', 'After your feedback')
                  : t('yoga.weekLater', 'Not yet built')}
              </span>
            </div>
          )
        })}
      </div>

      {/* What last week's feedback changed, in the user's own terms. */}
      {plan.progression_adjustment?.reasons?.length > 0 && (
        <div className="yoga-progression-note">
          <span className="yoga-progression-title">
            {t('yoga.progressionTitle', 'Adjusted from your feedback')}
          </span>
          <ul className="yoga-progression-list">
            {plan.progression_adjustment.reasons.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        </div>
      )}

      {/* ── Week note banner ── */}
      {weekNote && (
        <div className="yoga-week-banner">
          <span className="yoga-week-banner-icon"><Leaf size={16} strokeWidth={2} /></span>
          <span className="yoga-week-banner-text">
            <strong>{t('yoga.week', 'Week {{n}}', { n: activeWeek + 1 })} · {t(`yoga.weekTheme.${YOGA_WEEK_THEMES[activeWeek].toLowerCase()}`, YOGA_WEEK_THEMES[activeWeek])}:</strong> {weekNote}
          </span>
        </div>
      )}

      {/* ── Day-list toolbar ── */}
      {weekDays.length > 0 && (
        <div className="plan-days-toolbar">
          <h3 className="plan-days-toolbar-title">{t('yoga.weekDays', 'Week {{n}} — {{count}} days', { n: activeWeek + 1, count: weekDays.length })}</h3>
          <button type="button" className="plan-days-toolbar-btn" onClick={toggleAllDays}>
            {allDaysOpen ? t('yoga.collapseAll', 'Collapse all') : t('yoga.expandAll', 'Expand all')}
          </button>
        </div>
      )}

      {/* ── Day cards ── */}
      <div className="yoga-days-grid">
        {weekDays.map((day, dayIdx) => {
          const isRest = day.rest || !day.session
          const session = day.session || {}
          const intention = dailyIntention[day.day_name] || null
          const warmupOpen = expandedWarmup.has(dayIdx)
          const cooldownOpen = expandedCooldown.has(dayIdx)
          const dayOpen = expandedDays.has(dayIdx)

          // Shown on the collapsed card so a closed day still says what it is.
          // Rest days say it with their badge, so they get no summary.
          const summaryBits = isRest ? [] : [
            session.main_sequence?.length && `${session.main_sequence.length} poses`,
            session.warmup?.length && `${session.warmup.length} warmup`,
            session.cooldown?.length && `${session.cooldown.length} cooldown`,
            session.pranayama_section && 'pranayama',
          ].filter(Boolean)

          return (
            <div key={dayIdx} className={`yoga-day-card${isRest ? ' rest' : ''}${dayOpen ? ' open' : ''}`}>
              {/* h3 wrapping the disclosure button is the standard accordion
                  shape: the day is a landmark in the outline AND the control. */}
              <h3 className="yoga-day-heading">
                <button
                  type="button"
                  className="yoga-day-header yoga-day-toggle"
                  onClick={() => toggleDay(dayIdx)}
                  aria-expanded={dayOpen}
                >
                  <div className="yoga-day-name">
                    {isRest ? <Moon size={13} /> : <Flower2 size={13} />}
                    {day.day_name || `Day ${day.day}`}
                  </div>
                  <div className="yoga-day-headmeta">
                    {!dayOpen && summaryBits.length > 0 && (
                      <span className="yoga-day-summary">{summaryBits.join(' · ')}</span>
                    )}
                    {/* The week has a load arc — two strong days, three moderate,
                        one gentle, one restorative, all in the same time slot. The
                        badge is what makes that visible: without it an easy Sunday
                        reads as a thin plan rather than as the recovery day. */}
                    {!isRest && session.intensity && (
                      <span className={`yoga-intensity-badge ${session.intensity}`}>
                        {t(`yoga.intensity.${session.intensity}`, session.intensity_label)}
                      </span>
                    )}
                    {isRest
                      ? <span className="yoga-duration-badge-sm rest">{t('yoga.rest', 'Rest')}</span>
                      : session.total_duration_minutes && (
                        <span className="yoga-duration-badge-sm">{session.total_duration_minutes} min</span>
                      )}
                    {dayOpen ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                  </div>
                </button>
              </h3>

              {!dayOpen ? null : isRest ? (
                <div className="yoga-rest-card">
                  <p className="yoga-rest-tip">{t('yoga.restTip', "Let your body absorb the week's practice. Gentle movement and stillness are welcome.")}</p>
                </div>
              ) : (
                <>
                  {/* The badge now reports the session that was built, so when that is
                      materially short of the request, say why instead of leaving the
                      practitioner to notice the gap themselves. */}
                  {session.duration_notice && (
                    <div className="yoga-duration-notice">
                      <Info size={12} />
                      <span>{session.duration_notice}</span>
                    </div>
                  )}
                  {/* Why this day is easier or harder than yesterday, in the same
                      slot and largely the same sequence. Without it the arc is
                      invisible and an easy day just looks like a repeat.
                      `effort_cue` is the instruction that actually makes the day
                      lighter, so it belongs with the note rather than buried. */}
                  {session.intensity_note && (
                    <div className="yoga-duration-notice">
                      <Info size={12} />
                      <span>
                        {session.intensity_note}
                        {session.effort_cue && ` ${session.effort_cue}`}
                      </span>
                    </div>
                  )}
                  {/* Two days a week carry a second breathing technique, paid for
                      out of asana. Without this the shorter pose list reads as
                      the plan running out rather than as the day's design. */}
                  {session.pranayama_focus_note && (
                    <div className="yoga-duration-notice">
                      <Wind size={12} />
                      <span>{session.pranayama_focus_note}</span>
                    </div>
                  )}
                  {session.rotation_notice && (
                    <div className="yoga-duration-notice">
                      <Info size={12} />
                      <span>{session.rotation_notice}</span>
                    </div>
                  )}
                  <button
                    type="button"
                    className="yoga-practice-btn"
                    onClick={() => setActiveSession({
                      session,
                      week: activeWeekData?.week || activeWeek + 1,
                      day: day.day,
                    })}
                  >
                    <Play size={14} /> {t('yoga.startPractice', 'Start guided practice')}
                  </button>

                  {session.dosha_theme && (
                    <p className="yoga-session-theme">{session.dosha_theme}</p>
                  )}
                  {intention && (
                    <div className="yoga-day-intention">&ldquo;{intention}&rdquo;</div>
                  )}

                  {/* Surya Namaskar flow */}
                  {session.surya_namaskar && (
                    <SuryaNamaskarCard sns={session.surya_namaskar} />
                  )}

                  {/* Warmup collapsible */}
                  {session.warmup?.length > 0 && (
                    <div className="yoga-section-block">
                      <button className="yoga-section-toggle" onClick={() => toggleWarmup(dayIdx)}>
                        <span className="yoga-section-label">{t('yoga.section.warmup', 'Warmup ({{count}})', { count: session.warmup.length })}</span>
                        {warmupOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                      </button>
                      {warmupOpen && (
                        <ul className="yoga-pose-list">
                          {session.warmup.map((p, pi) => (
                            <li key={pi} className="yoga-warmup-pose">
                              <span className="yoga-wp-names">
                                <span className="yoga-wp-name">{primaryName(p)}</span>
                                {secondaryName(p) && (
                                  <span className="yoga-wp-english">{secondaryName(p)}</span>
                                )}
                              </span>
                              {p.duration_seconds && <span className="yoga-wp-dur">{p.duration_seconds}s</span>}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}

                  {/* Main sequence */}
                  {session.main_sequence?.length > 0 && (
                    <div className="yoga-section-block">
                      <h4 className="yoga-section-label standalone">{t('yoga.section.main', 'Main Practice ({{count}} poses)', { count: session.main_sequence.length })}</h4>
                      <div className="yoga-main-list">
                        {session.main_sequence.map((p, pi) => {
                          const poseId = `${dayIdx}-main-${pi}`
                          const isOpen = expandedPoses.has(poseId)
                          return (
                            <div key={pi} className="yoga-pose-row">
                              <div className="yoga-pose-top">
                                <div className="yoga-pose-name-block">
                                  <span className="yoga-pose-name">{primaryName(p)}</span>
                                  {secondaryName(p) && (
                                    <span className="yoga-pose-english">{secondaryName(p)}</span>
                                  )}
                                </div>
                                <div className="yoga-pose-chips">
                                  {p.duration_seconds && (
                                    <span className="yoga-duration-badge">{p.duration_seconds}s</span>
                                  )}
                                  {p.category && (
                                    <span className="yoga-category-chip">{p.category}</span>
                                  )}
                                </div>
                              </div>
                              {p.primary_benefits?.length > 0 && (
                                <ul className="yoga-pose-benefits">
                                  {p.primary_benefits.slice(0, 2).map((b, bi) => <li key={bi}>{b}</li>)}
                                </ul>
                              )}
                              {(p.instructions?.length > 0 || p.modification || p.ayurvedic_rationale) && (
                                <>
                                  <button className="yoga-pose-expand-toggle" onClick={() => togglePose(poseId)}>
                                    {isOpen ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
                                    {isOpen ? t('yoga.less', 'Less') : t('yoga.details', 'Details')}
                                  </button>
                                  {isOpen && (
                                    <div className="yoga-pose-expand">
                                      <PoseFigure imageUrl={p.image_url} name={primaryName(p)} category={p.category}
                                                  figure={p.figure} />
                                      {p.instructions?.length > 0 && (
                                        <ol className="yoga-pose-instructions">
                                          {p.instructions.map((step, si) => <li key={si}>{step}</li>)}
                                        </ol>
                                      )}
                                      {p.modification && (
                                        <p className="yoga-pose-modification">{t('yoga.modification', 'Modification')}: {p.modification}</p>
                                      )}
                                      {p.ayurvedic_rationale && (
                                        <p className="yoga-pose-rationale">{p.ayurvedic_rationale}</p>
                                      )}
                                    </div>
                                  )}
                                </>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}

                  {/* Cooldown collapsible */}
                  {session.cooldown?.length > 0 && (
                    <div className="yoga-section-block">
                      <button className="yoga-section-toggle" onClick={() => toggleCooldown(dayIdx)}>
                        <span className="yoga-section-label">{t('yoga.section.cooldown', 'Cooldown ({{count}})', { count: session.cooldown.length })}</span>
                        {cooldownOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                      </button>
                      {cooldownOpen && (
                        <ul className="yoga-pose-list">
                          {session.cooldown.map((p, pi) => (
                            <li key={pi} className="yoga-warmup-pose">
                              <span className="yoga-wp-names">
                                <span className="yoga-wp-name">{primaryName(p)}</span>
                                {secondaryName(p) && (
                                  <span className="yoga-wp-english">{secondaryName(p)}</span>
                                )}
                              </span>
                              {p.duration_seconds && <span className="yoga-wp-dur">{p.duration_seconds}s</span>}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}

                  {/* Pranayama */}
                  {session.pranayama_section?.map((pr, prIdx) => {
                    const pranaKey = `${dayIdx}-${prIdx}`
                    const pranaOpen = expandedPrana.has(pranaKey)
                    const hasInstructions = pr.instructions?.length > 0
                    return (
                      <div className="yoga-prana-card" key={pr.technique_id || prIdx}>
                        <div className="yoga-prana-header">
                          <Wind size={12} className="yoga-prana-icon" />
                          <span className="yoga-prana-name">
                            {primaryName(pr)}
                            {secondaryName(pr) && (
                              <span className="yoga-prana-sanskrit"> · {secondaryName(pr)}</span>
                            )}
                          </span>
                          {pr.duration_minutes && (
                            <span className="yoga-prana-dur">{pr.duration_minutes} min</span>
                          )}
                        </div>
                        {pr.dosha_note && (
                          <p className="yoga-prana-dosha-note">{pr.dosha_note}</p>
                        )}
                        {hasInstructions && (
                          <>
                            <button className="yoga-pose-expand-toggle" onClick={() => togglePrana(pranaKey)}>
                              {pranaOpen ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
                              {pranaOpen ? t('yoga.less', 'Less') : t('yoga.instructions', 'Instructions')}
                            </button>
                            {pranaOpen && (
                              <ol className="yoga-pose-instructions yoga-prana-instructions">
                                {pr.instructions.map((step, si) => <li key={si}>{step}</li>)}
                              </ol>
                            )}
                          </>
                        )}
                      </div>
                    )
                  })}

                  {/* Dharana / Meditation slot */}
                  {session.dharana_section && (() => {
                    const dh = session.dharana_section
                    const dharanaOpen = expandedDharana.has(dayIdx)
                    return (
                      <div className="yoga-dharana-card">
                        <div className="yoga-dharana-header">
                          <Brain size={12} className="yoga-dharana-icon" />
                          <span className="yoga-dharana-name">
                            {dh.sanskrit_name || dh.technique}
                            {dh.sanskrit_name && dh.sanskrit_name !== dh.technique && (
                              <span className="yoga-dharana-sanskrit"> · {dh.technique}</span>
                            )}
                          </span>
                          {dh.duration_minutes && (
                            <span className="yoga-dharana-dur">{dh.duration_minutes} min</span>
                          )}
                        </div>
                        {dh.dosha_note && (
                          <p className="yoga-dharana-dosha-note">{dh.dosha_note}</p>
                        )}
                        {dh.instructions?.length > 0 && (
                          <>
                            <button className="yoga-pose-expand-toggle" onClick={() => toggleDharana(dayIdx)}>
                              {dharanaOpen ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
                              {dharanaOpen ? t('yoga.less', 'Less') : t('yoga.howToPractice', 'How to practice')}
                            </button>
                            {dharanaOpen && (
                              <>
                                <ol className="yoga-pose-instructions yoga-dharana-instructions">
                                  {dh.instructions.map((step, si) => <li key={si}>{step}</li>)}
                                </ol>
                                {dh.classical_reference && (
                                  <p className="yoga-dharana-ref">{dh.classical_reference}</p>
                                )}
                              </>
                            )}
                          </>
                        )}
                      </div>
                    )
                  })()}
                </>
              )}
            </div>
          )
        })}
      </div>

      {showFeedback && activeWeek === fourWeekPlan.length - 1 && (
        <WeekFeedbackCard
          plan={plan}
          week={latestWeek}
          nextWeek={nextWeek}
          onPlanUpdate={(updated) => {
            setLivePlan(updated)
            // Land the user on the week they just unlocked.
            setActiveWeek((updated.four_week_plan || []).length - 1)
            setExpandedDays(new Set())
          }}
        />
      )}

      {/* ── Ayurvedic Tips ── */}
      {Object.keys(tips).length > 0 && (
        <div className="yoga-tips-section">
          <h3 className="yoga-tips-title"><Leaf size={14} /> {t('yoga.tipsTitle', 'Ayurvedic Practice Tips')}</h3>
          <div className="yoga-tips-grid">
            {[
              { key: 'best_time', label: t('yoga.tip.bestTime', 'Best Time') },
              { key: 'environment', label: t('yoga.tip.environment', 'Environment') },
              { key: 'what_to_wear', label: t('yoga.tip.whatToWear', 'What to Wear') },
              { key: 'after_practice', label: t('yoga.tip.afterPractice', 'After Practice') },
            ].map(({ key, label }) => tips[key] ? (
              <div key={key} className="yoga-tip-card">
                <h4 className="yoga-tip-label">{label}</h4>
                <p className="yoga-tip-text">{tips[key]}</p>
              </div>
            ) : null)}
          </div>
          {tips.dosha_note && <p className="yoga-dosha-note">{tips.dosha_note}</p>}
        </div>
      )}

      {/* ── Enrichment cards ── */}
      {plan.breathing_guidance && (
        <div className="yoga-enrichment-card">
          <h3 className="yoga-enrichment-label"><Wind size={13} /> {t('yoga.breathingGuidance', 'Breathing Guidance')}</h3>
          <p className="yoga-enrichment-text">{plan.breathing_guidance}</p>
        </div>
      )}
      {plan.lifestyle_sync && (
        <div className="yoga-enrichment-card">
          <h3 className="yoga-enrichment-label"><Leaf size={13} /> {t('yoga.lifestyleSync', 'Lifestyle Sync')}</h3>
          <p className="yoga-enrichment-text">{plan.lifestyle_sync}</p>
        </div>
      )}
      {plan.motivational_note && (
        <div className="yoga-motivational">{plan.motivational_note}</div>
      )}

      {activeSession && (
        <SessionPlayer
          session={activeSession.session}
          planId={plan.plan_id}
          week={activeSession.week}
          day={activeSession.day}
          onClose={() => setActiveSession(null)}
        />
      )}
    </div>
  )
}

