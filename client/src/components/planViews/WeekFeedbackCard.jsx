import React, { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { ArrowRight, Loader2, Sparkles } from 'lucide-react'
import client from '../../api/client'
import { primaryName, secondaryName } from './poseNames'

/**
 * End-of-week feedback, and the trigger for the next week.
 *
 * The plan used to arrive as four weeks generated up front — which meant week 3
 * was decided before the user had practised week 1. Weeks are now built one at a
 * time from what actually happened, and this is where that gets asked.
 *
 * Every question is optional and the next week can be generated without
 * answering any of them. Someone who wants to keep practising should never be
 * held up by a form.
 */

const CHOICES = {
  difficulty: [
    { v: 'too_easy', k: 'tooEasy', label: 'Too easy' },
    { v: 'just_right', k: 'justRight', label: 'Just right' },
    { v: 'too_hard', k: 'tooHard', label: 'Too hard' },
  ],
  session_length: [
    { v: 'too_short', k: 'tooShort', label: 'Too short' },
    { v: 'just_right', k: 'justRight', label: 'Just right' },
    { v: 'too_long', k: 'tooLong', label: 'Too long' },
  ],
  energy_after: [
    { v: 'drained', k: 'drained', label: 'Drained' },
    { v: 'neutral', k: 'neutral', label: 'Neutral' },
    { v: 'energised', k: 'energised', label: 'Energised' },
  ],
}


function ChoiceRow({ name, value, onChange, options, t }) {
  return (
    <div className="wf-choice-row">
      {options.map(opt => (
        <button
          key={opt.v}
          type="button"
          className={`wf-choice${value === opt.v ? ' selected' : ''}`}
          aria-pressed={value === opt.v}
          onClick={() => onChange(value === opt.v ? null : opt.v)}
        >
          {t(`yoga.feedback.${name}.${opt.k}`, opt.label)}
        </button>
      ))}
    </div>
  )
}


export function WeekFeedbackCard({ plan, week, nextWeek, onPlanUpdate }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const [answers, setAnswers] = useState({
    difficulty: null, session_length: null, energy_after: null,
  })
  const [daysPractised, setDaysPractised] = useState(null)
  const [dropped, setDropped] = useState(() => new Set())
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState(null)

  // Only poses the user actually met this week can be dropped.
  const weekPoses = React.useMemo(() => {
    const seen = new Map()
    for (const day of week?.days || []) {
      if (!day.session) continue
      for (const section of ['warmup', 'main_sequence', 'cooldown']) {
        for (const p of day.session[section] || []) {
          if (p.pose_id && !p.final_relaxation && !seen.has(p.pose_id)) {
            seen.set(p.pose_id, { name: primaryName(p), english: secondaryName(p) })
          }
        }
      }
    }
    return [...seen.entries()].map(([id, names]) => ({ id, ...names }))
  }, [week])

  const set = (name) => (value) => setAnswers(a => ({ ...a, [name]: value }))

  const toggleDropped = (poseId) => setDropped(prev => {
    const next = new Set(prev)
    if (next.has(poseId)) next.delete(poseId); else next.add(poseId)
    return next
  })

  const submit = async () => {
    setStatus('saving')
    setError(null)
    try {
      const { data } = await client.post('/plans/yoga/next-week', {
        plan_id: plan.plan_id,
        week: week?.week,
        feedback: {
          ...answers,
          days_practised: daysPractised,
          dropped_pose_ids: [...dropped],
        },
      })
      setStatus('done')
      onPlanUpdate?.(data)
      queryClient.invalidateQueries({ queryKey: ['plans-history'] })
    } catch (err) {
      setStatus('idle')
      setError(
        err?.response?.data?.detail
        || t('yoga.feedback.error', 'We could not build the next week. Please try again.')
      )
    }
  }

  const busy = status === 'saving'

  return (
    <div className="wf-card">
      <div className="wf-header">
        <Sparkles size={14} className="wf-icon" />
        <div>
          <h3 className="wf-title">
            {t('yoga.feedback.title', 'How did week {{n}} go?', { n: week?.week })}
          </h3>
          <p className="wf-sub">
            {t('yoga.feedback.subtitle',
               'Week {{n}} is built from your answers. Skip anything you would rather not answer.',
               { n: nextWeek })}
          </p>
        </div>
      </div>

      <div className="wf-question">
        <span className="wf-label">{t('yoga.feedback.difficultyLabel', 'The practice felt')}</span>
        <ChoiceRow name="difficulty" value={answers.difficulty}
                   onChange={set('difficulty')} options={CHOICES.difficulty} t={t} />
      </div>

      <div className="wf-question">
        <span className="wf-label">{t('yoga.feedback.lengthLabel', 'Session length was')}</span>
        <ChoiceRow name="session_length" value={answers.session_length}
                   onChange={set('session_length')} options={CHOICES.session_length} t={t} />
      </div>

      <div className="wf-question">
        <span className="wf-label">{t('yoga.feedback.energyLabel', 'Afterwards you felt')}</span>
        <ChoiceRow name="energy_after" value={answers.energy_after}
                   onChange={set('energy_after')} options={CHOICES.energy_after} t={t} />
      </div>

      <div className="wf-question">
        <span className="wf-label">
          {t('yoga.feedback.daysLabel', 'Days you practised')}
        </span>
        <div className="wf-choice-row wf-days">
          {[0, 1, 2, 3, 4, 5, 6, 7].map(n => (
            <button
              key={n} type="button"
              className={`wf-choice wf-day${daysPractised === n ? ' selected' : ''}`}
              aria-pressed={daysPractised === n}
              onClick={() => setDaysPractised(daysPractised === n ? null : n)}
            >
              {n}
            </button>
          ))}
        </div>
      </div>

      {weekPoses.length > 0 && (
        <details className="wf-drop">
          <summary className="wf-drop-summary">
            {t('yoga.feedback.dropLabel', 'Any pose you want to leave out?')}
            {dropped.size > 0 && <span className="wf-drop-count"> · {dropped.size}</span>}
          </summary>
          <p className="wf-drop-help">
            {t('yoga.feedback.dropHelp',
               'Anything that hurt or that you would rather not do again. It will not appear in future weeks.')}
          </p>
          <div className="wf-drop-list">
            {weekPoses.map(p => (
              <button
                key={p.id} type="button"
                className={`wf-drop-chip${dropped.has(p.id) ? ' selected' : ''}`}
                aria-pressed={dropped.has(p.id)}
                onClick={() => toggleDropped(p.id)}
                title={p.english || undefined}
              >
                {p.name}
                {p.english && <span className="wf-drop-english">{p.english}</span>}
              </button>
            ))}
          </div>
        </details>
      )}

      {error && <p className="wf-error">{error}</p>}

      <button type="button" className="wf-submit" onClick={submit} disabled={busy}>
        {busy
          ? <><Loader2 size={14} className="wf-spin" /> {t('yoga.feedback.building', 'Building week {{n}}…', { n: nextWeek })}</>
          : <>{t('yoga.feedback.submit', 'Generate week {{n}}', { n: nextWeek })} <ArrowRight size={14} /></>}
      </button>
    </div>
  )
}

export default WeekFeedbackCard
