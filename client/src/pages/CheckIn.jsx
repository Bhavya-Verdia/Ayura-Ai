import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { m, AnimatePresence } from 'framer-motion'
import { Helmet } from 'react-helmet-async'
import API from '../api/client'
import { useAuth } from '../providers/AuthContext'
import { Zap, Moon, Flame, CircleCheck, ClipboardList, Sparkles, TriangleAlert, CircleDot, Circle } from 'lucide-react'
import './CheckIn.css'
import '../components/VikritiCheckIn.css'

// 1-5 lifestyle pulse + engagement (sleep/stress/digestion feed the Vikriti engine)
const PULSE = [
  { id: 'energy',    label: 'Energy',         hints: ['Drained', 'Low', 'Fair', 'Good', 'High'] },
  { id: 'sleep',     label: 'Sleep',          hints: ['Very poor', 'Poor', 'Fair', 'Good', 'Excellent'] },
  { id: 'stress',    label: 'Stress',         hints: ['Extreme', 'High', 'Moderate', 'Low', 'None'] },
  { id: 'digestion', label: 'Digestion',      hints: ['Very poor', 'Poor', 'Fair', 'Good', 'Strong'] },
  { id: 'adherence', label: 'Plan Adherence', hints: ['None', 'A little', 'About half', 'Most', 'All of it'] },
]

const QUICK_SYMPTOMS = [
  { id: 'anxiety_worry', label: 'Anxiety or worry' },
  { id: 'dry_skin_constipation', label: 'Dryness or constipation' },
  { id: 'trouble_sleeping', label: 'Trouble sleeping' },
  { id: 'heartburn_acidity', label: 'Acidity or inflammation' },
  { id: 'irritability', label: 'Irritability' },
  { id: 'weight_gain', label: 'Weight gain or sluggishness' },
  { id: 'low_energy', label: 'Low energy' },
  { id: 'bloating_gas', label: 'Bloating or gas' },
  { id: 'coated_tongue_ama', label: 'Coated tongue' },
  { id: 'feeling_balanced', label: 'Feeling balanced' },
]

const HIST_METRICS = [
  { id: 'energy', label: 'Energy', Icon: Zap, color: 'var(--ayura-amber)' },
  { id: 'sleep', label: 'Sleep', Icon: Moon, color: 'var(--ayura-violet)' },
  { id: 'digestion', label: 'Digestion', Icon: Flame, color: 'var(--ayura-teal)' },
  { id: 'adherence', label: 'Adherence', Icon: CircleCheck, color: 'var(--primary-light)' },
]

function MiniBar({ value, color }) {
  const max = value > 5 ? 10 : 5            // tolerate legacy 1-10 records
  const pct = Math.min(100, ((value - 1) / (max - 1)) * 100)
  return (
    <div className="chk-mini-bar-track">
      <div className="chk-mini-bar-fill" style={{ width: `${pct}%`, background: color }} />
    </div>
  )
}

function HistoryCard({ entry, index }) {
  const date = new Date(entry.timestamp)
  const dateStr = date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
  return (
    <m.div
      className="chk-hist-card"
      initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
    >
      <div className="chk-hist-header"><span className="chk-hist-date">{dateStr}</span></div>
      <div className="chk-hist-metrics">
        {HIST_METRICS.filter(m => entry[m.id] != null).map(m => (
          <div key={m.id} className="chk-hist-metric">
            <div className="chk-hist-metric-row">
              <span style={{ display: 'inline-flex', color: m.color }}><m.Icon size={15} strokeWidth={2} /></span>
              <span className="chk-hist-metric-label">{m.label}</span>
            </div>
            <MiniBar value={entry[m.id]} color={m.color} />
          </div>
        ))}
      </div>
      {entry.symptoms?.length > 0 && (
        <div className="chk-hist-symptoms">
          <span className="chk-hist-tag-label">Symptoms:</span>
          {entry.symptoms.map(s => <span key={s} className="chk-hist-tag">{String(s).replace(/_/g, ' ')}</span>)}
        </div>
      )}
      {entry.what_felt_good && <p className="chk-hist-felt-good">"{entry.what_felt_good}"</p>}
    </m.div>
  )
}

