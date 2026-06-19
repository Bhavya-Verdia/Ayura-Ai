import { useState } from 'react'
import { motion } from 'framer-motion'
import { useQueryClient } from '@tanstack/react-query'
import { profileAPI } from '../api/client'
import { useAuth } from '../providers/AuthContext'
import './VikritiCheckIn.css'

const QUICK_SYMPTOMS = [
  { id: 'anxiety_worry', icon: '🌀', label: 'Anxiety or worry' },
  { id: 'dry_skin_constipation', icon: '🌵', label: 'Dryness or constipation' },
  { id: 'trouble_sleeping', icon: '🌙', label: 'Trouble sleeping' },
  { id: 'heartburn_acidity', icon: '🔥', label: 'Acidity or inflammation' },
  { id: 'irritability', icon: '⚡', label: 'Irritability' },
  { id: 'weight_gain', icon: '🏔️', label: 'Weight gain or sluggishness' },
  { id: 'low_energy', icon: '😶', label: 'Low energy' },
  { id: 'bloating_gas', icon: '💨', label: 'Bloating or gas' },
  { id: 'coated_tongue_ama', icon: '👅', label: 'Coated tongue' },
  { id: 'morning_heaviness', icon: '🪨', label: 'Morning heaviness' },
  { id: 'feeling_balanced', icon: '✨', label: 'Feeling balanced' },
]

const PULSE_FIELDS = [
  {
    id: 'sleep_this_week',
    label: 'Sleep',
    icons: ['😫', '😴', '😐', '😊', '✨'],
    hints: ['Very poor', 'Poor', 'Fair', 'Good', 'Excellent'],
  },
  {
    id: 'stress_this_week',
    label: 'Stress',
    icons: ['🌋', '😰', '😐', '😌', '🧘'],
    hints: ['Extreme', 'High', 'Moderate', 'Low', 'None'],
  },
  {
    id: 'digestion_this_week',
    label: 'Digestion',
    icons: ['💨', '😣', '😐', '😊', '🌿'],
    hints: ['Very poor', 'Poor', 'Fair', 'Good', 'Strong'],
  },
]

export default function VikritiCheckIn({ onDismiss }) {
  const [selected, setSelected] = useState([])
  const [pulse, setPulse] = useState({ sleep_this_week: null, stress_this_week: null, digestion_this_week: null })
  const [status, setStatus] = useState('idle')
  const [menstrualPhase, setMenstrualPhase] = useState(false)
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const isFemale = user?.gender === 'female'

  function toggle(id) {
    setSelected((prev) => {
      if (id === 'feeling_balanced') return ['feeling_balanced']
      const without = prev.filter((s) => s !== 'feeling_balanced')
      return without.includes(id) ? without.filter((s) => s !== id) : [...without, id]
    })
  }

  function setPulseField(field, value) {
    setPulse(prev => ({ ...prev, [field]: value }))
  }

  async function submit() {
    setStatus('submitting')
    try {
      const res = await profileAPI.vikritiCheckIn({
        current_symptoms: selected,
        ...pulse,
        ...(isFemale ? { menstrual_phase: menstrualPhase } : {}),
      })
      queryClient.setQueryData(['auth-user'], (old) => old ? { ...old, data: res.data } : old)
      setStatus('done')
    } catch {
      setStatus('idle')
    }
  }

  const canSubmit = selected.length > 0 || Object.values(pulse).some(v => v !== null)

  if (status === 'done') {
    return (
      <motion.div className="vci-card" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
        <div className="vci-done">
          <span className="vci-done-icon">✅</span>
          <span className="vci-done-text">Vikriti updated — your plans will reflect this.</span>
        </div>
      </motion.div>
    )
  }

  return (
    <motion.div className="vci-card" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
      <div className="vci-header">
        <span className="vci-pulse" />
        <span className="vci-title">Weekly Vikriti Check-in</span>
        {onDismiss && (
          <button type="button" className="vci-dismiss" onClick={onDismiss} aria-label="Dismiss">✕</button>
        )}
      </div>
      <p className="vci-sub">A quick snapshot of this week — fine-tunes your wellness plans.</p>

      {/* ── Lifestyle pulse ── */}
      <div className="vci-pulse-section">
        {PULSE_FIELDS.map((field) => (
          <div key={field.id} className="vci-pulse-row">
            <span className="vci-pulse-label">{field.label}</span>
            <div className="vci-pulse-icons">
              {field.icons.map((icon, i) => (
                <button
                  key={i}
                  type="button"
                  className={`vci-pulse-btn${pulse[field.id] === i + 1 ? ' selected' : ''}`}
                  onClick={() => setPulseField(field.id, i + 1)}
                  title={field.hints[i]}
                  aria-label={`${field.label}: ${field.hints[i]}`}
                >
                  {icon}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      {isFemale && (
        <div className="vci-menstrual-row">
          <button
            type="button"
            className={`vci-menstrual-btn${menstrualPhase ? ' active' : ''}`}
            onClick={() => setMenstrualPhase(p => !p)}
          >
            {menstrualPhase ? '🔴' : '⭕'} On or near my period
          </button>
          <span className="vci-menstrual-hint">Pitta naturally rises — we factor this in automatically</span>
        </div>
      )}

      <p className="vci-sub" style={{ marginTop: 16 }}>Any symptoms this week?</p>
      <div className="vci-chips">
        {QUICK_SYMPTOMS.map((s) => (
          <motion.button
            key={s.id}
            type="button"
            className={`vci-chip ${selected.includes(s.id) ? 'selected' : ''}`}
            onClick={() => toggle(s.id)}
            whileTap={{ scale: 0.96 }}
          >
            <span>{s.icon}</span> {s.label}
          </motion.button>
        ))}
      </div>

      <div className="vci-footer">
        <motion.button
          type="button"
          className="btn btn-primary"
          onClick={submit}
          disabled={status === 'submitting' || !canSubmit}
          whileTap={{ scale: 0.97 }}
        >
          {status === 'submitting' ? 'Updating…' : 'Update My Vikriti'}
        </motion.button>
      </div>
    </motion.div>
  )
}
