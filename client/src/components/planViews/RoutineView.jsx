import React, { useState } from 'react'
import { m } from 'framer-motion'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { plansAPI } from '../../api/client'
import {
  Sun, PersonStanding, Pencil, RotateCcw, Plus, Trash2, Dumbbell, Leaf, Sparkles, Star, Droplets, ShieldCheck, Flame, ArrowRight, Moon, Zap, Activity, ChevronDown, ChevronUp, Wind, Flower2, Brain, UtensilsCrossed, Clock, CupSoda, BookOpen, TriangleAlert, BadgeCheck,
} from 'lucide-react'
import { DOSHA_COLOR, doshaInk } from '../../constants/dosha'
import RoutinePdfButtons from '../RoutinePdfButtons'

// Earthy day-part palette — warm gold → herbal greens → terracotta → cool
// evening/night tones, each hue distinct so adjacent timeline slots read apart.
// bg/border/dot are translucent tints that work on either theme, so they stay
// inline. The label ink does NOT: every value here used to be a dark-on-light
// one (#312e81 measured 1.68:1 on the dark theme, which is the default), so the
// activity names are themed in CSS via [data-slot] instead — see .din-slot.
const SLOT_COLORS = {
  morning_routine: { bg: 'rgba(224,165,60,0.12)',  border: 'rgba(224,165,60,0.35)',  dot: '#e0a53c' },
  self_care:       { bg: 'rgba(79,174,143,0.10)',  border: 'rgba(79,174,143,0.30)',  dot: '#4fae8f' },
  exercise:        { bg: 'rgba(92,171,116,0.10)',  border: 'rgba(92,171,116,0.30)',  dot: '#5cab74' },
  meal:            { bg: 'rgba(224,138,74,0.10)',  border: 'rgba(224,138,74,0.30)',  dot: '#e08a4a' },
  work:            { bg: 'rgba(168,157,139,0.10)', border: 'rgba(168,157,139,0.26)', dot: '#a89d8b' },
  rest:            { bg: 'rgba(160,140,240,0.10)', border: 'rgba(160,140,240,0.28)', dot: '#a08cf0' },
  wind_down:       { bg: 'rgba(139,143,224,0.10)', border: 'rgba(139,143,224,0.28)', dot: '#8b8fe0' },
  sleep:           { bg: 'rgba(30,27,75,0.08)',    border: 'rgba(99,102,241,0.22)',  dot: '#4f46e5' },
  // What the user added themselves — its own hue, so it reads apart from the plan.
  custom:          { bg: 'rgba(96,165,250,0.10)',  border: 'rgba(96,165,250,0.32)',  dot: '#60a5fa' },
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
    <m.div
      className={`din-ritual-card${ritual.withheld ? ' withheld' : ''}`}
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: idx * 0.05 }}
    >
      <button className="din-ritual-header" onClick={() => setOpen(o => !o)}>
        <span className="din-ritual-icon"><Icon size={14} /></span>
        <span className="din-ritual-name">{ritual.name}</span>
        {/* A withheld ritual carries duration 0, which `0 &&` rendered as a bare "0". */}
        {ritual.withheld
          ? <span className="din-ritual-dur">Skipped</span>
          : ritual.duration_min > 0 && <span className="din-ritual-dur">{ritual.duration_min} min</span>}
        {open ? <ChevronUp size={13} className="din-ritual-chevron" /> : <ChevronDown size={13} className="din-ritual-chevron" />}
      </button>
      {open && <p className="din-ritual-body">{ritual.instruction}</p>}
    </m.div>
  )
}


// The routine is the user's to fit around their life. These cannot be left out:
// the day's anchors, and the two main meals.
const UNSKIPPABLE = new Set(['wake', 'sleep', 'lunch', 'dinner'])

// "7:05 PM" -> "19:05", for <input type="time">.
function to24h(label) {
  const match = /^(\d{1,2}):(\d{2})\s*(AM|PM)$/i.exec(label || '')
  if (!match) return ''
  const h = (Number(match[1]) % 12) + (match[3].toUpperCase() === 'PM' ? 12 : 0)
  return `${String(h).padStart(2, '0')}:${match[2]}`
}

