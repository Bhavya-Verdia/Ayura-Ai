import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Check, ChevronDown, ChevronUp, Pause, Play, Plus, SkipForward, Timer, X } from 'lucide-react'
import client, { workoutsAPI } from '../../api/client'
import { track, EVENTS } from '../../lib/analytics'

/**
 * Gym workout mode.
 *
 * The plan was something to read between sets and log after the fact, from
 * inside an accordion — so most sets were never logged, and every adaptive
 * part of the feature (next week's weights, the next block, the level) runs on
 * logged sets. This runs the session the way it is trained: warm-up, then one
 * exercise at a time with each set ticked as it is done, the rest counted down
 * between them, and the exercise logged the moment it is finished rather than
 * at the end, so closing the tab costs at most the exercise in progress.
 */

const EFFORT = [
  { value: 'easy',  label: 'Easy' },
  { value: 'right', label: 'About right' },
  { value: 'hard',  label: 'Very hard' },
]

const repRange = (reps) => {
  const m = String(reps || '').trim().match(/^(\d+)\s*[-–]\s*(\d+)$/)
  return m ? [Number(m[1]), Number(m[2])] : null
}
// "30 sec", "45s hold", "1 × 6 min" — work measured in time, not reps.
const seconds = (text) => {
  const s = String(text || '')
  const min = s.match(/(\d+)\s*min/)
  if (min) return Number(min[1]) * 60
  const sec = s.match(/(\d+)\s*(?:s\b|sec)/)
  return sec ? Number(sec[1]) : null
}
const clock = (s) => {
  const v = Math.max(0, Math.round(s))
  return `${Math.floor(v / 60)}:${String(v % 60).padStart(2, '0')}`
}
const MAX_SECONDS = 4 * 60 * 60

function useChime() {
  const ctxRef = useRef(null)
  return useCallback((frequency = 660) => {
    try {
      const Ctx = window.AudioContext || window.webkitAudioContext
      if (!Ctx) return
      if (!ctxRef.current) ctxRef.current = new Ctx()
      const ctx = ctxRef.current
      if (ctx.state === 'suspended') ctx.resume()
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.frequency.value = frequency
      gain.gain.setValueAtTime(0.0001, ctx.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.16, ctx.currentTime + 0.02)
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.45)
      osc.connect(gain).connect(ctx.destination)
      osc.start()
      osc.stop(ctx.currentTime + 0.45)
    } catch { /* a cue is a nicety */ }
  }, [])
}

// A phone that locks between sets loses the rest timer and the next exercise.
function useWakeLock() {
  useEffect(() => {
    let lock = null
    let cancelled = false
    const acquire = async () => {
      try {
        if ('wakeLock' in navigator && document.visibilityState === 'visible') {
          lock = await navigator.wakeLock.request('screen')
          if (cancelled) lock.release()
        }
      } catch { /* not supported, or refused — the session still works */ }
    }
    acquire()
    const onVisible = () => { if (document.visibilityState === 'visible') acquire() }
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      cancelled = true
      document.removeEventListener('visibilitychange', onVisible)
      try { lock?.release() } catch { /* already released */ }
    }
  }, [])
}

/** Countdown that survives a throttled background tab: wall-clock deltas. */
function useCountdown(total, running, onDone) {
  const [left, setLeft] = useState(total)
  const doneRef = useRef(onDone)
  useEffect(() => { doneRef.current = onDone }, [onDone])
  useEffect(() => {
    if (!running) return undefined
    let last = performance.now()
    const id = setInterval(() => {
      const now = performance.now()
      const delta = (now - last) / 1000
      last = now
      setLeft(prev => Math.max(prev - delta, 0))
    }, 250)
    return () => clearInterval(id)
  }, [running])
  // Reaching zero is noticed here, not inside the state updater: React may run
  // an updater twice, and a side effect in one fired the interval timer's
  // phase change twice, skipping every easy phase.
  useEffect(() => {
    if (running && left <= 0) doneRef.current?.()
  }, [left, running])
  return [left, setLeft]
}

