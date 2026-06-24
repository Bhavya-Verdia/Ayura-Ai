import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { Helmet } from 'react-helmet-async'
import API from '../api/client'
import './CheckIn.css'

const METRICS = [
  { id: 'energy',    label: 'Energy Levels',  icon: '⚡', color: 'var(--ayura-amber)' },
  { id: 'digestion', label: 'Digestion',       icon: '🔥', color: 'var(--ayura-teal)' },
  { id: 'sleep',     label: 'Sleep Quality',   icon: '🌙', color: 'var(--ayura-violet)' },
  { id: 'adherence', label: 'Plan Adherence',  icon: '✅', color: 'var(--primary-light)' },
]

function MetricMiniBar({ value, color }) {
  const pct = Math.min(100, ((value - 1) / 9) * 100)
  return (
    <div className="chk-mini-bar-track">
      <div className="chk-mini-bar-fill" style={{ width: `${pct}%`, background: color }} />
    </div>
  )
}

function HistoryCard({ entry, index }) {
  const date = new Date(entry.timestamp)
  const dateStr = date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
  const avgScore = Math.round((entry.energy + entry.digestion + entry.sleep + entry.adherence) / 4)
  return (
    <motion.div
      className="chk-hist-card"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: index * 0.05 }}
    >
      <div className="chk-hist-header">
        <span className="chk-hist-date">{dateStr}</span>
        <span className="chk-hist-avg">avg {avgScore}/10</span>
      </div>
      <div className="chk-hist-metrics">
        {METRICS.map(m => (
          <div key={m.id} className="chk-hist-metric">
            <div className="chk-hist-metric-row">
              <span className="chk-hist-metric-icon">{m.icon}</span>
              <span className="chk-hist-metric-label">{m.label}</span>
              <span className="chk-hist-metric-val" style={{ color: m.color }}>{entry[m.id]}/10</span>
            </div>
            <MetricMiniBar value={entry[m.id]} color={m.color} />
          </div>
        ))}
      </div>
      {entry.symptoms?.length > 0 && (
        <div className="chk-hist-symptoms">
          <span className="chk-hist-tag-label">Symptoms:</span>
          {entry.symptoms.map((s, i) => <span key={i} className="chk-hist-tag">{s}</span>)}
        </div>
      )}
      {entry.what_felt_good && (
        <p className="chk-hist-felt-good">"{entry.what_felt_good}"</p>
      )}
    </motion.div>
  )
}

