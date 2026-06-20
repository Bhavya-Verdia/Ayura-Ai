import React, { useState, useContext, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { toast } from 'sonner'
import { AuthContext } from '../providers/AuthContext'
import { useTheme } from '../providers/ThemeProvider'
import API, { plansAPI, preferencesAPI, progressAPI, profileAPI } from '../api/client'
import PlanViewer from '../components/PlanViewer'
import VikritiCheckIn from '../components/VikritiCheckIn'
import DoshaValidationCard from '../components/DoshaValidationCard'
import DoshaArcRings from '../components/DoshaArcRings'
import PreferencesModal from '../components/PreferencesModal'
import SectionBoundary from '../components/SectionBoundary'
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

function formatRelativeTime(dateStr) {
  if (!dateStr) return null
  const diffMs = Date.now() - new Date(dateStr).getTime()
  const mins  = Math.floor(diffMs / 60000)
  const hours = Math.floor(mins  / 60)
  const days  = Math.floor(hours / 24)
  if (mins  <  1) return 'just now'
  if (mins  < 60) return `${mins}m ago`
  if (hours < 24) return `${hours}h ago`
  if (days  ===1) return 'yesterday'
  return `${days}d ago`
}

function extractPreview(planData, maxLen = 110) {
  if (!planData) return null
  const raw = typeof planData === 'string' ? planData : JSON.stringify(planData)
  const stripped = raw
    .replace(/#{1,6}\s+/g, '').replace(/\*{1,2}/g, '').replace(/`/g, '')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1').replace(/\n+/g, ' ').trim()
  return stripped.length > maxLen ? stripped.slice(0, maxLen).trimEnd() + '…' : stripped
}

function StreakCard() {
  const { data: progress } = useQuery({
    queryKey: ['progress-summary'],
    queryFn: () => progressAPI.getSummary().then(r => r.data),
    staleTime: 5 * 60 * 1000,
    retry: 1,
  })

  const streak = progress?.current_streak ?? progress?.streak ?? 0
  const checkedInToday = progress?.checked_in_today ?? false

  const days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date()
    d.setDate(d.getDate() - (6 - i))
    const dateStr = d.toISOString().split('T')[0]
    const isActive = !!(progress?.recent_dates?.includes(dateStr) || progress?.active_dates?.includes(dateStr))
    return {
      label: ['Su','Mo','Tu','We','Th','Fr','Sa'][d.getDay()],
      isActive,
      isToday: i === 6,
    }
  })

  const message =
    streak >= 14 ? 'Incredible streak — keep going!' :
    streak >= 7  ? 'One full week! Phenomenal.' :
    streak >= 3  ? 'Great consistency!' :
    streak >= 1  ? 'Good start — keep it up!' :
    'Start your streak — check in today!'

  return (
    <motion.div
      className="dash-streak-card"
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.1 }}
    >
      <div className="dash-streak-left">
        <div className="dash-streak-flame">🔥</div>
        <div>
          <div className="dash-streak-count">
            <span className="dash-streak-num">{streak}</span>
            <span className="dash-streak-unit">day{streak !== 1 ? 's' : ''}</span>
          </div>
          <p className="dash-streak-sub">{message}</p>
        </div>
      </div>
      <div className="dash-streak-right">
        <div className="dash-streak-dots">
          {days.map((day, i) => (
            <div key={i} className="dash-streak-day">
              <div className={`dash-streak-dot${day.isActive ? ' active' : ''}${day.isToday ? ' today' : ''}`} />
              <span className="dash-streak-day-lbl">{day.label}</span>
            </div>
          ))}
        </div>
        <Link to="/checkin" className="dash-streak-cta">
          {checkedInToday ? '✓ Done for today' : '↗ Check in now'}
        </Link>
      </div>
    </motion.div>
  )
}

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

function computeVikritiTrend(history, dominant) {
  if (!history || history.length < 2 || !dominant) return null
  const recent = history.slice(-3)
  const scores = recent.map(h => h.scores?.[dominant] ?? 50)
  const avg = (a) => a.reduce((s, v) => s + v, 0) / a.length
  const older = avg(scores.slice(0, Math.ceil(scores.length / 2)))
  const newer = avg(scores.slice(Math.floor(scores.length / 2)))
  const delta = newer - older
  if (delta < -3) return 'improving'
  if (delta > 3)  return 'worsening'
  return 'stable'
}

