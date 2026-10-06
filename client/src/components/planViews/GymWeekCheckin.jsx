import React, { useState } from 'react'
import { Check, ClipboardCheck, ShieldAlert, RefreshCw } from 'lucide-react'
import { workoutsAPI } from '../../api/client'

const FEELINGS = [
  { value: 'too_easy', label: 'Too easy' },
  { value: 'right',    label: 'About right' },
  { value: 'too_hard', label: 'Too hard' },
]

// Where it hurt. The values are the gym form's injury tokens, so a pain added
// to the injury list reaches the same gates as one ticked on the form; the
// server refuses anything outside GYM_INJURY_OPTIONS.
const PAIN_AREAS = [
  { value: 'knee',       label: 'Knee' },
  { value: 'lower_back', label: 'Lower back' },
  { value: 'shoulder',   label: 'Shoulder' },
  { value: 'elbow',      label: 'Elbow' },
  { value: 'wrist',      label: 'Wrist' },
  { value: 'neck',       label: 'Neck' },
  { value: 'hip',        label: 'Hip' },
  { value: 'ankle',      label: 'Ankle' },
]

// Reasons to stop and be examined — none of them is answered by a lighter weight.
const RED_FLAGS = [
  { value: 'chest_pain',     label: 'Chest pain or pressure' },
  { value: 'fainting',       label: 'Fainting or nearly fainting' },
  { value: 'palpitations',   label: 'Racing or irregular heartbeat' },
  { value: 'breathlessness', label: 'Breathless far beyond the effort' },
]

const toggle = (list, v) => (list.includes(v) ? list.filter(x => x !== v) : [...list, v])

/**
 * "How was week N?" — the three things a coach asks before writing the next
 * week. It can hold or lower next week's weights but never raise them; pain can
 * go onto the injury list both plans read; a red flag stops the plan's advice
 * about load altogether.
 */
export function GymWeekCheckin({ planId, week, saved, onSaved, onRebuild }) {
  const [open, setOpen] = useState(false)
  const [feeling, setFeeling] = useState(saved?.feeling || 'right')
  const [pain, setPain] = useState(saved?.pain_areas || [])
  const [addToInjuries, setAddToInjuries] = useState(false)
  const [unwell, setUnwell] = useState(!!saved?.unwell)
  const [flags, setFlags] = useState(saved?.red_flags || [])
  const [state, setState] = useState('idle')
  const [rebuild, setRebuild] = useState(false)

  if (!planId || week > 3) return null

  // Check-ins arrive after the card first renders, so the form is filled from
  // what was saved when it opens rather than when it mounts.
  const openForm = () => {
    setFeeling(saved?.feeling || 'right')
    setPain(saved?.pain_areas || [])
    setUnwell(!!saved?.unwell)
    setFlags(saved?.red_flags || [])
    setAddToInjuries(false)
    setOpen(true)
  }

  const save = async () => {
    setState('saving')
    const body = { plan_id: planId, week, feeling, pain_areas: pain, unwell, red_flags: flags,
      add_to_injuries: addToInjuries }
    try {
      const { data } = await workoutsAPI.checkin(body)
      setRebuild(!!data?.rebuild_recommended)
      onSaved?.(body)
      setState('saved')
      setOpen(false)
    } catch {
      setState('error')
    }
  }

  if (!open) {
    return (
      <div className="gym-checkin gym-checkin-closed">
        <span className="gym-checkin-title">
          <ClipboardCheck size={15} /> {saved ? `Week ${week} checked in` : `How was week ${week}?`}
        </span>
        <span className="gym-checkin-sub">
          {saved
            ? 'Week ' + (week + 1) + "'s weights take it into account."
            : `Thirty seconds — week ${week + 1}'s weights are set from it and your logged sets.`}
        </span>
        {saved?.red_flags?.length > 0 && (
          <p className="gym-checkin-stop" role="alert">
            <ShieldAlert size={14} /> Stop training and see a doctor before your next session.
          </p>
        )}
        {rebuild && onRebuild && (
          <button type="button" className="gym-log-save gym-checkin-rebuild" onClick={onRebuild}>
            <RefreshCw size={12} /> Rebuild my plan around it
          </button>
        )}
        <button type="button" className="gym-log-toggle" onClick={openForm}>
          {saved ? 'Edit check-in' : 'Check in'}
        </button>
      </div>
    )
  }

  return (
    <div className="gym-checkin" role="group" aria-label={`Week ${week} check-in`}>
      <span className="gym-checkin-title"><ClipboardCheck size={15} /> How was week {week}?</span>

      <p className="gym-checkin-q">Overall, the training felt</p>
      <div className="gym-log-effort" role="radiogroup" aria-label="Overall the training felt">
        {FEELINGS.map(o => (
          <button key={o.value} type="button" role="radio" aria-checked={feeling === o.value}
            className={`gym-log-chip${feeling === o.value ? ' active' : ''}`}
            onClick={() => setFeeling(o.value)}>{o.label}</button>
        ))}
      </div>

      <p className="gym-checkin-q">Any new pain while training or after?</p>
      <div className="gym-log-effort">
        {PAIN_AREAS.map(o => (
          <button key={o.value} type="button" aria-pressed={pain.includes(o.value)}
            className={`gym-log-chip${pain.includes(o.value) ? ' active' : ''}`}
            onClick={() => setPain(p => toggle(p, o.value))}>{o.label}</button>
        ))}
      </div>
      {pain.length > 0 && (
        <label className="gym-checkin-check">
          <input type="checkbox" checked={addToInjuries} onChange={e => setAddToInjuries(e.target.checked)} />
          Add to my injuries, so my gym and yoga plans work around it
        </label>
      )}

      <label className="gym-checkin-check">
        <input type="checkbox" checked={unwell} onChange={e => setUnwell(e.target.checked)} />
        I was unwell this week
      </label>

      <p className="gym-checkin-q">Did any of these happen while training?</p>
      <div className="gym-log-effort">
        {RED_FLAGS.map(o => (
          <button key={o.value} type="button" aria-pressed={flags.includes(o.value)}
            className={`gym-log-chip gym-checkin-flag${flags.includes(o.value) ? ' active' : ''}`}
            onClick={() => setFlags(f => toggle(f, o.value))}>{o.label}</button>
        ))}
      </div>
      {flags.length > 0 && (
        <p className="gym-checkin-stop" role="alert">
          <ShieldAlert size={14} /> Stop training and see a doctor before your next session — these
          are reasons to be examined, not to lift lighter.
        </p>
      )}

      <div className="gym-log-actions">
        <button type="button" className="gym-log-cancel" onClick={() => setOpen(false)}>Cancel</button>
        <button type="button" className="gym-log-save" onClick={save} disabled={state === 'saving'}>
          {state === 'saving' ? 'Saving…' : <><Check size={12} /> Save</>}
        </button>
      </div>
      {state === 'error' && <p className="gym-log-error">Could not save — check your connection and try again.</p>}
    </div>
  )
}