function SlotTimeEditor({ slot, dayName, onSave, onCancel, busy }) {
  const [time, setTime] = useState(to24h(slot.time))
  const [scope, setScope] = useState('every')
  const day = scope === 'day' ? dayName.toLowerCase() : null
  return (
    <div className="din-time-editor" role="group" aria-label={`Change time for ${slot.activity}`}>
      <div className="din-time-editor-row">
        <input
          type="time"
          value={time}
          onChange={e => setTime(e.target.value)}
          aria-label="New time"
          autoFocus
        />
        <div className="din-time-scope" role="radiogroup" aria-label="Apply to">
          <button type="button" role="radio" aria-checked={scope === 'every'}
            className={scope === 'every' ? 'active' : ''} onClick={() => setScope('every')}>Every day</button>
          <button type="button" role="radio" aria-checked={scope === 'day'}
            className={scope === 'day' ? 'active' : ''} onClick={() => setScope('day')}>Only {dayName}</button>
        </div>
      </div>
      <div className="din-time-editor-actions">
        <button type="button" className="din-time-save" disabled={busy || !time}
          onClick={() => onSave({ slot_id: slot.id, time, day })}>Save</button>
        {!UNSKIPPABLE.has(slot.id) && (
          <button type="button" disabled={busy}
            onClick={() => onSave({ slot_id: slot.id, time: 'off', day })}>Leave out</button>
        )}
        {slot.user_set && (
          <button type="button" disabled={busy}
            onClick={() => onSave({ slot_id: slot.id, time: null, day })}>Suggested time</button>
        )}
        <button type="button" disabled={busy} onClick={onCancel}>Cancel</button>
      </div>
    </div>
  )
}

const ITEM_CATEGORIES = [
  ['activity', 'Activity'], ['work', 'Work / study'], ['exercise', 'Exercise'],
  ['meal', 'Meal'], ['self_care', 'Self-care'], ['rest', 'Rest'],
]
const WEEK = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

// Add or edit something of the user's own: a commute, school pickup, a class.
function ItemEditor({ item, onSubmit, onDelete, onCancel, busy }) {
  const [form, setForm] = useState({
    title: item?.activity || '',
    time: item ? to24h(item.time) : '',
    duration_minutes: item?.duration_minutes || 30,
    category: item?.category || 'activity',
    days: item?.days || [],
    note: item?.description || '',
  })
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))
  const toggleDay = d => set('days', form.days.includes(d) ? form.days.filter(x => x !== d) : [...form.days, d])
  const valid = form.title.trim() && form.time && form.duration_minutes >= 5
  return (
    <form
      className="din-time-editor din-item-editor"
      onSubmit={e => { e.preventDefault(); if (valid) onSubmit({ ...form, title: form.title.trim(), duration_minutes: Number(form.duration_minutes) }) }}
    >
      <label className="din-item-field din-item-wide">
        <span>What</span>
        <input type="text" maxLength={60} value={form.title} onChange={e => set('title', e.target.value)}
          placeholder="e.g. Commute, School pickup, Guitar class" autoFocus />
      </label>
      <div className="din-time-editor-row">
        <label className="din-item-field">
          <span>Start</span>
          <input type="time" value={form.time} onChange={e => set('time', e.target.value)} />
        </label>
        <label className="din-item-field">
          <span>Minutes</span>
          <input type="number" min={5} max={600} step={5} value={form.duration_minutes}
            onChange={e => set('duration_minutes', e.target.value)} />
        </label>
        <label className="din-item-field">
          <span>Kind</span>
          <select value={form.category} onChange={e => set('category', e.target.value)}>
            {ITEM_CATEGORIES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </label>
      </div>
      <div className="din-item-days" role="group" aria-label="Days">
        <button type="button" aria-pressed={form.days.length === 0}
          className={form.days.length === 0 ? 'active' : ''} onClick={() => set('days', [])}>Every day</button>
        {WEEK.map(d => (
          <button key={d} type="button" aria-pressed={form.days.includes(d)}
            className={form.days.includes(d) ? 'active' : ''} onClick={() => toggleDay(d)}>
            {d.slice(0, 3).replace(/^./, c => c.toUpperCase())}
          </button>
        ))}
      </div>
      <label className="din-item-field din-item-wide">
        <span>Note (optional)</span>
        <input type="text" maxLength={200} value={form.note} onChange={e => set('note', e.target.value)} />
      </label>
      <div className="din-time-editor-actions">
        <button type="submit" className="din-time-save" disabled={busy || !valid}>{item ? 'Save' : 'Add'}</button>
        {onDelete && (
          <button type="button" disabled={busy} onClick={onDelete}><Trash2 size={11} aria-hidden="true" />Remove</button>
        )}
        <button type="button" disabled={busy} onClick={onCancel}>Cancel</button>
      </div>
    </form>
  )
}

