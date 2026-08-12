import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import {
  Play, Pause, SkipForward, SkipBack, X, Check, Volume2, VolumeX,
} from 'lucide-react'
import { PoseFigure } from './PoseFigure'
import {
  buildSessionTimeline, timelineTotalSeconds, formatClock, SEGMENT_KIND,
} from './buildSessionTimeline'
import client from '../../api/client'
import { useTranslation } from 'react-i18next'

/**
 * Guided practice mode.
 *
 * The yoga plan was a document — four weeks of well-reasoned sequences that a
 * user could read but never be led through, and that the app had no way of
 * knowing had ever been practised. This runs the session: one segment at a
 * time, counting down, announcing side changes, and recording what was actually
 * done when it ends.
 */

// A short sine blip marks each segment change. Generated with WebAudio rather
// than shipped as a file — artifact CSP aside, a two-tone cue is not worth a
// network request, and this keeps the player self-contained.
function useChime(enabled) {
  const ctxRef = useRef(null)
  return useCallback((frequency = 660) => {
    if (!enabled) return
    try {
      const Ctx = window.AudioContext || window.webkitAudioContext
      if (!Ctx) return
      if (!ctxRef.current) ctxRef.current = new Ctx()
      const ctx = ctxRef.current
      if (ctx.state === 'suspended') ctx.resume()
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = 'sine'
      osc.frequency.value = frequency
      gain.gain.setValueAtTime(0.0001, ctx.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.14, ctx.currentTime + 0.02)
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.5)
      osc.connect(gain).connect(ctx.destination)
      osc.start()
      osc.stop(ctx.currentTime + 0.5)
    } catch {
      /* audio is a nicety — never let it break the practice */
    }
  }, [enabled])
}

function ProgressRing({ fraction }) {
  const R = 52
  const C = 2 * Math.PI * R
  return (
    <svg className="sp-ring" viewBox="0 0 120 120" aria-hidden="true">
      <circle className="sp-ring-track" cx="60" cy="60" r={R} />
      <circle
        className="sp-ring-fill" cx="60" cy="60" r={R}
        strokeDasharray={C}
        strokeDashoffset={C * (1 - fraction)}
      />
    </svg>
  )
}

