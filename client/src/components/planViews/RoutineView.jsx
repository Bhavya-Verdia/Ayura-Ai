import React, { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Sun, PersonStanding, Dumbbell, Leaf, Sparkles, Star, Droplets, ShieldCheck, Flame, ArrowRight, Moon, Zap, Activity, ChevronDown, ChevronUp, Wind, Flower2, Brain, UtensilsCrossed, Clock, CupSoda, BookOpen, TriangleAlert, BadgeCheck,
} from 'lucide-react'
import { DOSHA_COLOR } from './shared'

const SLOT_COLORS = {
  morning_routine: { bg: 'rgba(251,191,36,0.12)',  border: 'rgba(251,191,36,0.35)',  dot: '#f59e0b', label: '#b45309' },
  self_care:       { bg: 'rgba(45,212,191,0.10)',  border: 'rgba(45,212,191,0.32)',  dot: '#2dd4bf', label: '#0f766e' },
  exercise:        { bg: 'rgba(74,222,128,0.10)',  border: 'rgba(74,222,128,0.30)',  dot: '#4ade80', label: '#15803d' },
  meal:            { bg: 'rgba(251,146,60,0.10)',  border: 'rgba(251,146,60,0.30)',  dot: '#fb923c', label: '#c2410c' },
  work:            { bg: 'rgba(148,163,184,0.08)', border: 'rgba(148,163,184,0.22)', dot: '#94a3b8', label: '#475569' },
  rest:            { bg: 'rgba(167,139,250,0.10)', border: 'rgba(167,139,250,0.28)', dot: '#a78bfa', label: '#7c3aed' },
  wind_down:       { bg: 'rgba(129,140,248,0.10)', border: 'rgba(129,140,248,0.28)', dot: '#818cf8', label: '#4338ca' },
  sleep:           { bg: 'rgba(30,27,75,0.08)',    border: 'rgba(99,102,241,0.22)',  dot: '#4f46e5', label: '#312e81' },
}

const SLOT_ICON_MAP = {
  sun: Sun, ritual: Sparkles, massage: Activity, yoga: Flower2, gym: Dumbbell,
  meal: UtensilsCrossed, work: BookOpen, rest: Moon, moon: Moon,
  milk: CupSoda, walk: PersonStanding, tea: Leaf, sleep: Moon,
  water: Droplets, tooth: Sparkles, tongue: Sparkles, nose: Wind,
  mouth: Sparkles, bath: Droplets, brush: Sparkles, eye: Sparkles,
  foot: Sparkles, head: Brain,
}

const RITUAL_ICON_MAP = {
  water: Droplets, tooth: Sparkles, tongue: Zap, nose: Wind,
  mouth: Activity, massage: Activity, bath: Droplets, brush: Zap,
  eye: Star, foot: Leaf, head: Brain, milk: CupSoda, tea: Leaf,
  walk: PersonStanding,
}


function RitualCard({ ritual, idx }) {
  const [open, setOpen] = useState(false)
  const Icon = RITUAL_ICON_MAP[ritual.icon] || Sparkles
  return (
    <motion.div
      className="din-ritual-card"
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: idx * 0.05 }}
    >
      <button className="din-ritual-header" onClick={() => setOpen(o => !o)}>
        <span className="din-ritual-icon"><Icon size={14} /></span>
        <span className="din-ritual-name">{ritual.name}</span>
        {ritual.duration_min && <span className="din-ritual-dur">{ritual.duration_min} min</span>}
        {open ? <ChevronUp size={13} className="din-ritual-chevron" /> : <ChevronDown size={13} className="din-ritual-chevron" />}
      </button>
      {open && <p className="din-ritual-body">{ritual.instruction}</p>}
    </motion.div>
  )
}


function TimelineSlot({ slot, idx }) {
  const [mealOpen, setMealOpen] = useState(false)
  const colors = SLOT_COLORS[slot.type] || SLOT_COLORS.work
  const Icon = SLOT_ICON_MAP[slot.icon] || Sparkles

  return (
    <motion.div
      className="din-slot"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: idx * 0.04 }}
      style={{ '--slot-bg': colors.bg, '--slot-border': colors.border }}
    >
      <div className="din-slot-time-col">
        <span className="din-slot-time">{slot.time}</span>
        <div className="din-slot-line" style={{ background: colors.dot }} />
      </div>
      <div className="din-slot-dot" style={{ background: colors.dot }} />
      <div className="din-slot-body" style={{ background: colors.bg, borderColor: colors.border }}>
        <div className="din-slot-top">
          <span className="din-slot-icon-wrap" style={{ color: colors.label }}><Icon size={13} /></span>
          <span className="din-slot-activity" style={{ color: colors.label }}>{slot.activity}</span>
          {slot.gym_focus && <span className="din-gym-focus-badge">{slot.gym_focus}</span>}
          {slot.type === 'meal' && (
            <button className="din-meal-toggle" onClick={() => setMealOpen(o => !o)}>
              {mealOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
          )}
        </div>
        {slot.description && <p className="din-slot-desc">{slot.description}</p>}
        {slot.condition_note && (
          <div className="din-slot-cond-note">
            <Zap size={11} />
            <span>{slot.condition_note}</span>
          </div>
        )}
        {slot.agni_note && (
          <div className="din-slot-agni-note">
            <Flame size={11} />
            <span>{slot.agni_note}</span>
          </div>
        )}
        {slot.occupation_note && (
          <div className="din-slot-occ-note">
            <BookOpen size={11} />
            <span>{slot.occupation_note}</span>
          </div>
        )}
        {mealOpen && slot.meal_type && (
          <div className="din-meal-expand">
            <span className="din-meal-tag">See your Diet Plan for today's {slot.meal_type} details.</span>
          </div>
        )}
      </div>
    </motion.div>
  )
}


