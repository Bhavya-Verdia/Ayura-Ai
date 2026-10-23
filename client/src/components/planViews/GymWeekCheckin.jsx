import React, { useState } from 'react'
import { Check, ClipboardCheck, ShieldAlert, RefreshCw } from 'lucide-react'
import { workoutsAPI } from '../../api/client'
import { track, EVENTS } from '../../lib/analytics'

import { tr } from '../../lib/tr'
import { Trans } from 'react-i18next'
const FEELINGS = [
  { value: 'too_easy', get label() { return tr('ui.gymWeekCheckin.tooEasy', 'Too easy') } },
  { value: 'right',    get label() { return tr('ui.gymWeekCheckin.aboutRight', 'About right') } },
  { value: 'too_hard', get label() { return tr('ui.gymWeekCheckin.tooHard', 'Too hard') } },
]

// Where it hurt. The values are the gym form's injury tokens, so a pain added
// to the injury list reaches the same gates as one ticked on the form; the
// server refuses anything outside GYM_INJURY_OPTIONS.
const PAIN_AREAS = [
  { value: 'knee',       get label() { return tr('ui.gymWeekCheckin.knee', 'Knee') } },
  { value: 'lower_back', get label() { return tr('ui.gymWeekCheckin.lowerBack', 'Lower back') } },
  { value: 'shoulder',   get label() { return tr('ui.gymWeekCheckin.shoulder', 'Shoulder') } },
  { value: 'elbow',      get label() { return tr('ui.gymWeekCheckin.elbow', 'Elbow') } },
  { value: 'wrist',      get label() { return tr('ui.gymWeekCheckin.wrist', 'Wrist') } },
  { value: 'neck',       get label() { return tr('ui.gymWeekCheckin.neck', 'Neck') } },
  { value: 'hip',        get label() { return tr('ui.gymWeekCheckin.hip', 'Hip') } },
  { value: 'ankle',      get label() { return tr('ui.gymWeekCheckin.ankle', 'Ankle') } },
]