export function SessionPlayer({ session, planId, week, day, onClose }) {
  const { t } = useTranslation()
  const segments = useMemo(() => buildSessionTimeline(session), [session])
  const totalSeconds = useMemo(() => timelineTotalSeconds(segments), [segments])

  const [index, setIndex] = useState(0)
  const [remaining, setRemaining] = useState(segments[0]?.seconds ?? 0)
  const [running, setRunning] = useState(false)
  const [sound, setSound] = useState(true)
  const [finished, setFinished] = useState(false)
  const [saveState, setSaveState] = useState('idle')
  // Snapshotted when the practice ends — the running total lives in a ref so the
  // countdown does not re-render on every tick, and a ref cannot be read during
  // render.
  const [finalSeconds, setFinalSeconds] = useState(0)

  const skippedRef = useRef(new Set())
  const elapsedRef = useRef(0)
  const chime = useChime(sound)

  const segment = segments[index]
  const isLast = index >= segments.length - 1

  // Countdown. Wall-clock deltas rather than an accumulating counter, so a
  // backgrounded tab (where timers are throttled) does not silently drift.
  useEffect(() => {
    if (!running || finished) return undefined
    let last = performance.now()
    const id = setInterval(() => {
      const now = performance.now()
      const delta = (now - last) / 1000
      last = now
      elapsedRef.current += delta
      setRemaining(prev => Math.max(prev - delta, 0))
    }, 250)
    return () => clearInterval(id)
  }, [running, finished])

  const persist = useCallback(async (completed) => {
    setSaveState('saving')
    try {
      await client.post('/practice/session', {
        plan_id: planId ?? null,
        feature: 'yoga',
        week, day,
        duration_seconds: Math.round(elapsedRef.current),
        segments_total: segments.length,
        segments_completed: completed ? segments.length : index,
        completed,
        skipped_pose_ids: Array.from(skippedRef.current).slice(0, 60),
      })
      setSaveState('saved')
    } catch {
      // A failed log must never cost the user their practice. Say so and move on.
      setSaveState('error')
    }
  }, [planId, week, day, segments.length, index])

  const goTo = useCallback((nextIndex, { skipped = false } = {}) => {
    if (skipped && segments[index]?.poseId) skippedRef.current.add(segments[index].poseId)
    if (nextIndex >= segments.length) {
      setFinalSeconds(Math.round(elapsedRef.current))
      setFinished(true)
      setRunning(false)
      chime(880)
      // Finishing is an event, not a consequence of rendering — record it here
      // rather than from an effect watching `finished`.
      persist(true)
      return
    }
    const clamped = Math.max(0, nextIndex)
    setIndex(clamped)
    setRemaining(segments[clamped]?.seconds ?? 0)
  }, [index, segments, chime, persist])

  // Advance when the current segment runs out.
  useEffect(() => {
    if (!running || finished || remaining > 0) return
    chime(isLast ? 880 : 660)
    goTo(index + 1)
  }, [remaining, running, finished, index, isLast, goTo, chime])

  const exitEarly = useCallback(() => {
    if (elapsedRef.current > 30 && !finished) persist(false)
    onClose()
  }, [finished, persist, onClose])

  // Keyboard control — space to pause, arrows to move, escape to leave.
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === ' ') { e.preventDefault(); setRunning(r => !r) }
      else if (e.key === 'ArrowRight') goTo(index + 1, { skipped: true })
      else if (e.key === 'ArrowLeft') goTo(index - 1)
      else if (e.key === 'Escape') exitEarly()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [index, goTo, exitEarly])

  if (!segments.length) return null

  const segmentFraction = segment ? 1 - remaining / Math.max(segment.seconds, 1) : 0
  const doneSeconds = segments.slice(0, index).reduce((s, x) => s + x.seconds, 0)
  const overallFraction = Math.min((doneSeconds + (segment?.seconds ?? 0) * segmentFraction) / Math.max(totalSeconds, 1), 1)

  const body = (
    <div className="sp-overlay" role="dialog" aria-modal="true"
         aria-label={t('practice.title', 'Guided practice')}>
      <div className="sp-topbar">
        <div className="sp-progress-track">
          <div className="sp-progress-fill" style={{ width: `${overallFraction * 100}%` }} />
        </div>
        <div className="sp-topbar-row">
          <span className="sp-step-count">
            {finished
              ? t('practice.complete', 'Complete')
              : t('practice.stepCount', '{{current}} of {{total}}', { current: index + 1, total: segments.length })}
          </span>
          <span className="sp-total-left">
            {t('practice.timeLeft', '{{time}} left', {
              time: formatClock(Math.max(totalSeconds - doneSeconds - (segment ? segment.seconds - remaining : 0), 0)),
            })}
          </span>
          <div className="sp-topbar-actions">
            <button className="sp-icon-btn" onClick={() => setSound(s => !s)}
                    aria-label={sound ? t('practice.mute', 'Mute cues') : t('practice.unmute', 'Unmute cues')}>
              {sound ? <Volume2 size={16} /> : <VolumeX size={16} />}
            </button>
            <button className="sp-icon-btn" onClick={exitEarly}
                    aria-label={t('practice.exit', 'Exit practice')}>
              <X size={18} />
            </button>
          </div>
        </div>
      </div>

      {finished ? (
        <div className="sp-stage sp-complete">
          <div className="sp-complete-mark"><Check size={40} strokeWidth={2.5} /></div>
          <h2>{t('practice.completeTitle', 'Practice complete')}</h2>
          <p className="sp-complete-sub">
            {formatClock(finalSeconds)} · {t('practice.segments', '{{count}} segments', { count: segments.length })}
          </p>
          <p className="sp-save-state">
            {saveState === 'saving' && t('practice.saving', 'Saving your session…')}
            {saveState === 'saved' && t('practice.saved', 'Session saved to your timeline.')}
            {saveState === 'error' && t('practice.saveFailed', 'We could not save this session, but the practice still counts.')}
          </p>
          <button className="sp-primary-btn" onClick={onClose}>{t('practice.done', 'Done')}</button>
        </div>
      ) : (
        <div className="sp-stage">
          <span className="sp-section-tag">
            {t(`practice.section.${segment.section}`, segment.sectionLabel)}
          </span>
          <h2 className="sp-title">{segment.title}</h2>
          {segment.subtitle && <p className="sp-subtitle">{segment.subtitle}</p>}

          <div className="sp-timer-block">
            <ProgressRing fraction={segmentFraction} />
            <span className="sp-timer">{formatClock(remaining)}</span>
          </div>

          {segment.kind === SEGMENT_KIND.POSE && (
            <PoseFigure imageUrl={segment.imageUrl} name={segment.title}
                        category={segment.category} className="sp-pose-img" />
          )}

          {segment.breathCue && <p className="sp-breath-cue">{segment.breathCue}</p>}

          {segment.kind === SEGMENT_KIND.FLOW ? (
            <ol className="sp-steps">
              {segment.steps.map(s => (
                <li key={s.step}>
                  <strong>{s.sanskrit}</strong> — {s.cue}
                </li>
              ))}
            </ol>
          ) : (
            segment.instructions?.length > 0 && (
              <ol className="sp-steps">
                {segment.instructions.map((step, i) => <li key={i}>{step}</li>)}
              </ol>
            )
          )}

          {segment.modification && (
            <p className="sp-modification">{segment.modification}</p>
          )}
          {segment.safetyNotes?.length > 0 && (
            <ul className="sp-safety">
              {segment.safetyNotes.map((n, i) => <li key={i}>{n}</li>)}
            </ul>
          )}
        </div>
      )}

      {!finished && (
        <div className="sp-controls">
          <button className="sp-ctrl-btn" onClick={() => goTo(index - 1)}
                  disabled={index === 0} aria-label={t('practice.previous', 'Previous segment')}>
            <SkipBack size={20} />
          </button>
          <button className="sp-play-btn" onClick={() => setRunning(r => !r)}
                  aria-label={running ? t('practice.pause', 'Pause') : t('practice.start', 'Start')}>
            {running ? <Pause size={26} /> : <Play size={26} />}
          </button>
          <button className="sp-ctrl-btn" onClick={() => goTo(index + 1, { skipped: true })}
                  aria-label={t('practice.skip', 'Skip segment')}>
            <SkipForward size={20} />
          </button>
        </div>
      )}
    </div>
  )

  return createPortal(body, document.body)
}

export default SessionPlayer