function MealGuidancePanel({ guidance }) {
  const meals = ['breakfast', 'lunch', 'snack', 'dinner']
  const [active, setActive] = useState('lunch')
  const m = guidance[active] || {}
  return (
    <div className="din-meal-guide">
      <div className="din-meal-guide-tabs">
        {meals.map(k => (
          <button key={k} className={`din-mg-tab ${active === k ? 'active' : ''}`} onClick={() => setActive(k)}>
            {k.charAt(0).toUpperCase() + k.slice(1)}
          </button>
        ))}
      </div>
      {m.ideal_time && <div className="din-mg-time"><Clock size={11} /> {m.ideal_time}</div>}
      <div className="din-mg-cols">
        {m.favour?.length > 0 && (
          <div className="din-mg-col favour">
            <div className="din-mg-col-head"><BadgeCheck size={12} />Favour</div>
            <ul>{m.favour.map((f, i) => <li key={i}>{f}</li>)}</ul>
          </div>
        )}
        {m.avoid?.length > 0 && (
          <div className="din-mg-col avoid">
            <div className="din-mg-col-head"><TriangleAlert size={12} />Avoid</div>
            <ul>{m.avoid.map((f, i) => <li key={i}>{f}</li>)}</ul>
          </div>
        )}
      </div>
      {guidance.seasonal_note && (
        <div className="din-mg-season-note"><Sun size={11} />{guidance.seasonal_note}</div>
      )}
    </div>
  )
}


