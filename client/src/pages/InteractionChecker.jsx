import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Helmet } from 'react-helmet-async'
import { useAuth } from '../providers/AuthContext'
import { plansAPI } from '../api/client'
import './InteractionChecker.css'

const SEVERITY = {
  high:     { label: 'High',     color: '#f87171', bg: 'rgba(248,113,113,0.1)', icon: '⛔' },
  moderate: { label: 'Moderate', color: '#fb923c', bg: 'rgba(251,146,60,0.1)',  icon: '⚠️' },
  medium:   { label: 'Moderate', color: '#fb923c', bg: 'rgba(251,146,60,0.1)',  icon: '⚠️' },
  low:      { label: 'Low',      color: '#fbbf24', bg: 'rgba(251,191,36,0.1)',  icon: '⚠️' },
}

function sev(s) {
  return SEVERITY[(s || 'moderate').toLowerCase()] || SEVERITY.moderate
}

// ── Chip input ───────────────────────────────────────────────
function ChipInput({ label, hint, placeholder, items, setItems }) {
  const [draft, setDraft] = useState('')

  const add = () => {
    const parts = draft.split(',').map(s => s.trim()).filter(Boolean)
    if (!parts.length) return
    setItems(prev => [...new Set([...prev, ...parts])])
    setDraft('')
  }
  const remove = (item) => setItems(prev => prev.filter(i => i !== item))

  return (
    <div className="ic-field">
      <label className="ic-label">{label}</label>
      {hint && <p className="ic-hint">{hint}</p>}
      <div className="ic-chip-row">
        {items.map(item => (
          <span key={item} className="ic-chip">
            {item}
            <button type="button" onClick={() => remove(item)} aria-label={`Remove ${item}`}>✕</button>
          </span>
        ))}
      </div>
      <div className="ic-add-row">
        <input
          type="text"
          value={draft}
          placeholder={placeholder}
          onChange={e => setDraft(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); add() } }}
        />
        <button type="button" className="btn btn-secondary btn-sm" onClick={add}>Add</button>
      </div>
    </div>
  )
}

export default function InteractionChecker() {
  const { user } = useAuth()
  const [medications, setMedications] = useState(user?.current_medications || [])
  const [herbs, setHerbs] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  const canCheck = herbs.length > 0 && !loading

  async function runCheck() {
    setError('')
    setResult(null)
    setLoading(true)
    try {
      const res = await plansAPI.checkInteractions(herbs, medications)
      setResult(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not run the interaction check. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const warnings = result?.warnings || []
  const isSafe = result && result.status === 'safe'

  return (
    <>
      <Helmet>
        <title>Interaction Checker — Ayura AI</title>
        <meta name="description" content="Check your medications against Ayurvedic herbs and formulations for known drug–herb interactions before you take them." />
      </Helmet>

      <div className="ic-root">
        <div className="ic-orb ic-orb-a" aria-hidden="true" />
        <div className="ic-orb ic-orb-b" aria-hidden="true" />

        <div className="ic-container">
          <motion.div className="ic-header" initial={{ opacity: 0, y: -16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
            <h1 className="ic-title gradient-text">Interaction Checker</h1>
            <p className="ic-sub">Before you take an Ayurvedic herb or formulation, check it against your medications for known drug–herb interactions.</p>
          </motion.div>

          <motion.div className="ic-card" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.05 }}>
            <ChipInput
              label="Your medications"
              hint="Prefilled from your profile — edit as needed. Allopathic drug names work best (e.g. metformin, warfarin)."
              placeholder="Add a medication and press Enter"
              items={medications}
              setItems={setMedications}
            />
            <ChipInput
              label="Herb or formulation to check"
              hint="e.g. ashwagandha, turmeric, fenugreek, triphala"
              placeholder="Add an herb and press Enter"
              items={herbs}
              setItems={setHerbs}
            />

            <motion.button
              className="btn btn-primary ic-check-btn"
              onClick={runCheck}
              disabled={!canCheck}
              whileTap={{ scale: 0.97 }}
            >
              {loading
                ? <><span className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} /> Checking…</>
                : '🛡 Check safety'}
            </motion.button>
            {herbs.length === 0 && <p className="ic-need-herb">Add at least one herb to check.</p>}
          </motion.div>

          <AnimatePresence>
            {error && (
              <motion.div className="ic-error" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                ⚠️ {error}
              </motion.div>
            )}
          </AnimatePresence>

          <AnimatePresence mode="wait">
            {result && (
              <motion.div
                key={result.status + warnings.length}
                className="ic-result"
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.4 }}
              >
                {isSafe ? (
                  <div className="ic-safe-card">
                    <span className="ic-safe-icon">✅</span>
                    <div>
                      <div className="ic-safe-title">No known interactions detected</div>
                      <p className="ic-safe-text">{result.detailed_explanation}</p>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="ic-warn-banner">
                      <span>⚠️</span>
                      <span>{warnings.length} potential interaction{warnings.length !== 1 ? 's' : ''} found — review carefully and consult your physician.</span>
                    </div>

                    <div className="ic-warn-list">
                      {warnings.map((w, i) => {
                        const s = sev(w.severity)
                        return (
                          <motion.div
                            key={i}
                            className="ic-warn-card"
                            style={{ borderColor: s.color + '55', background: s.bg }}
                            initial={{ opacity: 0, x: -12 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.05 + i * 0.06 }}
                          >
                            <div className="ic-warn-top">
                              <span className="ic-warn-herb">{s.icon} {w.herb}</span>
                              <span className="ic-warn-x">×</span>
                              <span className="ic-warn-med">{String(w.medication_category || '').replace(/_/g, ' ')}</span>
                              <span className="ic-sev-badge" style={{ color: s.color, borderColor: s.color + '66' }}>{s.label}</span>
                            </div>
                            {w.effect && <p className="ic-warn-effect">{w.effect}</p>}
                            {w.recommendation && <p className="ic-warn-rec"><strong>Recommendation:</strong> {w.recommendation}</p>}
                            {w.alternative && <p className="ic-warn-alt"><strong>Safer alternative:</strong> {w.alternative}</p>}
                          </motion.div>
                        )
                      })}
                    </div>

                    {result.detailed_explanation && (
                      <div className="ic-explain">
                        <div className="ic-explain-label">✦ Safety guidance</div>
                        <p>{result.detailed_explanation}</p>
                      </div>
                    )}
                  </>
                )}

                {result.general_warnings?.length > 0 && (
                  <div className="ic-general">
                    <div className="ic-general-label">General precautions</div>
                    <ul>
                      {result.general_warnings.map((g, i) => <li key={i}>{g}</li>)}
                    </ul>
                  </div>
                )}

                <p className="ic-disclaimer">
                  This deterministic screen covers documented drug–herb interactions only — absence of a warning is not a guarantee of safety. Always consult a qualified physician or registered Vaidya before combining medications with Ayurvedic herbs.
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </>
  )
}