function RestTimer({ total, onFinish }) {
  const chime = useChime()
  const finish = useCallback(() => { chime(880); onFinish() }, [chime, onFinish])
  const [left, setLeft] = useCountdown(total, true, finish)
  return (
    <div className="gs-rest" role="timer" aria-live="polite">
      <span className="gs-rest-label"><Timer size={14} /> Rest</span>
      <span className="gs-rest-clock">{clock(left)}</span>
      <div className="gs-rest-actions">
        <button type="button" className="gym-log-toggle" onClick={() => setLeft(l => l + 30)}>
          <Plus size={12} /> 30 s
        </button>
        <button type="button" className="gym-log-save" onClick={onFinish}>
          <SkipForward size={12} /> Skip rest
        </button>
      </div>
    </div>
  )
}

function HoldTimer({ total }) {
  const chime = useChime()
  const [running, setRunning] = useState(false)
  const [left, setLeft] = useCountdown(total, running, () => { chime(880); setRunning(false) })
  return (
    <div className="gs-hold">
      <span className="gs-rest-clock">{clock(left)}</span>
      <div className="gs-rest-actions">
        <button type="button" className="gym-log-save" onClick={() => {
          if (left <= 0) setLeft(total)
          setRunning(r => !r)
        }}>
          {running ? <><Pause size={12} /> Pause</> : <><Play size={12} /> {left < total && left > 0 ? 'Resume' : 'Start'}</>}
        </button>
      </div>
    </div>
  )
}

// "30 sec hard / 30 sec easy" — work and easy phases, repeated for the sets.
const intervals = (text) => {
  const m = String(text || '').match(/(\d+)\s*(?:s\b|sec)[^/]*\/\s*(\d+)\s*(?:s\b|sec)/)
  return m ? [Number(m[1]), Number(m[2])] : null
}

function IntervalTimer({ work, easy, rounds }) {
  const chime = useChime()
  const [running, setRunning] = useState(false)
  const [phase, setPhase] = useState({ round: 1, hard: true })
  const [done, setDone] = useState(false)
  const advance = useCallback(() => {
    setPhase(p => {
      if (p.hard) { chime(520); return { ...p, hard: false } }
      if (p.round >= rounds) { chime(880); setRunning(false); setDone(true); return p }
      chime(880)
      return { round: p.round + 1, hard: true }
    })
  }, [chime, rounds])
  const [left, setLeft] = useCountdown(work, running, advance)
  // Each phase starts its own countdown.
  useEffect(() => { if (!done) setLeft(phase.hard ? work : easy) }, [phase, work, easy, done, setLeft])
  return (
    <div className={`gs-hold${phase.hard && running ? ' hard' : ''}`} role="timer" aria-live="polite">
      <span className="gs-rest-label">
        {done ? 'All rounds done' : `Round ${phase.round} of ${rounds} · ${phase.hard ? 'Hard' : 'Easy'}`}
      </span>
      <span className="gs-rest-clock">{clock(done ? 0 : left)}</span>
      {!done && (
        <div className="gs-rest-actions">
          <button type="button" className="gym-log-save" onClick={() => setRunning(r => !r)}>
            {running ? <><Pause size={12} /> Pause</> : <><Play size={12} /> {phase.round > 1 || !phase.hard ? 'Resume' : 'Start'}</>}
          </button>
        </div>
      )}
    </div>
  )
}