export default function CheckIn() {
  const [tab, setTab] = useState('checkin') // 'checkin' | 'history'
  const [formData, setFormData] = useState({
    energy: 5, digestion: 5, sleep: 5, adherence: 5, symptoms: '', what_felt_good: ''
  })
  const [insight, setInsight] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const { data: history = [], isLoading: histLoading } = useQuery({
    queryKey: ['checkin-history'],
    queryFn: () => API.get('/checkin/history?limit=12').then(r => r.data),
    enabled: tab === 'history',
    staleTime: 2 * 60 * 1000,
  })

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const payload = {
        ...formData,
        symptoms: formData.symptoms ? formData.symptoms.split(',').map(s => s.trim()).filter(Boolean) : []
      }
      const res = await API.post('/checkin/weekly', payload)
      setInsight(res.data)
    } catch {
      setError('Failed to submit check-in. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleSliderChange = (field, val) => {
    setFormData(prev => ({ ...prev, [field]: parseInt(val, 10) }))
  }

  return (
    <>
      <Helmet>
        <title>Weekly Check-In — Ayura AI</title>
        <meta name="description" content="Log your weekly health check-in to calibrate your Ayura AI wellness plan." />
      </Helmet>

      <div className="chk-root">
        <div className="chk-orb chk-orb-a" aria-hidden="true" />
        <div className="chk-orb chk-orb-b" aria-hidden="true" />

        <div className="chk-container">
          <motion.div
            className="chk-header"
            initial={{ opacity: 0, y: -16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            <h1 className="chk-page-title gradient-text">Weekly Check-In</h1>
            <p className="chk-page-sub">Calibrate your AI wellness plan with your latest bio-feedback.</p>
          </motion.div>

          {/* Tab switcher */}
          <div className="chk-tabs">
            <button
              className={`chk-tab${tab === 'checkin' ? ' active' : ''}`}
              onClick={() => { setTab('checkin'); setInsight(null) }}
            >
              New Check-In
            </button>
            <button
              className={`chk-tab${tab === 'history' ? ' active' : ''}`}
              onClick={() => setTab('history')}
            >
              History
              {history.length > 0 && <span className="chk-tab-badge">{history.length}</span>}
            </button>
          </div>

          <AnimatePresence mode="wait">
            {tab === 'history' ? (
              <motion.div
                key="history"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.3 }}
              >
                {histLoading ? (
                  <div className="chk-hist-loading">
                    {[...Array(3)].map((_, i) => (
                      <div key={i} className="chk-hist-card skeleton" style={{ height: 160 }} />
                    ))}
                  </div>
                ) : history.length === 0 ? (
                  <div className="chk-hist-empty">
                    <div style={{ fontSize: '3rem' }}>📋</div>
                    <p>No check-ins yet. Submit your first one!</p>
                  </div>
                ) : (
                  history.map((entry, i) => <HistoryCard key={i} entry={entry} index={i} />)
                )}
              </motion.div>
            ) : insight ? (
              <motion.div
                key="insight"
                className="chk-insight-card"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
              >
                <div className="chk-insight-icon">✨</div>
                <h3 className="chk-insight-title">AI Analysis Complete</h3>
                <p className="chk-insight-text">{insight.insight}</p>

                {insight.adapted_plans?.length > 0 && (
                  <div className="chk-adapted-box">
                    <span className="chk-adapted-label">Plans Updated:</span>
                    <div className="chk-adapted-tags">
                      {insight.adapted_plans.map(plan => (
                        <span key={plan} className="chk-adapted-tag">{plan}</span>
                      ))}
                    </div>
                  </div>
                )}

                <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>
                  <button className="btn btn-secondary chk-back-btn" onClick={() => setInsight(null)}>
                    New Check-In
                  </button>
                  <button className="btn btn-secondary chk-back-btn" onClick={() => { setInsight(null); setTab('history') }}>
                    View History
                  </button>
                </div>
              </motion.div>
            ) : (
              <motion.form
                key="form"
                className="chk-form"
                onSubmit={handleSubmit}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.4 }}
              >
                {error && (
                  <div className="chk-error">
                    ⚠️ {error}
                  </div>
                )}

                <div className="chk-metrics-grid">
                  {METRICS.map(metric => (
                    <div key={metric.id} className="chk-metric-card">
                      <div className="chk-metric-header">
                        <span className="chk-metric-icon">{metric.icon}</span>
                        <label className="chk-metric-label">{metric.label}</label>
                        <span className="chk-metric-val" style={{ color: metric.color, background: `${metric.color}18` }}>
                          {formData[metric.id]}/10
                        </span>
                      </div>
                      <input
                        type="range"
                        min="1" max="10"
                        className="chk-slider"
                        value={formData[metric.id]}
                        onChange={e => handleSliderChange(metric.id, e.target.value)}
                        style={{ '--val': `${((formData[metric.id] - 1) / 9) * 100}%`, '--track-color': metric.color }}
                      />
                      <div className="chk-slider-labels">
                        <span>Low</span>
                        <span>High</span>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="chk-text-inputs">
                  <div className="input-group">
                    <label>Any new symptoms? (comma separated)</label>
                    <input
                      type="text"
                      placeholder="e.g. slight headache, bloating..."
                      value={formData.symptoms}
                      onChange={e => setFormData({...formData, symptoms: e.target.value})}
                    />
                  </div>

                  <div className="input-group">
                    <label>What felt good this week?</label>
                    <textarea
                      placeholder="Share your wins, big or small..."
                      rows={3}
                      value={formData.what_felt_good}
                      onChange={e => setFormData({...formData, what_felt_good: e.target.value})}
                    />
                  </div>
                </div>

                <motion.button
                  type="submit"
                  className="btn btn-primary chk-submit-btn"
                  disabled={loading}
                  whileTap={{ scale: 0.98 }}
                >
                  {loading ? (
                    <><span className="spinner" style={{ width: 18, height: 18, borderWidth: 2 }} /> Analyzing...</>
                  ) : (
                    'Submit & Calibrate Plan'
                  )}
                </motion.button>
              </motion.form>
            )}
          </AnimatePresence>
        </div>
      </div>
    </>
  )
}
