import React, { useState } from 'react'
import { Check, PencilLine } from 'lucide-react'
import { workoutsAPI } from '../../api/client'
import { track, EVENTS } from '../../lib/analytics'

// How hard the sets felt. "Right" is what the plan asks for — the last two reps
// hard — and is what the next block's loads assume when nothing is said.
const EFFORT = [
  { value: 'easy',  label: 'Easy' },
  { value: 'right', label: 'About right' },
  { value: 'hard',  label: 'Very hard' },
]

const isRepRange = (reps) => /^\d+\s*-\s*\d+$/.test(String(reps || '').trim())

/**
 * Logs what was actually lifted for one exercise on one day. Only rep-based
 * work is logged: a carry or a plank has no weight-for-reps to learn from, and
 * conditioning is effort-based.
 */
export function GymSetLogger({ planId, week, day, exercise, logged, onSaved }) {
  const bodyweight = (exercise.equipment || 'bodyweight') === 'bodyweight'
  const setCount = Math.max(1, Math.min(Number(exercise.sets) || 3, 8))
  const initialRows = () => {
    const prior = logged?.sets || []
    return Array.from({ length: Math.max(setCount, prior.length) }, (_, i) => ({
      kg: prior[i]?.kg ? String(prior[i].kg) : '',
      reps: prior[i]?.reps ? String(prior[i].reps) : '',
    }))
  }
  const [open, setOpen] = useState(false)
  const [rows, setRows] = useState(initialRows)
  const [effort, setEffort] = useState(logged?.effort || 'right')
  const [state, setState] = useState('idle')
  const [minutes, setMinutes] = useState(logged?.minutes ? String(logged.minutes) : '')
  // Conditioning is logged as time and effort; there is no weight for reps.
  const cardio = exercise.role === 'conditioning' || exercise.category === 'cardio'

  if (!planId || (!cardio && !isRepRange(exercise.reps))) return null

  if (cardio) {
    const saveMinutes = async () => {
      setState('saving')
      const value = parseFloat(minutes) || 0
      try {
        await workoutsAPI.log({ plan_id: planId, week, day, exercise_id: exercise.exercise_id,
          sets: [], minutes: value, effort })
        onSaved?.(value > 0 ? { sets: [], minutes: value, effort } : null)
        if (value > 0) {
          track(EVENTS.GYM_SETS_LOGGED, { week, sets: 0, minutes: Math.round(value), effort,
            bodyweight: true, edited: Boolean(logged), source: 'plan' })
        }
        setState('saved')
        setOpen(false)
      } catch {
        setState('error')
      }
    }
    if (!open) {
      return (
        <div className="gym-log-row">
          {logged?.minutes > 0 && (
            <span className="gym-log-summary"><Check size={11} /> Logged: {logged.minutes} min</span>
          )}
          <button type="button" className="gym-log-toggle" onClick={() => setOpen(true)}>
            <PencilLine size={11} /> {logged?.minutes ? 'Edit' : 'Log your minutes'}
          </button>
        </div>
      )
    }
    return (
      <div className="gym-log-editor" role="group" aria-label={`Log minutes for ${exercise.exercise_name}`}>
        <div className="gym-log-set">
          <span className="gym-log-set-label">Minutes</span>
          <input type="number" inputMode="decimal" min="0" max="240" step="1" aria-label="Minutes"
            placeholder="min" value={minutes} onChange={e => setMinutes(e.target.value)} />
        </div>
        <div className="gym-log-effort" role="radiogroup" aria-label="How hard did it feel">
          {EFFORT.map(o => (
            <button key={o.value} type="button" role="radio" aria-checked={effort === o.value}
              className={`gym-log-chip${effort === o.value ? ' active' : ''}`}
              onClick={() => setEffort(o.value)}>{o.label}</button>
          ))}
        </div>
        <div className="gym-log-actions">
          <button type="button" className="gym-log-cancel" onClick={() => setOpen(false)}>Cancel</button>
          <button type="button" className="gym-log-save" onClick={saveMinutes} disabled={state === 'saving'}>
            {state === 'saving' ? 'Saving…' : 'Save'}
          </button>
        </div>
        {state === 'error' && <p className="gym-log-error">Could not save — check your connection and try again.</p>}
      </div>
    )
  }

  const save = async () => {
    setState('saving')
    const sets = rows
      .map(r => ({ kg: bodyweight ? 0 : parseFloat(r.kg) || 0, reps: parseInt(r.reps, 10) || 0 }))
      .filter(r => r.reps > 0)
    try {
      await workoutsAPI.log({ plan_id: planId, week, day, exercise_id: exercise.exercise_id, sets, effort })
      onSaved?.(sets.length ? { sets, effort } : null)
      if (sets.length) {
        track(EVENTS.GYM_SETS_LOGGED, { week, sets: sets.length, effort, bodyweight,
          edited: Boolean(logged), source: 'plan' })
      }
      setState('saved')
      setOpen(false)
    } catch {
      setState('error')
    }
  }

  const summary = logged?.sets?.length
    ? logged.sets.map(s => (bodyweight || !s.kg ? `${s.reps}` : `${s.kg}×${s.reps}`)).join(', ')
    : null

  if (!open) {
    return (
      <div className="gym-log-row">
        {summary && (
          <span className="gym-log-summary"><Check size={11} /> Logged: {summary}</span>
        )}
        <button type="button" className="gym-log-toggle"
          onClick={() => { setRows(initialRows()); setOpen(true) }}>
          <PencilLine size={11} /> {summary ? 'Edit' : 'Log your sets'}
        </button>
      </div>
    )
  }

  return (
    <div className="gym-log-editor" role="group" aria-label={`Log sets for ${exercise.exercise_name}`}>
      {rows.map((r, i) => (
        <div key={i} className="gym-log-set">
          <span className="gym-log-set-label">Set {i + 1}</span>
          {!bodyweight && (
            <input type="number" inputMode="decimal" min="0" max="500" step="0.5"
              aria-label={`Set ${i + 1} kg`} placeholder="kg" value={r.kg}
              onChange={e => setRows(rs => rs.map((x, j) => j === i ? { ...x, kg: e.target.value } : x))} />
          )}
          <input type="number" inputMode="numeric" min="0" max="100" step="1"
            aria-label={`Set ${i + 1} reps`} placeholder="reps" value={r.reps}
            onChange={e => setRows(rs => rs.map((x, j) => j === i ? { ...x, reps: e.target.value } : x))} />
        </div>
      ))}
      <div className="gym-log-effort" role="radiogroup" aria-label="How hard did it feel">
        {EFFORT.map(o => (
          <button key={o.value} type="button" role="radio" aria-checked={effort === o.value}
            className={`gym-log-chip${effort === o.value ? ' active' : ''}`}
            onClick={() => setEffort(o.value)}>{o.label}</button>
        ))}
      </div>
      <div className="gym-log-actions">
        <button type="button" className="gym-log-cancel" onClick={() => setOpen(false)}>Cancel</button>
        <button type="button" className="gym-log-save" onClick={save} disabled={state === 'saving'}>
          {state === 'saving' ? 'Saving…' : 'Save'}
        </button>
      </div>
      {state === 'error' && <p className="gym-log-error">Could not save — check your connection and try again.</p>}
    </div>
  )
}
