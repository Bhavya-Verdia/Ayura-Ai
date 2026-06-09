import React, { useState, useContext } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { toast } from 'sonner'
import { AuthContext } from '../providers/AuthContext'
import { useTheme } from '../providers/ThemeProvider'
import { plansAPI, preferencesAPI } from '../api/client'
import API from '../api/client'
import PlanViewer from '../components/PlanViewer'
import DoshaArcRings from '../components/DoshaArcRings'
import PreferencesModal from '../components/PreferencesModal'
import confetti from 'canvas-confetti'
import './Dashboard.css'

const PLAN_TYPES = [
  { id: 'routine',     title: 'Daily Routine & Diet', icon: '🌅',   desc: 'Chronological Dinacharya timeline with meals.', color: 'var(--ayura-amber)',  bg: 'rgba(251,146,60,0.08)' },
  { id: 'yoga',        title: 'Yoga & Pranayama',   icon: '🧘‍♀️', desc: 'Dosha-balanced morning/evening routines.',    color: 'var(--ayura-teal)',   bg: 'rgba(45,212,191,0.08)' },
  { id: 'gym',         title: 'Fitness & Gym',       icon: '🏋️',   desc: 'Workout splits with progressive intensity.',  color: 'var(--vata-color)',   bg: 'rgba(129,140,248,0.08)' },
  { id: 'panchakarma', title: 'Panchakarma Detox',   icon: '🌿',   desc: 'Seasonal cleanses tailored to your prakriti.', color: 'var(--ayura-sage)',   bg: 'rgba(74,222,128,0.08)' },
  { id: 'remedies',    title: 'Home Remedies',       icon: '🍵',   desc: 'Kitchen medicine for common ailments.',        color: 'var(--ayura-rose)',   bg: 'rgba(251,113,133,0.08)' },
  { id: 'medicines',   title: 'Ayurvedic Medicines', icon: '💊',   desc: 'Classical formulations for deep healing.',     color: 'var(--ayura-violet)', bg: 'rgba(167,139,250,0.08)' },
]

const DOSHA_COLOR = { vata: '#818CF8', pitta: '#fb923c', kapha: '#34d399' }

// Stagger animation variants for plan cards grid
const gridContainer = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.07, delayChildren: 0.1 }
  }
}
const gridItem = {
  hidden: { opacity: 0, y: 24, scale: 0.97 },
  show:   { opacity: 1, y: 0,  scale: 1, transition: { duration: 0.45, ease: [0.16, 1, 0.3, 1] } }
}

function fireConfetti() {
  confetti({ particleCount: 80, spread: 70, origin: { y: 0.5 }, colors: ['#2dd4bf', '#a78bfa', '#fb923c', '#4ade80'] })
}

function getTimeOfDay() {
  const h = new Date().getHours()
  if (h < 12) return 'morning'
  if (h < 17) return 'afternoon'
  return 'evening'
}

// ── Dosha Balance Gauge — replaced by DoshaArcRings component ─
function DoshaGauge({ dosha }) {
  if (!dosha) return null
  const doshaScores = { vata: 65, pitta: 45, kapha: 30 }
  return (
    <DoshaArcRings
      dominantDosha={dosha.toLowerCase()}
      scores={doshaScores}
      size={180}
    />
  )
}

// ── Health Score Card ─────────────────────────────────────────
function HealthScoreCard({ completedCount, total }) {
  const score = Math.round((completedCount / total) * 100)
  const circumference = 2 * Math.PI * 38
  const offset = circumference - (circumference * score / 100)

  return (
    <div className="dash-health-score-card">
      <div className="dash-health-score-ring-wrap">
        <svg width="96" height="96" viewBox="0 0 96 96">
          <circle cx="48" cy="48" r="38" fill="none" stroke="var(--border-subtle)" strokeWidth="6" />
          <motion.circle
            cx="48" cy="48" r="38" fill="none"
            stroke="url(#hgGrad)" strokeWidth="6"
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 1.4, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
            transform="rotate(-90 48 48)"
          />
          <defs>
            <linearGradient id="hgGrad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="var(--ayura-teal)" />
              <stop offset="100%" stopColor="var(--ayura-violet)" />
            </linearGradient>
          </defs>
        </svg>
        <div className="dash-health-score-label">
          <span className="dash-health-score-val">{score}%</span>
          <span className="dash-health-score-sub">complete</span>
        </div>
      </div>
      <div className="dash-health-score-info">
        <div className="dash-health-score-title">Wellness Score</div>
        <div className="dash-health-score-desc">
          {completedCount} of {total} plans generated. Keep building your protocol.
        </div>
      </div>
    </div>
  )
}

