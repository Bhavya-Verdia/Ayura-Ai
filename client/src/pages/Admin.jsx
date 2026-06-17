import { useState, Suspense } from 'react'
import { AnimatePresence } from 'framer-motion'
import { adminAPI } from '../api/client'
import { Helmet } from 'react-helmet-async'
import React from 'react'
import './Dashboard.css'

const LazyParticleField = React.lazy(() => import('../components/ParticleField'))

const cardVariant = {
  initial: { opacity: 0, y: 12 },
  animate: (i) => ({ opacity: 1, y: 0, transition: { delay: i * 0.06, duration: 0.4, ease: [0.16, 1, 0.3, 1] } }),
}

export default function Admin() {
  const [token, setToken] = useState('')
  const [summary, setSummary] = useState(null)
  const [users, setUsers] = useState([])
  const [feedback, setFeedback] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function loadAdmin() {
    setError('')
    setLoading(true)
    try {
      const [summaryRes, usersRes, feedbackRes] = await Promise.all([
        adminAPI.summary(token),
        adminAPI.users(token),
        adminAPI.feedback(token),
      ])
      setSummary(summaryRes.data)
      setUsers(usersRes.data || [])
      setFeedback(feedbackRes.data || [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load admin data.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <Helmet><title>Admin Portal | Ayura AI</title></Helmet>
    <div className="dash-root" style={{ position: 'relative' }}>
      <Suspense fallback={null}>
        <LazyParticleField count={200} spread={20} style={{ opacity: 0.35 }} />
      </Suspense>

      <main className="dash-main" style={{ margin: '0 auto', maxWidth: '1100px', position: 'relative', zIndex: 2 }}>
        <motion.section
          className="dash-section"
          style={{ display: 'grid', gap: '14px', padding: '24px' }}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        >
          <h1 style={{ margin: 0, fontFamily: "'Syne', sans-serif", fontSize: '1.6rem' }}>🔐 Ayura AI Admin</h1>
          <div className="input-group">
            <label htmlFor="admin-token">Admin Token</label>
            <input id="admin-token" type="password" value={token} onChange={e => setToken(e.target.value)} placeholder="Enter admin token..." />
          </div>
          <motion.button
            className="btn btn-primary"
            disabled={!token || loading}
            onClick={loadAdmin}
            whileTap={{ scale: 0.97 }}
          >
            {loading ? (
              <span style={{ display: 'flex', alignItems: 'center', gap: '8px', justifyContent: 'center' }}>
                <span className="spinner" style={{ width: '18px', height: '18px', borderWidth: '2px' }} />
                Loading...
              </span>
            ) : '🚀 Load Dashboard'}
          </motion.button>
          <AnimatePresence>
            {error && (
              <motion.div className="dash-notice error" initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                {error}
              </motion.div>
            )}
          </AnimatePresence>
        </motion.section>

        <AnimatePresence>
          {summary && (
            <motion.section
              className="dash-meta-grid"
              style={{ marginTop: '18px' }}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1, duration: 0.5 }}
            >
              {Object.entries(summary.counts || {}).map(([key, value], i) => (
                <motion.article
                  className="dash-meta-card ready"
                  key={key}
                  custom={i}
                  variants={cardVariant}
                  initial="initial"
                  animate="animate"
                >
                  <div className="dash-meta-title">{key.replace(/_/g, ' ')}</div>
                  <div className="dash-meta-state ready">{value}</div>
                </motion.article>
              ))}
            </motion.section>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {users.length > 0 && (
            <motion.section
              className="dash-section"
              style={{ marginTop: '18px', padding: '24px' }}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2, duration: 0.5 }}
            >
              <h2 style={{ marginTop: 0, fontFamily: "'Syne', sans-serif" }}>👥 Users ({users.length})</h2>
              <div style={{ display: 'grid', gap: '4px' }}>
                {users.map((user, i) => (
                  <motion.div
                    key={user.id}
                    style={{
                      display: 'flex', justifyContent: 'space-between', gap: '10px',
                      borderBottom: '1px solid rgba(149,197,255,.12)', padding: '10px 0',
                      alignItems: 'center',
                    }}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.25 + i * 0.03, duration: 0.3 }}
                  >
                    <span style={{ fontWeight: 600 }}>{user.email}</span>
                    <span style={{
                      fontSize: '.78rem', padding: '3px 8px', borderRadius: '999px',
                      background: user.dominant_dosha ? 'rgba(142,248,220,.1)' : 'rgba(149,197,255,.1)',
                      border: `1px solid ${user.dominant_dosha ? 'rgba(142,248,220,.25)' : 'rgba(149,197,255,.15)'}`,
                      color: user.dominant_dosha ? '#8ef8dc' : '#6b85a8',
                      textTransform: 'capitalize', fontWeight: 600,
                    }}>
                      {user.dominant_dosha || 'not set'}
                    </span>
                  </motion.div>
                ))}
              </div>
            </motion.section>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {feedback.length > 0 && (
            <motion.section
              className="dash-section"
              style={{ marginTop: '18px', padding: '24px' }}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3, duration: 0.5 }}
            >
              <h2 style={{ marginTop: 0, fontFamily: "'Syne', sans-serif" }}>📝 Feedback Reports ({feedback.length})</h2>
              <div style={{ display: 'grid', gap: '12px' }}>
                {feedback.map((f, i) => (
                  <motion.div
                    key={f.id}
                    style={{
                      background: 'var(--surface-900)', border: '1px solid var(--border)', 
                      borderRadius: '8px', padding: '16px', display: 'flex', flexDirection: 'column', gap: '8px'
                    }}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.35 + i * 0.03, duration: 0.3 }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <span style={{ 
                        fontSize: '.75rem', padding: '4px 10px', borderRadius: '4px',
                        background: f.type === 'Bug' ? 'rgba(239,68,68,0.1)' : 'rgba(59,130,246,0.1)',
                        color: f.type === 'Bug' ? '#ef4444' : '#60a5fa',
                        fontWeight: 600, letterSpacing: '0.5px', textTransform: 'uppercase'
                      }}>
                        {f.type}
                      </span>
                      <span style={{ fontSize: '.8rem', color: 'var(--text-400)' }}>
                        {new Date(f.created_at).toLocaleString()}
                      </span>
                    </div>
                    <p style={{ margin: '4px 0', color: 'var(--text-50)', lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>
                      {f.description}
                    </p>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '.85rem', color: 'var(--text-300)', marginTop: '4px' }}>
                      <span><strong>User:</strong> {f.user?.email || 'Unknown'}</span>
                      <span style={{ opacity: 0.7 }}>{f.url}</span>
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.section>
          )}
        </AnimatePresence>
      </main>
    </div>
    </>
  )
}
