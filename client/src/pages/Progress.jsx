import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { Helmet } from 'react-helmet-async'
import { progressAPI } from '../api/client'
import { toast } from 'sonner'
import './Progress.css'

const MOOD_OPTIONS = [
  { value: 'great',    label: 'Great',    emoji: '😄' },
  { value: 'good',     label: 'Good',     emoji: '🙂' },
  { value: 'neutral',  label: 'Okay',     emoji: '😐' },
  { value: 'tired',    label: 'Tired',    emoji: '😴' },
  { value: 'stressed', label: 'Stressed', emoji: '😰' },
]

const TREND_CONFIG = {
  losing_weight:      { label: 'Losing Weight',  icon: '📉', color: 'var(--ayura-teal)' },
  gaining_weight:     { label: 'Gaining Weight', icon: '📈', color: 'var(--ayura-amber)' },
  stable:             { label: 'Stable',         icon: '➡️',  color: 'var(--primary-light)' },
  insufficient_data:  { label: 'Not enough data',icon: '📊', color: 'var(--text-muted)' },
}

function StatCard({ icon, label, value, sub, color }) {
  return (
    <motion.div
      className="prg-stat-card"
      style={{ '--stat-color': color || 'var(--ayura-teal)' }}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="prg-stat-icon">{icon}</div>
      <div className="prg-stat-body">
        <div className="prg-stat-value">{value ?? '—'}</div>
        <div className="prg-stat-label">{label}</div>
        {sub && <div className="prg-stat-sub">{sub}</div>}
      </div>
    </motion.div>
  )
}

function MiniBar({ value, max = 10, color }) {
  const pct = Math.min(100, ((value || 0) / max) * 100)
  return (
    <div className="prg-mini-bar-track">
      <div className="prg-mini-bar-fill" style={{ width: `${pct}%`, background: color || 'var(--ayura-teal)' }} />
    </div>
  )
}

function LogEntry({ log, index }) {
  const moodInfo = MOOD_OPTIONS.find(m => m.value === log.mood)
  const date = new Date(log.date)
  const dateStr = date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
  return (
    <motion.div
      className="prg-log-entry"
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.35, delay: index * 0.05 }}
    >
      <div className="prg-log-date">{dateStr}</div>
      <div className="prg-log-metrics">
        {log.weight_kg && (
          <div className="prg-log-metric">
            <span className="prg-log-metric-label">Weight</span>
            <span className="prg-log-metric-val">{log.weight_kg} kg</span>
          </div>
        )}
        {log.adherence_percent != null && (
          <div className="prg-log-metric">
            <span className="prg-log-metric-label">Adherence</span>
            <span className="prg-log-metric-val">{log.adherence_percent}%</span>
            <MiniBar value={log.adherence_percent} max={100} color="var(--primary-light)" />
          </div>
        )}
        {log.mood && (
          <div className="prg-log-metric">
            <span className="prg-log-metric-label">Mood</span>
            <span className="prg-log-metric-val">{moodInfo?.emoji} {moodInfo?.label || log.mood}</span>
          </div>
        )}
      </div>
    </motion.div>
  )
}