// Reasons to stop and be examined — none of them is answered by a lighter weight.
const RED_FLAGS = [
  { value: 'chest_pain',     get label() { return tr('ui.gymWeekCheckin.chestPainOrPressure', 'Chest pain or pressure') } },
  { value: 'fainting',       get label() { return tr('ui.gymWeekCheckin.faintingOrNearlyFainting', 'Fainting or nearly fainting') } },
  { value: 'palpitations',   get label() { return tr('ui.gymWeekCheckin.racingOrIrregularHeartbeat', 'Racing or irregular heartbeat') } },
  { value: 'breathlessness', get label() { return tr('ui.gymWeekCheckin.breathlessFarBeyondTheEffort', 'Breathless far beyond the effort') } },
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
      // The week and how hard it felt only — pain, symptoms and injuries are
      // health answers and are not sent, not even as yes/no.
      track(EVENTS.GYM_CHECKIN_SUBMITTED, { week, feeling, edited: Boolean(saved) })
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
          <ClipboardCheck size={15} /> {saved ? tr('ui.gymWeekCheckin.weekCheckedIn', 'Week {{week}} checked in', { week }) : tr('ui.gymWeekCheckin.howWasWeek', 'How was week {{week}}?', { week })}
        </span>
        <span className="gym-checkin-sub">
          {saved
            ? 'Week ' + (week + 1) + "'s weights take it into account."
            : tr('ui.gymWeekCheckin.thirtySecondsWeekSWeights', 'Thirty seconds — week {{value}}\'s weights are set from it and your logged sets.', { value: week + 1 })}
        </span>
        {saved?.red_flags?.length > 0 && (
          <p className="gym-checkin-stop" role="alert">
            <ShieldAlert size={14} />{' '}{tr('ui.gymWeekCheckin.stopTrainingAndSeeA', 'Stop training and see a doctor before your next session.')}
          </p>
        )}
        {rebuild && onRebuild && (
          <button type="button" className="gym-log-save gym-checkin-rebuild"
            onClick={() => { track(EVENTS.GYM_REBUILD_REQUESTED, { source: 'checkin', week }); onRebuild() }}>
            <RefreshCw size={12} />{' '}{tr('ui.gymWeekCheckin.rebuildMyPlanAroundIt', 'Rebuild my plan around it')}
          </button>
        )}
        <button type="button" className="gym-log-toggle" onClick={openForm}>
          {saved ? tr('ui.gymWeekCheckin.editCheckIn', 'Edit check-in') : tr('ui.gymWeekCheckin.checkIn', 'Check in')}
        </button>
      </div>
    )
  }

  return (
    <div className="gym-checkin" role="group" aria-label={tr('ui.gymWeekCheckin.weekCheckIn', 'Week {{week}} check-in', { week })}>
      <span className="gym-checkin-title"><Trans i18nKey="ui.gymWeekCheckin.n0HowWasWeek" defaults={"<0/> How was week {{week}}?"} values={{ week }} components={[<ClipboardCheck size={15} />]} /></span>

      <p className="gym-checkin-q">{tr('ui.gymWeekCheckin.overallTheTrainingFelt', 'Overall, the training felt')}</p>
      <div className="gym-log-effort" role="radiogroup" aria-label={tr('ui.gymWeekCheckin.overallTheTrainingFelt2', 'Overall the training felt')}>
        {FEELINGS.map(o => (
          <button key={o.value} type="button" role="radio" aria-checked={feeling === o.value}
            className={`gym-log-chip${feeling === o.value ? ' active' : ''}`}
            onClick={() => setFeeling(o.value)}>{o.label}</button>
        ))}
      </div>

      <p className="gym-checkin-q">{tr('ui.gymWeekCheckin.anyNewPainWhileTraining', 'Any new pain while training or after?')}</p>
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
          {tr('ui.gymWeekCheckin.addToMyInjuriesSo', 'Add to my injuries, so my gym and yoga plans work around it')}
        </label>
      )}

      <label className="gym-checkin-check">
        <input type="checkbox" checked={unwell} onChange={e => setUnwell(e.target.checked)} />
        {tr('ui.gymWeekCheckin.iWasUnwellThisWeek', 'I was unwell this week')}
      </label>

      <p className="gym-checkin-q">{tr('ui.gymWeekCheckin.didAnyOfTheseHappen', 'Did any of these happen while training?')}</p>
      <div className="gym-log-effort">
        {RED_FLAGS.map(o => (
          <button key={o.value} type="button" aria-pressed={flags.includes(o.value)}
            className={`gym-log-chip gym-checkin-flag${flags.includes(o.value) ? ' active' : ''}`}
            onClick={() => setFlags(f => toggle(f, o.value))}>{o.label}</button>
        ))}
      </div>
      {flags.length > 0 && (
        <p className="gym-checkin-stop" role="alert">
          <ShieldAlert size={14} />{' '}{tr('ui.gymWeekCheckin.stopTrainingAndSeeA2', 'Stop training and see a doctor before your next session — these are reasons to be examined, not to lift lighter.')}
        </p>
      )}

      <div className="gym-log-actions">
        <button type="button" className="gym-log-cancel" onClick={() => setOpen(false)}>{tr('ui.gymWeekCheckin.cancel', 'Cancel')}</button>
        <button type="button" className="gym-log-save" onClick={save} disabled={state === 'saving'}>
          {state === 'saving' ? tr('ui.gymWeekCheckin.saving', 'Saving…') : <><Check size={12} />{' '}{tr('ui.gymWeekCheckin.save', 'Save')}</>}
        </button>
      </div>
      {state === 'error' && <p className="gym-log-error">{tr('ui.gymWeekCheckin.couldNotSaveCheckYour', 'Could not save — check your connection and try again.')}</p>}
    </div>
  )
}
