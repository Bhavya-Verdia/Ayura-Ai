import React, { useState } from 'react'
import {
  Sun, Leaf, AlertTriangle, Droplets, ShieldCheck, Flame, Moon, Timer, Zap, Target, Activity, ChevronDown, ChevronUp, Wind, Flower2, Brain,
} from 'lucide-react'
import { DOSHA_COLOR } from './shared'

const SNS_BREATH_COLOR = { 'Inhale': '#3b82f6', 'Exhale': '#ef4444', 'Natural': '#6b7280', 'Exhale — hold 3-5 breaths': '#ef4444' }


function SuryaNamaskarCard({ sns }) {
  const [open, setOpen] = useState(false)
  const pace = (sns.pace || '').replace(/\b\w/g, c => c.toUpperCase())
  return (
    <div className="sns-card">
      <div className="sns-header">
        <div className="sns-title-row">
          <Sun size={14} className="sns-sun-icon" />
          <span className="sns-title">Surya Namaskar</span>
          <span className="sns-sanskrit">सूर्य नमस्कार</span>
        </div>
        <div className="sns-meta">
          <span className="sns-badge">{sns.rounds} round{sns.rounds > 1 ? 's' : ''}</span>
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
        {open ? 'Hide 12 steps' : 'Show 12 steps'}
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


export function YogaView({ plan }) {
  const [activeWeek, setActiveWeek] = useState(0)
  const [expandedPoses, setExpandedPoses] = useState(new Set())
  const [expandedWarmup, setExpandedWarmup] = useState(new Set())
  const [expandedCooldown, setExpandedCooldown] = useState(new Set())
  const [expandedPrana, setExpandedPrana] = useState(new Set())
  const [expandedDharana, setExpandedDharana] = useState(new Set())

  const us = plan.user_summary || {}
  const fourWeekPlan = plan.four_week_plan || []
  const activeWeekData = fourWeekPlan[activeWeek] || null
  const weekDays = activeWeekData?.days || []
  const weekNote = activeWeekData?.note || null
  const tips = plan.ayurvedic_tips || {}
  const dailyIntention = plan.daily_intention || {}

  const doshaColor = DOSHA_COLOR[us.dominant_dosha] || DOSHA_COLOR.default
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
  const togglePrana = (dayIdx) => setExpandedPrana(prev => {
    const next = new Set(prev); next.has(dayIdx) ? next.delete(dayIdx) : next.add(dayIdx); return next
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
            {us.age_group === 'senior' ? <><Leaf size={14} strokeWidth={2} /> Senior-Adapted Practice</> : <><Zap size={14} strokeWidth={2} /> Youth Practice</>}
          </div>
        )}
        {us.medical_conditions?.length > 0 && (
          <div className="yoga-medical-banner">
            <span className="yoga-medical-label">Personalised for:</span>
            {us.medical_conditions.map(c => (
              <span key={c} className="yoga-medical-chip">{c.replace(/_/g, ' ')}</span>
            ))}
          </div>
        )}
      </div>

      {/* ── Pranayama safety exclusions (forceful breaths removed for safety) ── */}
      {plan.pranayama_safety_exclusions?.length > 0 && (
        <div className="yoga-prana-exclusions">
          <div className="yoga-prana-excl-title">
            <ShieldCheck size={13} /> Excluded for your safety
          </div>
          <ul className="yoga-prana-excl-list">
            {plan.pranayama_safety_exclusions.map((ex, i) => (
              <li key={i}><strong>{ex.name}</strong> — {ex.reason}</li>
            ))}
          </ul>
        </div>
      )}

      {/* ── Seasonal note ── */}
      {plan.seasonal_note && (
        <div className="yoga-seasonal-note">
          <Leaf size={12} />
          <span>{plan.seasonal_note}</span>
        </div>
      )}

      {/* ── Vitals bar ── */}
      <div className="yoga-vitals">
        {goalLabel && (
          <div className="yoga-vital-chip">
            <Target size={11} /><span className="yoga-vital-k">Goal</span><span className="yoga-vital-v">{goalLabel}</span>
          </div>
        )}
        {us.dominant_dosha && (
          <div className="yoga-vital-chip" style={{ borderColor: `${doshaColor}44`, color: doshaColor }}>
            <span className="yoga-vital-k">Dosha</span><span className="yoga-vital-v">{us.dominant_dosha.toUpperCase()}</span>
          </div>
        )}
        {us.experience && (
          <div className="yoga-vital-chip">
            <Activity size={11} /><span className="yoga-vital-k">Level</span>
            <span className="yoga-vital-v">{us.experience.replace(/\b\w/g, c => c.toUpperCase())}</span>
          </div>
        )}
        {styleLabel && (
          <div className="yoga-vital-chip">
            <Flower2 size={11} /><span className="yoga-vital-k">Style</span><span className="yoga-vital-v">{styleLabel}</span>
          </div>
        )}
        {us.time_available && (
          <div className="yoga-vital-chip">
            <Timer size={11} /><span className="yoga-vital-k">Duration</span><span className="yoga-vital-v">{us.time_available} min</span>
          </div>
        )}
        {us.time_of_day && (
          <div className="yoga-vital-chip">
            <Sun size={11} /><span className="yoga-vital-k">Time</span>
            <span className="yoga-vital-v">{us.time_of_day.replace(/\b\w/g, c => c.toUpperCase())}</span>
          </div>
        )}
        {us.agni_type && (
          <div className="yoga-vital-chip yoga-vital-agni">
            <Flame size={11} /><span className="yoga-vital-k">Agni</span>
            <span className="yoga-vital-v">{us.agni_type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</span>
          </div>
        )}
        {us.ojas_level && (
          <div className="yoga-vital-chip yoga-vital-ojas">
            <Droplets size={11} /><span className="yoga-vital-k">Ojas</span>
            <span className="yoga-vital-v">{us.ojas_level.replace(/\b\w/g, c => c.toUpperCase())}</span>
          </div>
        )}
        {us.stress_level && us.stress_level !== 'low' && (
          <div className="yoga-vital-chip yoga-vital-stress">
            <Zap size={11} /><span className="yoga-vital-k">Stress</span>
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
        {YOGA_WEEK_THEMES.map((theme, i) => (
          <button
            key={i}
            className={`yoga-week-tab${activeWeek === i ? ' active' : ''}`}
            onClick={() => setActiveWeek(i)}
          >
            <span className="yoga-tab-num">Week {i + 1}</span>
            <span className="yoga-tab-theme">{theme}</span>
          </button>
        ))}
      </div>

      {/* ── Week note banner ── */}
      {weekNote && (
        <div className="yoga-week-banner">
          <span className="yoga-week-banner-icon"><Leaf size={16} strokeWidth={2} /></span>
          <span className="yoga-week-banner-text">
            <strong>Week {activeWeek + 1} · {YOGA_WEEK_THEMES[activeWeek]}:</strong> {weekNote}
          </span>
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

          return (
            <div key={dayIdx} className={`yoga-day-card${isRest ? ' rest' : ''}`}>
              <div className="yoga-day-header">
                <div className="yoga-day-name">
                  {isRest ? <Moon size={13} /> : <Flower2 size={13} />}
                  {day.day_name || `Day ${day.day}`}
                </div>
                {!isRest && session.total_duration_minutes && (
                  <span className="yoga-duration-badge-sm">{session.total_duration_minutes} min</span>
                )}
              </div>

              {isRest ? (
                <div className="yoga-rest-card">
                  <p className="yoga-rest-tip">Let your body absorb the week's practice. Gentle movement and stillness are welcome.</p>
                </div>
              ) : (
                <>
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
                        <span className="yoga-section-label">Warmup ({session.warmup.length})</span>
                        {warmupOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                      </button>
                      {warmupOpen && (
                        <ul className="yoga-pose-list">
                          {session.warmup.map((p, pi) => (
                            <li key={pi} className="yoga-warmup-pose">
                              <span className="yoga-wp-name">{p.pose_name}</span>
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
                      <div className="yoga-section-label standalone">Main Practice ({session.main_sequence.length} poses)</div>
                      <div className="yoga-main-list">
                        {session.main_sequence.map((p, pi) => {
                          const poseId = `${dayIdx}-main-${pi}`
                          const isOpen = expandedPoses.has(poseId)
                          const hasValidImg = p.image_url && !p.image_url.startsWith('https://...')
                          return (
                            <div key={pi} className="yoga-pose-row">
                              <div className="yoga-pose-top">
                                <div className="yoga-pose-name-block">
                                  <span className="yoga-pose-name">{p.pose_name}</span>
                                  {p.sanskrit_name && (
                                    <span className="yoga-pose-sanskrit">{p.sanskrit_name}</span>
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
                                    {isOpen ? 'Less' : 'Details'}
                                  </button>
                                  {isOpen && (
                                    <div className="yoga-pose-expand">
                                      {hasValidImg && (
                                        <img src={p.image_url} alt={p.pose_name} className="yoga-pose-image" />
                                      )}
                                      {p.instructions?.length > 0 && (
                                        <ol className="yoga-pose-instructions">
                                          {p.instructions.map((step, si) => <li key={si}>{step}</li>)}
                                        </ol>
                                      )}
                                      {p.modification && (
                                        <p className="yoga-pose-modification">Modification: {p.modification}</p>
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
                        <span className="yoga-section-label">Cooldown ({session.cooldown.length})</span>
                        {cooldownOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                      </button>
                      {cooldownOpen && (
                        <ul className="yoga-pose-list">
                          {session.cooldown.map((p, pi) => (
                            <li key={pi} className="yoga-warmup-pose">
                              <span className="yoga-wp-name">{p.pose_name}</span>
                              {p.duration_seconds && <span className="yoga-wp-dur">{p.duration_seconds}s</span>}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}

                  {/* Pranayama */}
                  {session.pranayama_section?.length > 0 && (() => {
                    const pr = session.pranayama_section[0]
                    const pranaOpen = expandedPrana.has(dayIdx)
                    const hasInstructions = pr.instructions?.length > 0
                    return (
                      <div className="yoga-prana-card">
                        <div className="yoga-prana-header">
                          <Wind size={12} className="yoga-prana-icon" />
                          <span className="yoga-prana-name">
                            {pr.technique_name}
                            {pr.sanskrit_name && (
                              <span className="yoga-prana-sanskrit"> · {pr.sanskrit_name}</span>
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
                            <button className="yoga-pose-expand-toggle" onClick={() => togglePrana(dayIdx)}>
                              {pranaOpen ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
                              {pranaOpen ? 'Less' : 'Instructions'}
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
                  })()}

                  {/* Dharana / Meditation slot */}
                  {session.dharana_section && (() => {
                    const dh = session.dharana_section
                    const dharanaOpen = expandedDharana.has(dayIdx)
                    return (
                      <div className="yoga-dharana-card">
                        <div className="yoga-dharana-header">
                          <Brain size={12} className="yoga-dharana-icon" />
                          <span className="yoga-dharana-name">
                            {dh.technique}
                            {dh.sanskrit_name && (
                              <span className="yoga-dharana-sanskrit"> · {dh.sanskrit_name}</span>
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
                              {dharanaOpen ? 'Less' : 'How to practice'}
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

      {/* ── Ayurvedic Tips ── */}
      {Object.keys(tips).length > 0 && (
        <div className="yoga-tips-section">
          <div className="yoga-tips-title"><Leaf size={14} /> Ayurvedic Practice Tips</div>
          <div className="yoga-tips-grid">
            {[
              { key: 'best_time', label: 'Best Time' },
              { key: 'environment', label: 'Environment' },
              { key: 'what_to_wear', label: 'What to Wear' },
              { key: 'after_practice', label: 'After Practice' },
            ].map(({ key, label }) => tips[key] ? (
              <div key={key} className="yoga-tip-card">
                <div className="yoga-tip-label">{label}</div>
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
          <div className="yoga-enrichment-label"><Wind size={13} /> Breathing Guidance</div>
          <p className="yoga-enrichment-text">{plan.breathing_guidance}</p>
        </div>
      )}
      {plan.lifestyle_sync && (
        <div className="yoga-enrichment-card">
          <div className="yoga-enrichment-label"><Leaf size={13} /> Lifestyle Sync</div>
          <p className="yoga-enrichment-text">{plan.lifestyle_sync}</p>
        </div>
      )}
      {plan.motivational_note && (
        <div className="yoga-motivational">{plan.motivational_note}</div>
      )}
    </div>
  )
}