function VikritiTrendBadge({ trend, confidence, checkinCount }) {
  if (!trend && !confidence) return null
  const trendConfig = {
    improving: { label: '↓ Imbalance easing', color: '#34d399' },
    worsening: { label: '↑ Imbalance rising', color: '#fb923c' },
    stable:    { label: '~ Holding steady',   color: '#94a3b8' },
  }
  const tc = trendConfig[trend]
  const confidenceLabel =
    confidence >= 80 ? 'High confidence' :
    confidence >= 55 ? 'Medium confidence' :
    confidence >= 40 ? 'Early reading' : 'Getting started'
  const confidenceColor =
    confidence >= 80 ? '#34d399' :
    confidence >= 55 ? '#fbbf24' : '#94a3b8'

  return (
    <div className="dash-vikriti-badges">
      {tc && (
        <span className="dash-vikriti-badge" style={{ color: tc.color, borderColor: tc.color + '44' }}>
          {tc.label}
        </span>
      )}
      {confidence != null && (
        <span className="dash-vikriti-badge" style={{ color: confidenceColor, borderColor: confidenceColor + '44' }}
          title={checkinCount ? `Based on ${checkinCount} check-in${checkinCount !== 1 ? 's' : ''}` : undefined}
        >
          {confidenceLabel} {confidence != null ? `· ${confidence}%` : ''}
        </span>
      )}
    </div>
  )
}