export function RoutineView({ plan }) {
  const [activeDay, setActiveDay] = useState(0)
  const din = plan.dinacharya_protocol || {}
  const seasonal = plan.seasonal_ritucharya || {}
  const mealGuide = plan.meal_guidance || {}
  const weeklyRoutine = plan.weekly_routine || []
  const currentDay = weeklyRoutine[activeDay] || {}
  const timeline = currentDay.timeline || []
  const dayLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
  const dosha = (plan.user_summary?.dominant_dosha || 'vata').toLowerCase()
  const DOSHA_COLOR = { vata: '#818cf8', pitta: '#fb923c', kapha: '#2dd4bf' }
  const dcolor = DOSHA_COLOR[dosha] || '#818cf8'

  return (
    <div className="din-root">
      {/* ── Key principle banner ── */}
      {din.key_principle && (
        <motion.div className="din-principle-banner" initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
          <Star size={13} style={{ color: dcolor, flexShrink: 0 }} />
          <span>{din.key_principle}</span>
        </motion.div>
      )}

      {/* ── Time anchors row ── */}
      <motion.div className="din-anchors" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }}>
        <div className="din-anchor">
          <Sun size={14} style={{ color: '#f59e0b' }} />
          <div><div className="din-anchor-label">Wake</div><div className="din-anchor-val">{din.wake_time}</div></div>
        </div>
        <div className="din-anchor-sep" />
        <div className="din-anchor">
          <Moon size={14} style={{ color: '#818cf8' }} />
          <div><div className="din-anchor-label">Sleep</div><div className="din-anchor-val">{din.sleep_time}</div></div>
        </div>
        <div className="din-anchor-sep" />
        <div className="din-anchor">
          <Flame size={14} style={{ color: '#fb923c' }} />
          <div>
            <div className="din-anchor-label">Agni</div>
            <div className="din-anchor-val" style={{ textTransform: 'capitalize' }}>
              {(din.agni_type || din.agni_level || '').replace(/_/g, ' ')}
            </div>
          </div>
        </div>
        {din.age_band && (
          <>
            <div className="din-anchor-sep" />
            <div className="din-anchor">
              <Star size={14} style={{ color: dcolor }} />
              <div><div className="din-anchor-label">Avastha</div><div className="din-anchor-val" style={{ textTransform: 'capitalize' }}>{din.age_band}</div></div>
            </div>
          </>
        )}
        {seasonal.season && (
          <>
            <div className="din-anchor-sep" />
            <div className="din-anchor">
              <Leaf size={14} style={{ color: '#4ade80' }} />
              <div><div className="din-anchor-label">Season</div><div className="din-anchor-val">{seasonal.season.split(' ')[0]}</div></div>
            </div>
          </>
        )}
      </motion.div>

      {/* ── Dual-dosha note ── */}
      {din.dual_dosha_note && (
        <motion.div className="din-dual-dosha-note" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.13 }}>
          <Sparkles size={12} style={{ color: dcolor, flexShrink: 0 }} />
          <span>{din.dual_dosha_note}</span>
        </motion.div>
      )}

      {/* ── Seasonal banner ── */}
      {din.season_practice_note && (
        <motion.div className="din-season-banner" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.12 }}>
          <Leaf size={12} />
          <span>{din.season_practice_note}</span>
        </motion.div>
      )}

      <div className="din-two-col">
        {/* ── Left: Daily timeline ── */}
        <div className="din-left">
          {/* Day tabs */}
          <div className="din-day-tabs">
            {dayLabels.map((d, i) => {
              const isFasting = weeklyRoutine[i]?.is_fasting_day
              const isRest    = weeklyRoutine[i]?.is_rest_day
              return (
                <button
                  key={i}
                  className={`din-day-tab ${activeDay === i ? 'active' : ''} ${isFasting ? 'fasting' : ''} ${isRest ? 'rest-day' : ''}`}
                  onClick={() => setActiveDay(i)}
                  style={activeDay === i ? { '--tab-color': dcolor } : {}}
                >
                  {d}
                  {isFasting && <span className="din-fast-dot" />}
                </button>
              )
            })}
          </div>

          {/* Day exercise header */}
          {currentDay.exercise_label && (
            <div className="din-day-ex-label">
              <Dumbbell size={12} style={{ color: dcolor }} />
              <span>{currentDay.exercise_label}</span>
              {currentDay.is_rest_day && <span className="din-rest-badge">Rest</span>}
              {currentDay.is_fasting_day && <span className="din-fast-badge">Fasting</span>}
            </div>
          )}

          {/* Timeline */}
          <div className="din-timeline">
            {timeline.map((slot, i) => (
              <TimelineSlot key={i} slot={slot} idx={i} />
            ))}
          </div>
        </div>

        {/* ── Right: Dinacharya protocol ── */}
        <div className="din-right">
          {/* Morning rituals */}
          <div className="din-panel">
            <div className="din-panel-head"><Sun size={14} style={{ color: '#f59e0b' }} />Morning Protocol</div>
            <div className="din-ritual-list">
              {(din.morning_rituals || []).map((r, i) => <RitualCard key={i} ritual={r} idx={i} />)}
            </div>
          </div>

          {/* Evening rituals */}
          {(din.evening_rituals || []).length > 0 && (
            <div className="din-panel" style={{ marginTop: 16 }}>
              <div className="din-panel-head"><Moon size={14} style={{ color: '#818cf8' }} />Evening Wind-Down</div>
              <div className="din-ritual-list">
                {(din.evening_rituals || []).map((r, i) => <RitualCard key={i} ritual={r} idx={i} />)}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Meal Guidance ── */}
      {Object.keys(mealGuide).length > 0 && (
        <motion.div className="din-section" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <div className="din-section-head"><UtensilsCrossed size={14} />Dosha Meal Guidance</div>
          {mealGuide.general && <p className="din-section-body">{mealGuide.general}</p>}
          <MealGuidancePanel guidance={mealGuide} />
        </motion.div>
      )}

      {/* ── Seasonal Ritucharya ── */}
      {seasonal.season && (
        <motion.div className="din-section" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
          <div className="din-section-head"><Leaf size={14} />Seasonal Ritucharya — {seasonal.season}</div>
          <div className="din-seasonal-cols">
            {seasonal.recommended_foods?.length > 0 && (
              <div className="din-seas-col">
                <div className="din-seas-col-head favour"><BadgeCheck size={11} />Recommended Foods</div>
                <ul>{seasonal.recommended_foods.map((f, i) => <li key={i}>{f}</li>)}</ul>
              </div>
            )}
            {seasonal.foods_to_avoid?.length > 0 && (
              <div className="din-seas-col">
                <div className="din-seas-col-head avoid"><TriangleAlert size={11} />Avoid This Season</div>
                <ul>{seasonal.foods_to_avoid.map((f, i) => <li key={i}>{f}</li>)}</ul>
              </div>
            )}
          </div>
          {seasonal.seasonal_practices?.length > 0 && (
            <div className="din-seas-practices">
              <div className="din-seas-col-head" style={{ marginBottom: 8 }}><Sparkles size={11} />Seasonal Practices</div>
              <div className="din-seas-practice-grid">
                {seasonal.seasonal_practices.map((p, i) => (
                  <div key={i} className="din-seas-practice-chip"><ArrowRight size={10} />{p}</div>
                ))}
              </div>
            </div>
          )}
        </motion.div>
      )}

      {plan.disclaimer && (
        <div className="rv-disclaimer" style={{ marginTop: 20 }}>
          <ShieldCheck size={12} /><span>{plan.disclaimer}</span>
        </div>
      )}
    </div>
  )
}

// ── Classical basis — governing texts per plan type (BAMS credibility) ──