export default function Progress() {
  const qc = useQueryClient()
  const [showLogForm, setShowLogForm] = useState(false)
  const [form, setForm] = useState({ weight_kg: '', adherence_percent: '', mood: 'good', plan_feedback: '' })

  const { data: summary, isLoading, isError } = useQuery({
    queryKey: ['progress-summary'],
    queryFn: () => progressAPI.getSummary().then(r => r.data),
    staleTime: 5 * 60 * 1000,
  })

  const { data: logs = [] } = useQuery({
    queryKey: ['progress-logs'],
    queryFn: () => progressAPI.getLogs(30).then(r => r.data),
    staleTime: 5 * 60 * 1000,
  })

  const logMutation = useMutation({
    mutationFn: (data) => progressAPI.log(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['progress-summary'] })
      qc.invalidateQueries({ queryKey: ['progress-logs'] })
      setShowLogForm(false)
      setForm({ weight_kg: '', adherence_percent: '', mood: 'good', plan_feedback: '' })
      toast.success('Progress logged!')
    },
    onError: () => toast.error('Failed to log progress. Try again.'),
  })

  function handleLog(e) {
    e.preventDefault()
    const payload = {}
    if (form.weight_kg)         payload.weight_kg = parseFloat(form.weight_kg)
    if (form.adherence_percent) payload.adherence_percent = parseInt(form.adherence_percent, 10)
    if (form.mood)              payload.mood = form.mood
    if (form.plan_feedback)     payload.plan_feedback = form.plan_feedback
    logMutation.mutate(payload)
  }

  const trend = TREND_CONFIG[summary?.trend] || TREND_CONFIG.insufficient_data
  const streak = summary?.streak_data?.current_streak_days ?? 0
  const totalEntries = summary?.streak_data?.total_entries ?? summary?.current?.total_entries ?? 0
  const weight = summary?.current?.weight_kg
  const insight = summary?.weekly_insight

  return (
    <>
      <Helmet>
        <title>Progress — Ayura AI</title>
        <meta name="description" content="Track your wellness progress, weight trends, and adherence streaks." />
      </Helmet>

      <div className="prg-root">
        <div className="prg-orb prg-orb-a" aria-hidden="true" />
        <div className="prg-orb prg-orb-b" aria-hidden="true" />

        <div className="prg-container">
          {/* Header */}
          <motion.div className="prg-header" initial={{ opacity: 0, y: -16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
            <h1 className="prg-title gradient-text">Progress</h1>
            <p className="prg-sub">Track your wellness journey day by day.</p>
            <motion.button
              className="btn btn-primary prg-log-btn"
              onClick={() => setShowLogForm(v => !v)}
              whileTap={{ scale: 0.97 }}
            >
              {showLogForm ? '✕ Cancel' : '+ Log Today'}
            </motion.button>
          </motion.div>

          {/* Quick log form */}
          <AnimatePresence>
            {showLogForm && (
              <motion.form
                className="prg-log-form"
                onSubmit={handleLog}
                initial={{ opacity: 0, height: 0, marginBottom: 0 }}
                animate={{ opacity: 1, height: 'auto', marginBottom: 32 }}
                exit={{ opacity: 0, height: 0, marginBottom: 0 }}
                transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
              >
                <h3 className="prg-log-form-title">Log Today's Progress</h3>
                <div className="prg-log-grid">
                  <div className="input-group">
                    <label>Weight (kg)</label>
                    <input
                      type="number" step="0.1" min="20" max="300"
                      placeholder="e.g. 72.5"
                      value={form.weight_kg}
                      onChange={e => setForm(f => ({ ...f, weight_kg: e.target.value }))}
                    />
                  </div>
                  <div className="input-group">
                    <label>Plan Adherence (%)</label>
                    <input
                      type="number" min="0" max="100"
                      placeholder="e.g. 85"
                      value={form.adherence_percent}
                      onChange={e => setForm(f => ({ ...f, adherence_percent: e.target.value }))}
                    />
                  </div>
                </div>

                <div className="input-group">
                  <label>Mood</label>
                  <div className="prg-mood-chips">
                    {MOOD_OPTIONS.map(m => (
                      <button
                        key={m.value}
                        type="button"
                        className={`prg-mood-chip${form.mood === m.value ? ' active' : ''}`}
                        onClick={() => setForm(f => ({ ...f, mood: m.value }))}
                      >
                        {m.emoji} {m.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="input-group">
                  <label>Notes (optional)</label>
                  <textarea
                    rows={2}
                    placeholder="How did your plan feel today?"
                    value={form.plan_feedback}
                    onChange={e => setForm(f => ({ ...f, plan_feedback: e.target.value }))}
                  />
                </div>

                <motion.button
                  type="submit"
                  className="btn btn-primary"
                  disabled={logMutation.isPending}
                  whileTap={{ scale: 0.97 }}
                >
                  {logMutation.isPending ? 'Saving...' : 'Save Entry'}
                </motion.button>
              </motion.form>
            )}
          </AnimatePresence>

          {isLoading && (
            <div className="prg-loading">
              <div className="prg-stat-row">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="prg-stat-card skeleton" style={{ height: 90 }} />
                ))}
              </div>
            </div>
          )}

          {isError && (
            <div className="prg-empty">
              <div className="prg-empty-icon">⚠️</div>
              <p>Failed to load progress data. Check your connection.</p>
            </div>
          )}

          {!isLoading && !isError && summary && (
            <>
              {/* Stats row */}
              <div className="prg-stat-row">
                <StatCard icon="🔥" label="Day Streak" value={streak > 0 ? `${streak}d` : '0d'} sub="consecutive days logged" color="var(--ayura-amber)" />
                <StatCard icon="📋" label="Total Entries" value={totalEntries} sub="logs recorded" color="var(--primary-light)" />
                <StatCard icon="⚖️" label="Current Weight" value={weight ? `${weight} kg` : '—'} sub={summary.current?.bmi_category || ''} color="var(--ayura-violet)" />
                <StatCard icon={trend.icon} label="Weight Trend" value={trend.label} color={trend.color} />
              </div>

              {/* LLM Insight */}
              {insight && (
                <motion.div
                  className="prg-insight-card"
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: 0.2 }}
                >
                  <div className="prg-insight-icon">✨</div>
                  <div className="prg-insight-body">
                    <div className="prg-insight-label">AI Weekly Insight</div>
                    <p className="prg-insight-text">{insight}</p>
                  </div>
                </motion.div>
              )}

              {/* Recent entries */}
              {logs.length === 0 ? (
                <div className="prg-empty">
                  <div className="prg-empty-icon">📊</div>
                  <p className="prg-empty-title">No entries yet</p>
                  <p className="prg-empty-sub">Click "+ Log Today" to record your first progress entry.</p>
                </div>
              ) : (
                <div className="prg-logs-section">
                  <h2 className="prg-logs-title">Recent Entries <span className="prg-logs-count">{logs.length}</span></h2>
                  <div className="prg-logs-list">
                    {logs.map((log, i) => (
                      <LogEntry key={log.id || i} log={log} index={i} />
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </>
  )
}