// ── Main Dashboard ────────────────────────────────────────────
const Dashboard = () => {
  const { user } = useContext(AuthContext)
  const { theme, setTheme } = useTheme()
  const [viewingPlan, setViewingPlan]     = useState(null)
  const [viewingType, setViewingType]     = useState(null)
  const [generating,  setGenerating]      = useState({})
  const [prefModalConfig, setPrefModalConfig] = useState({ isOpen: false, typeId: null })

  const queryClient = useQueryClient()

  const { data: plans = {} } = useQuery({
    queryKey: ['plans-history'],
    queryFn: async () => {
      const res = await plansAPI.getHistory(0, 50)
      const latest = {}
      for (const entry of res.data) {
        const t = entry.plan_type
        if (!latest[t] && t !== 'holistic') latest[t] = entry.plan_data
      }
      return latest
    }
  })

  const generateMutation = useMutation({
    mutationFn: async ({ typeId, forceRegenerate = false }) => {
      // 0. Check if preferences are set for this feature
      const prefRes = await preferencesAPI.getFeature(typeId)
      if (!prefRes.data.is_set) {
        const err = new Error("PREF_REQUIRED")
        err.typeId = typeId
        throw err
      }

      // 1. Synchronous Generation
      const res = await API.post(`/plans/${typeId}`, { force_regenerate: forceRegenerate })
      
      return { typeId, data: res.data }
    },
    onMutate: ({ typeId }) => {
      setGenerating(prev => ({ ...prev, [typeId]: true }))
      toast.loading(`Generating your ${typeId} plan…`, { id: `gen-${typeId}` })
    },
    onSuccess: (result, { typeId }) => {
      const isFirstPlan = Object.keys(plans).length === 0
      queryClient.setQueryData(['plans-history'], old => ({
        ...old,
        [result.typeId]: result.data
      }))
      toast.success(`${result.typeId.charAt(0).toUpperCase() + result.typeId.slice(1)} plan ready! ✦`, { id: `gen-${result.typeId}` })
      // 🎉 Confetti on first plan generation
      if (isFirstPlan) fireConfetti()
    },
    onError: (err, { typeId }) => {
      if (err.message === "PREF_REQUIRED") {
        toast.dismiss(`gen-${typeId}`)
        setPrefModalConfig({ isOpen: true, typeId: err.typeId })
        return
      }
      if (err.response?.status === 429) {
        toast.error('Rate Limit Exceeded. Please wait a minute before requesting another sensitive medical plan.', { id: `gen-${typeId}` })
        return
      }
      toast.error(`Failed to generate ${typeId} plan. ${err.response?.data?.detail || 'Please try again.'}`, { id: `gen-${typeId}` })
    },
    onSettled: (_data, _err, { typeId }) => {
      setGenerating(prev => ({ ...prev, [typeId]: false }))
    }
  })

  const generatePlan = (typeId, forceRegenerate = false) => generateMutation.mutate({ typeId, forceRegenerate })

  const doshaBadgeColor = DOSHA_COLOR[user?.dominant_dosha?.toLowerCase()] || '#2dd4bf'
  const initials        = user?.name ? user.name.split(' ').map(w => w[0]).join('').slice(0,2).toUpperCase() : 'AY'
  const completedCount  = Object.keys(plans).length

  // ── Plan viewer ────────────────────────────────────────────
  if (viewingPlan) {
    return (
      <div className="dash-viewer-container">
        <div className="dash-viewer-back-bar">
          <button className="dash-back-btn" onClick={() => { setViewingPlan(null); setViewingType(null) }}>
            ← Back to Dashboard
          </button>
          <h2 className="dash-viewer-title">
            {PLAN_TYPES.find(t => t.id === viewingType)?.icon} {PLAN_TYPES.find(t => t.id === viewingType)?.title}
          </h2>
        </div>
        <PlanViewer plan={viewingPlan} planType={viewingType} />
      </div>
    )
  }

  return (
    <div className="dash-content-container">
      <PreferencesModal 
        isOpen={prefModalConfig.isOpen} 
        typeId={prefModalConfig.typeId}
        onClose={() => setPrefModalConfig({ isOpen: false, typeId: null })}
        onSubmitSuccess={() => {
          const tId = prefModalConfig.typeId
          setPrefModalConfig({ isOpen: false, typeId: null })
          generatePlan(tId)
        }}
      />

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '-16px', position: 'relative', zIndex: 10 }}>
        <motion.button 
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          className="btn btn-secondary btn-sm"
          style={{ display: 'flex', alignItems: 'center', gap: '6px', borderRadius: '20px', padding: '6px 14px', fontSize: '0.85rem' }}
          whileTap={{ scale: 0.95 }}
        >
          {theme === 'dark' ? '☀️ Light Mode' : '🌙 Dark Mode'}
        </motion.button>
      </div>

      {/* ── Hero Card ── */}
      <motion.div
        className="dash-hero-card"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="dash-hero-left">
          <div
            className="dash-hero-avatar"
            style={{
              background: `linear-gradient(135deg, ${doshaBadgeColor}44, ${doshaBadgeColor}22)`,
              border: `1px solid ${doshaBadgeColor}44`,
              color: doshaBadgeColor,
            }}
          >
            {initials}
          </div>
          <div>
            <h1 className="dash-hero-greeting">
              Good {getTimeOfDay()}, <span className="dash-hero-name">{user?.name?.split(' ')[0] || 'there'}</span>
            </h1>
            <p className="dash-hero-sub">
              {user?.dominant_dosha ? (
                <>Your dominant dosha is <span className="dash-dosha-tag" style={{ color: doshaBadgeColor }}>{user.dominant_dosha}</span></>
              ) : (
                'Your personalised wellness platform'
              )}
            </p>
          </div>
        </div>

        <div className="dash-hero-right" style={{ display: 'flex', gap: 20, alignItems: 'center', flexWrap: 'wrap' }}>
          {user?.dominant_dosha && <DoshaGauge dosha={user.dominant_dosha} />}
          <HealthScoreCard completedCount={completedCount} total={PLAN_TYPES.length} />
        </div>
      </motion.div>



      {/* ── Plans section ── */}
      <div className="dash-plans-header">
        <h2 className="dash-plans-title">Your Wellness Plans</h2>
        <p className="dash-plans-sub">Generate or view your AI-crafted Ayurvedic plans</p>
      </div>

      {/* Staggered card grid */}
      <motion.div
        className="dash-plans-grid"
        variants={gridContainer}
        initial="hidden"
        animate="show"
      >
        {PLAN_TYPES.map((type) => (
          <motion.div
            key={type.id}
            className={`dash-plan-card${plans[type.id] ? ' has-plan' : ''}`}
            variants={gridItem}
            whileHover={{ y: -5, transition: { duration: 0.2 } }}
          >
            <div className="dash-plan-card-header">
              <div className="dash-plan-icon-wrap">{type.icon}</div>
              {plans[type.id] && <span className="dash-plan-ready-badge">✦ Ready</span>}
            </div>

            <h3 className="dash-plan-name">{type.title}</h3>
            <p className="dash-plan-desc">{type.desc}</p>

            <div className="dash-plan-actions">
              {plans[type.id] ? (
                <div className="dash-plan-action-row">
                  <button className="dash-plan-view-btn" onClick={() => { setViewingPlan(plans[type.id]); setViewingType(type.id) }}>
                    View Plan →
                  </button>
                  <button
                    className="dash-plan-regen-btn"
                    onClick={() => generatePlan(type.id, true)}
                    disabled={generating[type.id]}
                    title="Regenerate"
                  >
                    {generating[type.id] ? '…' : '↻'}
                  </button>
                </div>
              ) : (
                <button
                  className="dash-plan-generate-btn"
                  onClick={() => generatePlan(type.id)}
                  disabled={generating[type.id]}
                >
                  {generating[type.id] ? (
                    <><span className="spinner" style={{ width: '16px', height: '16px', borderWidth: '2px' }} /> Generating…</>
                  ) : '✦ Generate Plan'}
                </button>
              )}
            </div>
          </motion.div>
        ))}
      </motion.div>

      {/* ── Quick nav cards ── */}
      <div className="dash-quick-nav">
        {[
          { label: 'AI Chat',   icon: '💬', path: '/chat',     desc: 'Ask your wellness advisor anything' },
          { label: 'Timeline',  icon: '📈', path: '/timeline', desc: 'Track your health progress' },
          { label: 'Check-In',  icon: '✅', path: '/checkin',  desc: "Log today's energy & mood" },
        ].map((item, i) => (
          <motion.div key={item.path} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: 0.3 + i * 0.1 }}>
            <Link to={item.path} className="dash-quick-card">
              <span className="dash-quick-icon">{item.icon}</span>
              <div className="dash-quick-info">
                <div className="dash-quick-label">{item.label}</div>
                <div className="dash-quick-desc">{item.desc}</div>
              </div>
              <span className="dash-quick-arrow">→</span>
            </Link>
          </motion.div>
        ))}
      </div>
    </div>
  )
}

export default Dashboard