/** One exercise: the sets, ticked as they are done, with the rest between them. */
function ExerciseStep({ ex, adjusted, prior, onComplete, onSkip }) {
  const range = repRange(ex.reps)
  const bodyweight = (ex.equipment || 'bodyweight') === 'bodyweight'
    || /^(Bodyweight|Band)/.test(ex.weight_range || '')
  const loggable = Boolean(range) && ex.role !== 'conditioning'
  const setCount = Math.max(1, Math.min(Number(ex.sets) || 1, 8))
  const target = adjusted?.load_kg ? String(adjusted.load_kg) : ''
  const [rows, setRows] = useState(() => Array.from({ length: setCount }, (_, i) => ({
    kg: prior?.sets?.[i]?.kg ? String(prior.sets[i].kg) : target,
    reps: prior?.sets?.[i]?.reps ? String(prior.sets[i].reps) : '',
    done: false,
  })))
  const [resting, setResting] = useState(false)
  const [effort, setEffort] = useState(prior?.effort || 'right')
  const [howTo, setHowTo] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(false)
  const interval = !loggable ? intervals(ex.reps) : null
  const timed = !loggable && !interval ? seconds(ex.reps) : null
  const cardio = ex.role === 'conditioning' || ex.category === 'cardio'
  // What the plan asked for, as the default the person corrects.
  const plannedSeconds = interval
    ? (interval[0] + interval[1]) * Math.max(1, Number(ex.sets) || 1)
    : (timed || 0) * (cardio ? Math.max(1, Number(ex.sets) || 1) : 1)
  const [minutes, setMinutes] = useState(() => (
    prior?.minutes ? String(prior.minutes)
      : plannedSeconds ? String(Math.max(1, Math.round(plannedSeconds / 60))) : ''))
  const doneCount = rows.filter(r => r.done).length
  const allDone = doneCount === rows.length

  const markDone = (i) => {
    setRows(rs => rs.map((r, j) => {
      if (j !== i) return r
      // An empty reps box on a ticked set means the plan's number was hit.
      return { ...r, done: true, reps: r.reps || String(range ? range[1] : '') }
    }))
    // The next set starts from this set's weight when it was left blank.
    setRows(rs => rs.map((r, j) => (j === i + 1 && !r.kg ? { ...r, kg: rs[i].kg } : r)))
    if (i < rows.length - 1 && ex.rest_seconds > 0) setResting(true)
  }

  const finish = async () => {
    if (cardio && !loggable) {
      const value = parseFloat(minutes) || 0
      if (!value) { onComplete(null); return }
      setSaving(true)
      setError(false)
      try {
        await onComplete({ sets: [], minutes: value, effort })
      } catch {
        setError(true)
      } finally {
        setSaving(false)
      }
      return
    }
    if (!loggable) { onComplete(null); return }
    const sets = rows.filter(r => r.done)
      .map(r => ({ kg: bodyweight ? 0 : parseFloat(r.kg) || 0, reps: parseInt(r.reps, 10) || 0 }))
      .filter(s => s.reps > 0)
    if (!sets.length) { onComplete(null); return }
    setSaving(true)
    setError(false)
    try {
      await onComplete({ sets, effort })
    } catch {
      setError(true)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="gs-exercise">
      {ex.role_label && <span className="sp-section-tag">{ex.role_label}</span>}
      <h2 className="gs-title">{ex.exercise_name}</h2>
      <p className="gs-rx">
        {ex.sets} × {ex.reps}{ex.rest_seconds > 0 ? ` · ${ex.rest_seconds}s rest` : ''}
      </p>
      {adjusted ? (
        <p className="gs-target"><strong>This week for you: {adjusted.text}</strong><span>{adjusted.reason}</span></p>
      ) : ex.weight_range && <p className="gs-target"><span>{ex.weight_range}</span></p>}
      {ex.coaching_cue && <p className="gym-ex-cue">{ex.coaching_cue}</p>}
      {ex.instructions?.length > 0 && (
        <>
          <button type="button" className="gym-instructions-toggle" onClick={() => setHowTo(v => !v)}>
            {howTo ? <ChevronUp size={11} /> : <ChevronDown size={11} />} {howTo ? 'Hide instructions' : 'How to perform'}
          </button>
          {howTo && <ol className="gym-instructions-panel">{ex.instructions.map((s, i) => <li key={i}>{s}</li>)}</ol>}
        </>
      )}

      {loggable ? (
        <div className="gs-sets" role="group" aria-label={`Sets for ${ex.exercise_name}`}>
          {rows.map((r, i) => (
            <div key={i} className={`gs-set${r.done ? ' done' : ''}`}>
              <span className="gym-log-set-label">Set {i + 1}</span>
              {!bodyweight && (
                <input type="number" inputMode="decimal" min="0" max="500" step="0.5" placeholder="kg"
                  aria-label={`Set ${i + 1} kg`} value={r.kg}
                  onChange={e => setRows(rs => rs.map((x, j) => j === i ? { ...x, kg: e.target.value } : x))} />
              )}
              <input type="number" inputMode="numeric" min="0" max="100" step="1"
                placeholder={range ? `${range[0]}-${range[1]}` : 'reps'}
                aria-label={`Set ${i + 1} reps`} value={r.reps}
                onChange={e => setRows(rs => rs.map((x, j) => j === i ? { ...x, reps: e.target.value } : x))} />
              <button type="button" className={`gs-set-done${r.done ? ' on' : ''}`}
                aria-label={r.done ? `Set ${i + 1} done` : `Mark set ${i + 1} done`}
                aria-pressed={r.done} disabled={r.done || resting}
                onClick={() => markDone(i)}>
                <Check size={16} />
              </button>
            </div>
          ))}
        </div>
      ) : interval ? (
        <IntervalTimer work={interval[0]} easy={interval[1]} rounds={Math.max(1, Number(ex.sets) || 1)} />
      ) : timed ? (
        <HoldTimer total={timed} />
      ) : null}

      {resting && <RestTimer total={ex.rest_seconds} onFinish={() => setResting(false)} />}

      {cardio && !loggable && (
        <div className="gym-log-set gs-minutes">
          <span className="gym-log-set-label">Minutes done</span>
          <input type="number" inputMode="decimal" min="0" max="240" step="1" aria-label="Minutes done"
            value={minutes} onChange={e => setMinutes(e.target.value)} />
        </div>
      )}
      {((loggable && doneCount > 0) || (cardio && !loggable)) && !resting && (
        <div className="gym-log-effort" role="radiogroup" aria-label="How hard did it feel">
          {EFFORT.map(o => (
            <button key={o.value} type="button" role="radio" aria-checked={effort === o.value}
              className={`gym-log-chip${effort === o.value ? ' active' : ''}`}
              onClick={() => setEffort(o.value)}>{o.label}</button>
          ))}
        </div>
      )}
      {ex.notes && <p className="gym-ex-notes">{ex.notes}</p>}
      {error && <p className="gym-log-error">Could not save — check your connection and try again.</p>}

      <div className="gs-step-actions">
        <button type="button" className="gym-log-cancel" onClick={onSkip}>Skip exercise</button>
        <button type="button" className="gym-log-save gs-next" onClick={finish}
          disabled={saving || resting || (loggable && !allDone && doneCount === 0)}>
          {saving ? 'Saving…' : loggable && !allDone && doneCount > 0 ? `Finish with ${doneCount} set${doneCount > 1 ? 's' : ''}` : 'Next'}
        </button>
      </div>
    </div>
  )
}

function ListStep({ tag, title, items, onNext, nextLabel = 'Next' }) {
  const [ticked, setTicked] = useState(() => new Set())
  return (
    <div className="gs-exercise">
      <span className="sp-section-tag">{tag}</span>
      <h2 className="gs-title">{title}</h2>
      <ul className="gs-checklist">
        {items.map((item, i) => (
          <li key={i}>
            <label>
              <input type="checkbox" checked={ticked.has(i)}
                onChange={() => setTicked(t => { const n = new Set(t); n.has(i) ? n.delete(i) : n.add(i); return n })} />
              <span>{item}</span>
            </label>
          </li>
        ))}
      </ul>
      <div className="gs-step-actions">
        <span />
        <button type="button" className="gym-log-save gs-next" onClick={onNext}>{nextLabel}</button>
      </div>
    </div>
  )
}

export function GymSessionPlayer({ planId, week, day, adjustments, logs, onLogged, onClose }) {
  useWakeLock()
  const steps = useMemo(() => {
    const out = []
    if (day.warmup?.length) out.push({ kind: 'list', tag: 'Warm-up', title: 'Warm up', items: day.warmup })
    ;(day.main_workout || []).forEach(ex => out.push({ kind: 'exercise', ex }))
    if (day.balance?.length) out.push({ kind: 'list', tag: 'Balance', title: 'Balance', items: day.balance })
    if (day.cooldown?.length) out.push({ kind: 'list', tag: 'Cool-down', title: 'Cool down', items: day.cooldown })
    return out
  }, [day])
  const exerciseTotal = steps.filter(s => s.kind === 'exercise').length

  const [index, setIndex] = useState(0)
  const [finished, setFinished] = useState(false)
  const [logged, setLogged] = useState(0)
  const [saveState, setSaveState] = useState('idle')
  const [finalSeconds, setFinalSeconds] = useState(0)
  const startRef = useRef(0)
  const persistedRef = useRef(false)

  useEffect(() => {
    startRef.current = performance.now()
    track(EVENTS.GYM_SESSION_STARTED, { week, day: day.day, exercises: exerciseTotal })
  }, [week, day.day, exerciseTotal])

  const elapsed = () => Math.min((performance.now() - startRef.current) / 1000, MAX_SECONDS)

  const persist = useCallback(async (completed, reached) => {
    if (persistedRef.current) return
    persistedRef.current = true
    const secs = Math.round(Math.min((performance.now() - startRef.current) / 1000, MAX_SECONDS))
    track(EVENTS.GYM_SESSION_FINISHED, { week, day: day.day, completed, exercises: exerciseTotal,
      exercises_logged: logged, minutes: Math.round(secs / 60) })
    setSaveState('saving')
    try {
      await client.post('/practice/session', {
        plan_id: planId ?? null, feature: 'gym', week, day: day.day,
        duration_seconds: secs, segments_total: steps.length,
        segments_completed: Math.min(reached, steps.length), completed,
      })
      setSaveState('saved')
    } catch {
      setSaveState('error')
    }
  }, [planId, week, day.day, steps.length, exerciseTotal, logged])

  const next = useCallback(() => {
    if (index + 1 >= steps.length) {
      setFinalSeconds(Math.round(elapsed()))
      setFinished(true)
      persist(true, steps.length)
      return
    }
    setIndex(i => i + 1)
    window.scrollTo?.(0, 0)
  }, [index, steps.length, persist])

  const logExercise = useCallback(async (ex, entry) => {
    if (entry) {
      await workoutsAPI.log({ plan_id: planId, week, day: day.day, exercise_id: ex.exercise_id, ...entry })
      // Derived here so the event carries a yes/no, never the weights.
      const bodyweight = entry.sets.every(s => !s.kg)
      track(EVENTS.GYM_SETS_LOGGED, { week, sets: entry.sets.length, effort: entry.effort,
        minutes: entry.minutes ? Math.round(entry.minutes) : 0,
        bodyweight, edited: false, source: 'session' })
      setLogged(n => n + 1)
      onLogged?.(day.day, ex.exercise_id, entry)
    }
    next()
  }, [planId, week, day.day, next, onLogged])

  const exit = () => {
    // A session left after real work is still a session; a mis-tap is not.
    if (!finished && elapsed() > 60) persist(false, index)
    onClose()
  }

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') exit() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  const step = steps[index]
  const exerciseNo = steps.slice(0, index + 1).filter(s => s.kind === 'exercise').length

  const body = (
    <div className="sp-overlay gs-overlay" role="dialog" aria-modal="true" aria-label="Workout">
      <div className="sp-topbar">
        <div className="sp-progress-track">
          <div className="sp-progress-fill" style={{ width: `${((finished ? steps.length : index) / Math.max(steps.length, 1)) * 100}%` }} />
        </div>
        <div className="sp-topbar-row">
          <span className="sp-step-count">
            {finished ? 'Complete'
              : step?.kind === 'exercise' ? `Exercise ${exerciseNo} of ${exerciseTotal}` : step?.tag}
          </span>
          <span className="sp-total-left">Week {week} · {day.day_name}</span>
          <div className="sp-topbar-actions">
            <button className="sp-icon-btn" onClick={exit} aria-label="End workout"><X size={18} /></button>
          </div>
        </div>
      </div>

      <div className="gs-stage">
        {finished ? (
          <div className="sp-complete">
            <div className="sp-complete-mark"><Check size={40} strokeWidth={2.5} /></div>
            <h2>Workout complete</h2>
            <p className="sp-complete-sub">
              {clock(finalSeconds)} · {logged} of {exerciseTotal} exercises logged
            </p>
            <p className="sp-save-state">
              {saveState === 'saving' && 'Saving your session…'}
              {saveState === 'saved' && 'Saved — next week’s weights are set from what you logged.'}
              {saveState === 'error' && 'The session could not be saved, but every exercise you finished was logged.'}
            </p>
            <button className="sp-primary-btn" onClick={onClose}>Back to plan</button>
          </div>
        ) : step.kind === 'exercise' ? (
          <ExerciseStep
            key={`${index}:${step.ex.exercise_id}`}
            ex={step.ex}
            adjusted={adjustments?.[step.ex.exercise_id]}
            prior={logs?.[`${week}:${day.day}:${step.ex.exercise_id}`]}
            onComplete={(entry) => logExercise(step.ex, entry)}
            onSkip={next}
          />
        ) : (
          <ListStep key={index} tag={step.tag} title={step.title} items={step.items}
            onNext={next} nextLabel={index + 1 >= steps.length ? 'Finish workout' : 'Next'} />
        )}
      </div>
    </div>
  )
  return createPortal(body, document.body)
}

export default GymSessionPlayer