export default function CheckIn() {
  const { profile } = useAuth()
  const isFemale = profile?.gender === 'female'
  const [tab, setTab] = useState('checkin')
  const [pulse, setPulse] = useState({ energy: 3, sleep: 3, stress: 3, digestion: 3, adherence: 3 })
  const [symptoms, setSymptoms] = useState([])
  const [menstrual, setMenstrual] = useState(false)
  const [stageUpdates, setStageUpdates] = useState({})
  const [feltGood, setFeltGood] = useState('')
  const [insight, setInsight] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const { data: history = [], isLoading: histLoading } = useQuery({
    queryKey: ['checkin-history'],
    queryFn: () => API.get('/checkin/history?limit=12').then(r => r.data),
  })

  function toggleSymptom(id) {
    setSymptoms(prev => {
      if (id === 'feeling_balanced') return prev.includes('feeling_balanced') ? [] : ['feeling_balanced']
      const without = prev.filter(s => s !== 'feeling_balanced')
      return without.includes(id) ? without.filter(s => s !== id) : [...without, id]
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true); setError(null)
    try {
      const payload = {
        ...pulse,
        symptoms,
        what_felt_good: feltGood,
        ...(isFemale ? { menstrual_phase: menstrual } : {}),
        ...(Object.keys(stageUpdates).length > 0 ? { disease_stage_updates: stageUpdates } : {}),
      }
      const res = await API.post('/checkin/weekly', payload)
      setInsight(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <Helmet>
        <title>Weekly Check-In — Ayura AI</title>
        <meta name="description" content="Your weekly Ayurvedic check-in — refines your Vikriti and calibrates your plans." />
      </Helmet>

      <div className="chk-root">
        <div className="chk-orb chk-orb-a" aria-hidden="true" />
        <div className="chk-orb chk-orb-b" aria-hidden="true" />

        <div className="chk-container">
          <m.div className="chk-header" initial={{ opacity: 0, y: -16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
            <h1 className="chk-page-title gradient-text">Weekly Check-In</h1>
            <p className="chk-page-sub">A quick snapshot of your week — refines your Vikriti and fine-tunes your plans.</p>
          </m.div>

          <div className="chk-tabs">
            <button className={`chk-tab${tab === 'checkin' ? ' active' : ''}`} onClick={() => { setTab('checkin'); setInsight(null) }}>New Check-In</button>
            <button className={`chk-tab${tab === 'history' ? ' active' : ''}`} onClick={() => setTab('history')}>
              History{history.length > 0 && <span className="chk-tab-badge">{history.length}</span>}
            </button>
          </div>

          <AnimatePresence mode="wait">
            {tab === 'history' ? (
              <m.div key="history" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.3 }}>
                {histLoading ? (
                  <div className="chk-hist-loading">{[...Array(3)].map((_, i) => <div key={i} className="chk-hist-card skeleton" style={{ height: 160 }} />)}</div>
                ) : history.length === 0 ? (
                  <div className="chk-hist-empty"><div style={{ display: 'flex', justifyContent: 'center', color: 'var(--ayura-teal)', marginBottom: 8 }}><ClipboardList size={34} strokeWidth={1.6} /></div><p>No check-ins yet. Submit your first one!</p></div>
                ) : (
                  history.map((entry, i) => <HistoryCard key={i} entry={entry} index={i} />)
                )}
              </m.div>
            ) : insight ? (
              <m.div key="insight" className="chk-insight-card" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }} transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}>
                <div className="chk-insight-icon"><Sparkles size={22} strokeWidth={1.8} /></div>
                <h3 className="chk-insight-title">Vikriti Updated</h3>
                <p className="chk-insight-text">{insight.insight}</p>
                {insight.adapted_plans?.length > 0 && (
                  <div className="chk-adapted-box">
                    <span className="chk-adapted-label">Plans refreshed (your imbalance shifted):</span>
                    <div className="chk-adapted-tags">{insight.adapted_plans.map(p => <span key={p} className="chk-adapted-tag">{p}</span>)}</div>
                  </div>
                )}
                <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>
                  <button className="btn btn-secondary chk-back-btn" onClick={() => { setInsight(null); setSymptoms([]); setStageUpdates({}); setFeltGood('') }}>New Check-In</button>
                  <button className="btn btn-secondary chk-back-btn" onClick={() => { setInsight(null); setTab('history') }}>View History</button>
                </div>
              </m.div>
            ) : (
              <m.form key="form" className="chk-form" onSubmit={handleSubmit} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} transition={{ duration: 0.4 }}>
                {error && <div className="chk-error" style={{ display: 'flex', alignItems: 'center', gap: 6 }}><TriangleAlert size={15} strokeWidth={2} /> {error}</div>}

                {/* ── Lifestyle pulse (1-5 emoji) ── */}
                <div className="vci-pulse-section" style={{ marginBottom: 20 }}>
                  {PULSE.map(field => (
                    <div key={field.id} className="vci-pulse-row">
                      <span className="vci-pulse-label">{field.label}</span>
                      <div className="vci-pulse-icons">
                        {field.hints.map((hint, i) => (
                          <button key={i} type="button"
                            className={`vci-pulse-btn${pulse[field.id] === i + 1 ? ' selected' : ''}`}
                            onClick={() => setPulse(p => ({ ...p, [field.id]: i + 1 }))}
                            title={hint} aria-label={`${field.label}: ${hint}`}>
                            {i + 1}
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>

                {isFemale && (
                  <div className="vci-menstrual-row">
                    <button type="button" className={`vci-menstrual-btn${menstrual ? ' active' : ''}`} onClick={() => setMenstrual(p => !p)}>
                      <span style={{ display: 'inline-flex', verticalAlign: '-2px', color: menstrual ? 'var(--ayura-rose)' : 'inherit' }}>{menstrual ? <CircleDot size={15} strokeWidth={2} /> : <Circle size={15} strokeWidth={2} />}</span> On or near my period
                    </button>
                    <span className="vci-menstrual-hint">Pitta naturally rises — we factor this in</span>
                  </div>
                )}

                <p className="vci-sub" style={{ marginTop: 8 }}>Any symptoms this week?</p>
                <div className="vci-chips">
                  {QUICK_SYMPTOMS.map(s => (
                    <m.button key={s.id} type="button" whileTap={{ scale: 0.96 }}
                      className={`vci-chip ${symptoms.includes(s.id) ? 'selected' : ''}`} onClick={() => toggleSymptom(s.id)}>
                      {s.label}
                    </m.button>
                  ))}
                </div>

                {profile?.medical_history?.length > 0 && (
                  <div className="vci-disease-stage-section">
                    <h4 className="vci-section-title">Disease Progress Check</h4>
                    <p className="vci-sub">How are your conditions evolving?</p>
                    {profile.medical_history.slice(0, 5).map(cid => (
                      <div key={cid} className="vci-stage-row">
                        <span className="vci-stage-label">{cid.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</span>
                        <div className="vci-stage-selects">
                          <select className="vci-stage-select" value={stageUpdates[cid]?.duration || ''}
                            onChange={e => setStageUpdates(p => ({ ...p, [cid]: { ...p[cid], duration: e.target.value } }))}>
                            <option value="">Duration…</option>
                            <option value="months">Less than 1 year</option>
                            <option value="1-3y">1–3 years</option>
                            <option value="3-5y">3–5 years</option>
                            <option value="5y+">5+ years</option>
                          </select>
                          <select className="vci-stage-select" value={stageUpdates[cid]?.trajectory || ''}
                            onChange={e => setStageUpdates(p => ({ ...p, [cid]: { ...p[cid], trajectory: e.target.value } }))}>
                            <option value="">Trend…</option>
                            <option value="worsening">Getting worse</option>
                            <option value="stable">Stable</option>
                            <option value="improving">Improving</option>
                          </select>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                <div className="chk-text-inputs">
                  <div className="input-group">
                    <label>What felt good this week?</label>
                    <textarea placeholder="Share your wins, big or small..." rows={3} value={feltGood} onChange={e => setFeltGood(e.target.value)} />
                  </div>
                </div>

                <m.button type="submit" className="btn btn-primary chk-submit-btn" disabled={loading} whileTap={{ scale: 0.98 }}>
                  {loading ? (<><span className="spinner" style={{ width: 18, height: 18, borderWidth: 2 }} /> Analyzing…</>) : 'Submit & Refine My Vikriti'}
                </m.button>
              </m.form>
            )}
          </AnimatePresence>
        </div>
      </div>
    </>
  )
}
