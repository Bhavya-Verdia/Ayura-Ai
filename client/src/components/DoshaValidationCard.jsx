import { useState } from 'react'
import { motion } from 'framer-motion'
import { profileAPI } from '../api/client'
import './DoshaValidationCard.css'

const DOSHA_QUESTIONS = {
  vata: 'Have you felt less anxious, better rested, or more grounded over the past 2 weeks?',
  pitta: 'Have you felt less irritable, with reduced acidity or inflammation, over the past 2 weeks?',
  kapha: 'Have you felt more energised, lighter, or less congested over the past 2 weeks?',
}

const DOSHA_COLORS = {
  vata: '#818cf8',
  pitta: '#fb923c',
  kapha: '#34d399',
}

export default function DoshaValidationCard({ vikritiDominant, onDone }) {
  const [status, setStatus] = useState('idle') // idle | submitting | done

  const question = DOSHA_QUESTIONS[vikritiDominant] ||
    'Have your wellness plans helped you feel more balanced over the past 2 weeks?'
  const color = DOSHA_COLORS[vikritiDominant] || 'var(--ayura-teal)'

  async function submit(improved) {
    setStatus('submitting')
    try {
      await profileAPI.doshaValidation({ improved })
    } catch {
      // non-fatal
    } finally {
      setStatus('done')
      onDone?.()
    }
  }

  if (status === 'done') return null

  return (
    <motion.div
      className="dvc-card"
      style={{ borderLeftColor: color }}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <div className="dvc-header">
        <span className="dvc-icon">📅</span>
        <span className="dvc-label">2-Week Check-In</span>
      </div>
      <p className="dvc-question">{question}</p>
      <div className="dvc-actions">
        <button
          type="button"
          className="btn btn-primary btn-sm"
          disabled={status === 'submitting'}
          onClick={() => submit(true)}
        >
          Yes, feeling better
        </button>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          disabled={status === 'submitting'}
          onClick={() => submit(false)}
        >
          Not yet
        </button>
        <button
          type="button"
          className="dvc-later"
          disabled={status === 'submitting'}
          onClick={() => onDone?.()}
        >
          Remind me later
        </button>
      </div>
    </motion.div>
  )
}