function TimelineSlot({ slot, idx, dayName, onSave, onItem, busy }) {
  const [mealOpen, setMealOpen] = useState(false)
  const [editing, setEditing] = useState(false)
  const slotType = SLOT_COLORS[slot.type] ? slot.type : 'work'
  const colors = SLOT_COLORS[slotType]
  const Icon = SLOT_ICON_MAP[slot.icon] || Sparkles

  return (
    <m.div
      className="din-slot"
      data-slot={slotType}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: idx * 0.04 }}
      style={{ '--slot-bg': colors.bg, '--slot-border': colors.border }}
    >
      <div className="din-slot-time-col">
        {slot.id && onSave ? (
          <button
            type="button"
            className={`din-slot-time din-slot-time-btn${slot.user_set ? ' user-set' : ''}`}
            onClick={() => setEditing(e => !e)}
            aria-expanded={editing}
            aria-label={`${slot.time}, ${slot.activity}. ${slot.custom ? 'Edit' : 'Change time'}`}
          >
            {slot.time}<Pencil size={10} aria-hidden="true" />
          </button>
        ) : (
          <span className="din-slot-time">{slot.time}</span>
        )}
        <div className="din-slot-line" style={{ background: colors.dot }} />
      </div>
      <div className="din-slot-dot" style={{ background: colors.dot }} />
      <div className="din-slot-body" style={{ background: colors.bg, borderColor: colors.border }}>
        <div className="din-slot-top">
          <span className="din-slot-icon-wrap"><Icon size={13} /></span>
          <span className="din-slot-activity">{slot.activity}</span>
          {slot.gym_focus && <span className="din-gym-focus-badge">{slot.gym_focus}</span>}
          {slot.custom
            ? <span className="din-user-set-badge">Added by you</span>
            : slot.user_set && <span className="din-user-set-badge">Your time</span>}
          {slot.type === 'meal' && (
            <button className="din-meal-toggle" onClick={() => setMealOpen(o => !o)}>
              {mealOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
          )}
        </div>
        {slot.description && <p className="din-slot-desc">{slot.description}</p>}
        {(slot.schedule_notes || []).map((note, i) => (
          <div key={`s${i}`} className="din-slot-cond-note din-slot-sched-note">
            <Clock size={11} />
            <span>{note}</span>
          </div>
        ))}
        {editing && slot.custom && onItem && (
          <ItemEditor
            item={slot}
            busy={busy}
            onCancel={() => setEditing(false)}
            onSubmit={async body => { if (await onItem('update', slot.id, body)) setEditing(false) }}
            onDelete={async () => { if (await onItem('delete', slot.id)) setEditing(false) }}
          />
        )}
        {editing && !slot.custom && (
          <SlotTimeEditor
            slot={slot}
            dayName={dayName}
            busy={busy}
            onCancel={() => setEditing(false)}
            onSave={async body => { if (await onSave(body)) setEditing(false) }}
          />
        )}
        {(slot.condition_notes || (slot.condition_note ? [slot.condition_note] : [])).map((note, i) => (
          <div key={i} className="din-slot-cond-note">
            <Zap size={11} />
            <span>{note}</span>
          </div>
        ))}
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
    </m.div>
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
            <h4 className="din-mg-col-head"><BadgeCheck size={12} />Favour</h4>
            <ul>{m.favour.map((f, i) => <li key={i}>{f}</li>)}</ul>
          </div>
        )}
        {m.avoid?.length > 0 && (
          <div className="din-mg-col avoid">
            <h4 className="din-mg-col-head"><TriangleAlert size={12} />Avoid</h4>
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


export function RoutineView({ plan: initialPlan }) {
  const [activeDay, setActiveDay] = useState(0)
  // A time edit returns the rebuilt routine; it replaces this one here and in the
  // dashboard's cache, so going back and reopening shows the same day.
  const [plan, setPlan] = useState(initialPlan)
  const [saving, setSaving] = useState(false)
  const queryClient = useQueryClient()
  const [adding, setAdding] = useState(false)
  const saveItem = (action, id, body) => apply(
    action === 'add' ? plansAPI.addRoutineItem(body)
      : action === 'update' ? plansAPI.updateRoutineItem(id, body)
        : plansAPI.deleteRoutineItem(id),
    'Could not save that. Try again.')
  const saveTime = (body) => apply(plansAPI.setRoutineTime(body), 'Could not change that time. Try again.')
  const apply = async (request, failure) => {
    setSaving(true)
    try {
      const res = await request
      setPlan(res.data)
      queryClient.setQueryData(['plans-history'], old => old ? ({
        ...old, routine: { ...(old.routine || {}), data: res.data },
      }) : old)
      return true
    } catch (err) {
      const detail = err.response?.data?.detail
      toast.error(typeof detail === 'string' ? detail : failure)
      return false
    } finally {
      setSaving(false)
    }
  }
  const hasCustomTimes = Object.keys(plan.custom_times || {}).length > 0
    || Object.keys(plan.custom_times_by_day || {}).length > 0
  const din = plan.dinacharya_protocol || {}
  const seasonal = plan.seasonal_ritucharya || {}
  const mealGuide = plan.meal_guidance || {}
  const weeklyRoutine = plan.weekly_routine || []
  const currentDay = weeklyRoutine[activeDay] || {}
  const timeline = currentDay.timeline || []
  const dayLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
  const dosha = (plan.user_summary?.dominant_dosha || 'vata').toLowerCase()
  const dcolor = DOSHA_COLOR[dosha] || DOSHA_COLOR.default
  // Theme-flipping ink for anything that renders as text (the active day tab
  // sat at 2.15:1 in light mode with the dark-theme dosha hex).
  const dtext = doshaInk(dosha)

  const limits = plan.exercise_limits
  const adjustments = [
    ...(din.pregnancy_notices || []).map(n => ({ why: n })),
    ...(limits?.reasons?.length
      ? [{ what: 'Exercise', why: `kept ${limits.cap === 'gentle' ? 'gentle' : 'to a pace you can talk through'}${limits.low_impact ? ' and low impact' : ''}, because of ${limits.reasons.join(' and ')}.` }]
      : limits?.low_impact ? [{ what: 'Exercise', why: 'kept low impact — no running or jumping.' }] : []),
    ...(din.withheld_practices || []).map(w => ({ what: w.practice, why: w.reason })),
    ...(seasonal.withheld || []).map(w => ({ what: w.item, why: w.reason })),
    ...(mealGuide.withheld || []).map(w => ({ what: w.item, why: w.reason })),
  ]
  // A day with no gym or yoga slot reads the same whether the plan was left out
  // or never made, so the second case says what to do.
  const linked = plan.linked_plans || {}
  const missingPlans = ['gym', 'yoga'].filter(k => linked[k] === 'none')
  const linkNotice = missingPlans.length
    ? `You have no ${missingPlans.join(' or ')} plan yet. Create one and regenerate this routine, and its sessions will be placed in your day.`
    : null
  const coaching = [plan.plan_description, plan.dosha_coaching, plan.agni_coaching, plan.sleep_coaching,
    plan.seasonal_rationale, plan.integration_note, plan.motivational_note].filter(c => typeof c === 'string' && c.trim())

  return (
    <div className="din-root">
      <RoutinePdfButtons />
      {/* ── Key principle banner ── */}
      {din.key_principle && (
        <m.div className="din-principle-banner" initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
          <Star size={13} style={{ color: dcolor, flexShrink: 0 }} />
          <span>{din.key_principle}</span>
        </m.div>
      )}

      {/* A later wake is honoured — the classical hour is an ideal, the user's life
          is a fact — but it costs the pre-dawn window the morning practices are built
          around, and the plan says so rather than quietly moving the time. */}
      {din.wake_notice && (
        <div className="din-wake-notice">
          <TriangleAlert size={12} />
          <span>{din.wake_notice}</span>
        </div>
      )}

      {[din.sleep_notice, plan.fasting_notice, linkNotice].filter(Boolean).map((n, i) => (
        <div key={i} className="din-wake-notice">
          <TriangleAlert size={12} />
          <span>{n}</span>
        </div>
      ))}

      {/* What this routine changed or left out for this person, in one place. The
          engine withheld herbs, rituals and foods and capped exercise, and the
          screen said none of it — a missing practice and a forgotten one look
          identical otherwise. */}
      {adjustments.length > 0 && (
        <div className="gym-condition-guidance din-adjustments">
          <h4><ShieldCheck size={13} />Adjusted for you</h4>
          <ul>
            {adjustments.map((a, i) => (
              <li key={i}>{a.what && <strong>{a.what}: </strong>}{a.why}</li>
            ))}
          </ul>
        </div>
      )}

      {/* ── Time anchors row ── */}
      <m.div className="din-anchors" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }}>
        <div className="din-anchor">
          <Sun size={14} style={{ color: '#f59e0b' }} />
          <div><div className="din-anchor-label">Wake</div><div className="din-anchor-val">{din.wake_time}</div></div>
        </div>
        <div className="din-anchor-sep" />
        <div className="din-anchor">
          <Moon size={14} style={{ color: '#a08cf0' }} />
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
            {din.agni_source && din.agni_source !== 'default' && (
              <div className="din-anchor-label">from {din.agni_source}</div>
            )}
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
      </m.div>

      {/* ── Dual-dosha note ── */}
      {din.dual_dosha_note && (
        <m.div className="din-dual-dosha-note" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.13 }}>
          <Sparkles size={12} style={{ color: dcolor, flexShrink: 0 }} />
          <span>{din.dual_dosha_note}</span>
        </m.div>
      )}

      {/* ── Seasonal banner ── */}
      {din.season_practice_note && (
        <m.div className="din-season-banner" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.12 }}>
          <Leaf size={12} />
          <span>{din.season_practice_note}</span>
        </m.div>
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
                  style={activeDay === i ? { '--tab-color': dtext } : {}}
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
          {plan.weekly_theme?.[currentDay.day_name] && (
            <p className="din-day-theme">{plan.weekly_theme[currentDay.day_name]}</p>
          )}

          <div className="din-edit-hint">
            <span>Tap a time to change it to fit your day.</span>
            <button type="button" disabled={saving} onClick={() => setAdding(a => !a)} aria-expanded={adding}>
              <Plus size={11} aria-hidden="true" />Add to my routine
            </button>
            {hasCustomTimes && (
              <button type="button" disabled={saving} onClick={() => saveTime({ reset_all: true })}>
                <RotateCcw size={11} aria-hidden="true" />Reset all my times
              </button>
            )}
          </div>
          {adding && (
            <ItemEditor
              busy={saving}
              onCancel={() => setAdding(false)}
              onSubmit={async body => { if (await saveItem('add', null, body)) setAdding(false) }}
            />
          )}
          {currentDay.sleep_notice && (
            <div className="din-wake-notice">
              <TriangleAlert size={12} />
              <span>{currentDay.sleep_notice}</span>
            </div>
          )}

          {/* Timeline */}
          <div className="din-timeline">
            {timeline.map((slot, i) => (
              <TimelineSlot key={`${slot.id || i}-${slot.time}`} slot={slot} idx={i}
                dayName={currentDay.day_name || dayLabels[activeDay]} onSave={saveTime} onItem={saveItem} busy={saving} />
            ))}
          </div>
        </div>

        {/* ── Right: Dinacharya protocol ── */}
        <div className="din-right">
          {/* Morning rituals */}
          <div className="din-panel">
            <h3 className="din-panel-head"><Sun size={14} style={{ color: '#f59e0b' }} />Morning Protocol</h3>
            <div className="din-ritual-list">
              {(din.morning_rituals || []).map((r, i) => <RitualCard key={i} ritual={r} idx={i} />)}
            </div>
          </div>

          {/* Evening rituals */}
          {(din.evening_rituals || []).length > 0 && (
            <div className="din-panel" style={{ marginTop: 16 }}>
              <h3 className="din-panel-head"><Moon size={14} style={{ color: '#a08cf0' }} />Evening Wind-Down</h3>
              <div className="din-ritual-list">
                {(din.evening_rituals || []).map((r, i) => <RitualCard key={i} ritual={r} idx={i} />)}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Meal Guidance ── */}
      {Object.keys(mealGuide).length > 0 && (
        <m.div className="din-section" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <h3 className="din-section-head"><UtensilsCrossed size={14} />Dosha Meal Guidance</h3>
          {mealGuide.general && <p className="din-section-body">{mealGuide.general}</p>}
          {mealGuide.agni_note && <p className="din-section-body">{mealGuide.agni_note}</p>}
          <MealGuidancePanel guidance={mealGuide} />
        </m.div>
      )}

      {/* ── Seasonal Ritucharya ── */}
      {seasonal.season && (
        <m.div className="din-section" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
          <h3 className="din-section-head"><Leaf size={14} />Seasonal Ritucharya — {seasonal.season}</h3>
          <div className="din-seasonal-cols">
            {seasonal.recommended_foods?.length > 0 && (
              <div className="din-seas-col">
                <h4 className="din-seas-col-head favour"><BadgeCheck size={11} />Recommended Foods</h4>
                <ul>{seasonal.recommended_foods.map((f, i) => <li key={i}>{f}</li>)}</ul>
              </div>
            )}
            {seasonal.foods_to_avoid?.length > 0 && (
              <div className="din-seas-col">
                <h4 className="din-seas-col-head avoid"><TriangleAlert size={11} />Avoid This Season</h4>
                <ul>{seasonal.foods_to_avoid.map((f, i) => <li key={i}>{f}</li>)}</ul>
              </div>
            )}
          </div>
          {seasonal.seasonal_practices?.length > 0 && (
            <div className="din-seas-practices">
              <h4 className="din-seas-col-head" style={{ marginBottom: 8 }}><Sparkles size={11} />Seasonal Practices</h4>
              <div className="din-seas-practice-grid">
                {seasonal.seasonal_practices.map((p, i) => (
                  <div key={i} className="din-seas-practice-chip"><ArrowRight size={10} />{p}</div>
                ))}
              </div>
            </div>
          )}
        </m.div>
      )}

      {/* The AI coaching was generated, billed against the daily allowance, and
          rendered nowhere. */}
      {coaching.length > 0 && (
        <m.div className="din-section" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
          <h3 className="din-section-head"><BookOpen size={14} />Why This Routine</h3>
          {coaching.map((c, i) => <p key={i} className="din-section-body">{c}</p>)}
          {plan.coaching_withheld?.length > 0 && (
            <p className="din-coaching-withheld">
              {plan.coaching_withheld.length === 1 ? 'One sentence' : `${plan.coaching_withheld.length} sentences`} of
              the AI coaching {plan.coaching_withheld.length === 1 ? 'was' : 'were'} held back because {plan.coaching_withheld.length === 1 ? 'it' : 'they'} recommended
              something this routine leaves out for you.
            </p>
          )}
        </m.div>
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