// ── Dosha Balance Gauge — replaced by DoshaArcRings component ─
function DoshaGauge({ dosha, doshaScores }) {
  if (!dosha) return null
  const scores = doshaScores && (doshaScores.vata || doshaScores.pitta || doshaScores.kapha)
    ? doshaScores
    : null
  if (!scores) return null
  return (
    <DoshaArcRings
      dominantDosha={dosha.toLowerCase()}
      scores={scores}
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

// ── Plan Feedback Card ────────────────────────────────────────
function PlanFeedbackCard({ planType, onDone }) {
  const queryClient = useQueryClient()
  const [status, setStatus] = useState('idle')

  async function submit(improved) {
    setStatus('submitting')
    try {
      const res = await profileAPI.planFeedback({ plan_type: planType, improved })
      queryClient.setQueryData(['auth-user'], (old) => old ? { ...old, data: res.data } : old)
      onDone()
    } catch {
      setStatus('idle')
    }
  }

  return (
    <motion.div
      className="dash-feedback-card"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <p className="dash-feedback-q">
        It's been 2 weeks — is your <strong>{planType}</strong> plan working for you?
      </p>
      <div className="dash-feedback-btns">
        <button
          type="button"
          className="btn btn-primary btn-sm"
          disabled={status === 'submitting'}
          onClick={() => submit(true)}
        >
          Yes, improving
        </button>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          disabled={status === 'submitting'}
          onClick={() => submit(false)}
        >
          Not yet
        </button>
      </div>
    </motion.div>
  )
}

// ── Re-assessment Trigger Card ─────────────────────────────────
function ReassessmentCard({ onDismiss }) {
  return (
    <motion.div
      className="dash-reassess-card"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="dash-reassess-icon">🔄</div>
      <div className="dash-reassess-body">
        <strong>Your plans haven&apos;t been hitting the mark</strong>
        <p>Your dosha profile may need updating — this happens when life circumstances, stress levels, or seasons change significantly.</p>
      </div>
      <div className="dash-reassess-actions">
        <Link to="/dosha-quiz" className="btn btn-primary btn-sm">Reassess My Dosha →</Link>
        <button type="button" className="btn btn-secondary btn-sm" onClick={onDismiss}>Not now</button>
      </div>
    </motion.div>
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
  const [showCheckin, setShowCheckin]     = useState(true)
  const [feedbackDone, setFeedbackDone]   = useState(false)
  const [doshaValidationDismissed, setDoshaValidationDismissed] = useState(false)
  const [reassessmentDismissed, setReassessmentDismissed] = useState(false)

  const queryClient = useQueryClient()

  const { data: plans = {} } = useQuery({
    queryKey: ['plans-history'],
    queryFn: async () => {
      const res = await plansAPI.getHistory(50)
      const entries = res.data?.items ?? res.data ?? []
      const latest = {}
      for (const entry of entries) {
        const t = entry.plan_type
        if (!latest[t] && t !== 'holistic') latest[t] = { data: entry.plan_data, created_at: entry.created_at }
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
    onSuccess: (result) => {
      const isFirstPlan = Object.keys(plans).length === 0
      queryClient.setQueryData(['plans-history'], old => ({
        ...old,
        [result.typeId]: { data: result.data, created_at: new Date().toISOString() }
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

  const nowMs = new Date().getTime()

  const needsCheckin = useMemo(() => {
    if (!user?.vikriti_scores) return false
    if (!user?.last_vikriti_checkin) return true
    const daysSince = (nowMs - new Date(user.last_vikriti_checkin).getTime()) / (1000 * 60 * 60 * 24)
    return daysSince >= 7
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.vikriti_scores, user?.last_vikriti_checkin])

  const feedbackTarget = useMemo(() => {
    if (feedbackDone) return null
    for (const [type, plan] of Object.entries(plans)) {
      if (!plan?.created_at) continue
      const days = (nowMs - new Date(plan.created_at).getTime()) / (1000 * 60 * 60 * 24)
      if (days >= 14 && !user?.last_plan_feedback) return type
    }
    return null
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [feedbackDone, plans, user?.last_plan_feedback])

  const showDoshaValidation = useMemo(() => {
    if (doshaValidationDismissed) return false
    if (!user?.vikriti_dominant) return false
    if (user?.last_dosha_validation) return false
    const assessedAt = user?.updated_at
    if (!assessedAt) return false
    const daysSince = (nowMs - new Date(assessedAt).getTime()) / (1000 * 60 * 60 * 24)
    return daysSince >= 14
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doshaValidationDismissed, user?.vikriti_dominant, user?.last_dosha_validation, user?.updated_at])

  const showReassessment = useMemo(() =>
    !reassessmentDismissed && (
      (user?.plan_not_working_streak || 0) >= 3 ||
      user?.needs_reassessment === true
    ),
  [reassessmentDismissed, user?.plan_not_working_streak, user?.needs_reassessment]
  )

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
        <SectionBoundary
          fallbackMessage="This plan couldn't render. The data may be in an unexpected format."
          onBack={() => { setViewingPlan(null); setViewingType(null) }}
        >
          <PlanViewer plan={viewingPlan} planType={viewingType} />
        </SectionBoundary>
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
            <VikritiTrendBadge
              trend={computeVikritiTrend(user?.vikriti_history, user?.vikriti_dominant)}
              confidence={user?.dosha_confidence}
              checkinCount={user?.checkin_count}
            />
            {user?.ojas_level && (
              <div className={`dash-ojas-pill ojas-${user.ojas_level}`}>
                <span className="dash-ojas-icon">✦</span>
                <span>Ojas: {user.ojas_level === 'high' ? 'High — Strong Immunity' : user.ojas_level === 'medium' ? 'Medium — Fair Vitality' : 'Low — Depleted'}{user.ojas_score != null ? ` (${user.ojas_score}/100)` : ''}</span>
              </div>
            )}
          </div>
        </div>

        <div className="dash-hero-right" style={{ display: 'flex', gap: 20, alignItems: 'center', flexWrap: 'wrap' }}>
          {user?.dominant_dosha && <DoshaGauge dosha={user.dominant_dosha} doshaScores={user.dosha_scores} />}
          <HealthScoreCard completedCount={completedCount} total={PLAN_TYPES.length} />
        </div>
      </motion.div>



      {/* ── Streak Card ── */}
      <StreakCard />

      {/* ── Weekly Vikriti Check-in ── */}
      {needsCheckin && showCheckin && (
        <VikritiCheckIn onDismiss={() => setShowCheckin(false)} />
      )}

      {/* ── 14-day plan feedback ── */}
      {feedbackTarget && (
        <PlanFeedbackCard planType={feedbackTarget} onDone={() => setFeedbackDone(true)} />
      )}

      {/* ── 14-day dosha validation ── */}
      {showDoshaValidation && (
        <DoshaValidationCard
          vikritiDominant={user.vikriti_dominant}
          onDone={() => setDoshaValidationDismissed(true)}
        />
      )}

      {/* ── Re-assessment suggestion ── */}
      {showReassessment && (
        <ReassessmentCard onDismiss={() => setReassessmentDismissed(true)} />
      )}

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
            {plans[type.id] ? (
              <p className="dash-plan-preview">{extractPreview(plans[type.id].data) || type.desc}</p>
            ) : (
              <p className="dash-plan-desc">{type.desc}</p>
            )}
            {plans[type.id]?.created_at && (
              <span className="dash-plan-timestamp">↻ Updated {formatRelativeTime(plans[type.id].created_at)}</span>
            )}

            <div className="dash-plan-actions">
              {plans[type.id] ? (
                <div className="dash-plan-action-row">
                  <button className="dash-plan-view-btn" onClick={() => { setViewingPlan(plans[type.id].data); setViewingType(type.id) }}>
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
