import React, { useState } from 'react'
import { useQuery, useInfiniteQuery, useQueryClient } from '@tanstack/react-query'

import { motion, AnimatePresence } from 'framer-motion'
import { Helmet } from 'react-helmet-async'
import API from '../api/client'
import { progressAPI } from '../api/client'
import { SkeletonLine } from '../components/Skeleton'
import './HealthTimeline.css'


/* ─── Event config ───────────────────────────────────── */
const EVENT_CONFIG = {
  symptom_logged: {
    icon: '🤒',
    label: 'Symptom Logged',
    colorVar: '--accent',
    glowColor: 'rgba(245,158,11,0.45)',
    bgColor: 'rgba(245,158,11,0.08)',
    borderColor: 'rgba(245,158,11,0.2)',
    badgeClass: 'badge-accent',
    filterKey: 'symptoms',
  },
  progress_logged: {
    icon: '📊',
    label: 'Progress Check-In',
    colorVar: '--primary-light',
    glowColor: 'rgba(45,212,191,0.45)',
    bgColor: 'rgba(45,212,191,0.07)',
    borderColor: 'rgba(45,212,191,0.2)',
    badgeClass: 'badge-primary',
    filterKey: 'progress',
  },
  adaptation_failed: {
    icon: '⚠️',
    label: 'Adaptation Error',
    colorVar: '--rose',
    glowColor: 'rgba(244,63,94,0.45)',
    bgColor: 'rgba(244,63,94,0.07)',
    borderColor: 'rgba(244,63,94,0.2)',
    badgeClass: 'badge-rose',
    filterKey: 'adaptations',
  },
  plan_generated: {
    icon: '✨',
    label: 'Plan Generated',
    colorVar: '--primary',
    glowColor: 'rgba(13,148,136,0.45)',
    bgColor: 'rgba(13,148,136,0.07)',
    borderColor: 'rgba(13,148,136,0.2)',
    badgeClass: 'badge-primary',
    filterKey: 'plans',
  },
  adaptation_triggered: {
    icon: '🔄',
    label: 'Plan Adapted',
    colorVar: '--sage',
    glowColor: 'rgba(16,185,129,0.45)',
    bgColor: 'rgba(16,185,129,0.07)',
    borderColor: 'rgba(16,185,129,0.2)',
    badgeClass: 'badge-primary',
    filterKey: 'adaptations',
  },
  reminder_set: {
    icon: '⏰',
    label: 'Reminder Set',
    colorVar: '--ayura-violet',
    glowColor: 'rgba(139,92,246,0.45)',
    bgColor: 'rgba(139,92,246,0.07)',
    borderColor: 'rgba(139,92,246,0.2)',
    badgeClass: '',
    filterKey: 'all',
  },
  default: {
    icon: '📝',
    label: 'Health Event',
    colorVar: '--text-muted',
    glowColor: 'rgba(94,138,133,0.35)',
    bgColor: 'rgba(94,138,133,0.06)',
    borderColor: 'rgba(94,138,133,0.15)',
    badgeClass: '',
    filterKey: 'all',
  },
}

const FILTERS = [
  { id: 'all',         label: 'All Events',    icon: '🗓️' },
  { id: 'symptoms',    label: 'Symptoms',      icon: '🤒' },
  { id: 'progress',    label: 'Progress',      icon: '📊' },
  { id: 'plans',       label: 'Plans',         icon: '✨' },
  { id: 'adaptations', label: 'Adaptations',   icon: '🔄' },
]

const PAGE_SIZE = 10

/* ─── Helpers ────────────────────────────────────────── */
function getEventConfig(type) {
  return EVENT_CONFIG[type] || EVENT_CONFIG.default
}

function formatDateTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: true,
  })
}

function formatTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('en-IN', {
    hour: '2-digit', minute: '2-digit', hour12: true,
  })
}

function getDateGroup(iso) {
  if (!iso) return 'Earlier'
  const d = new Date(iso)
  const now = new Date()
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const startOfYesterday = new Date(startOfToday - 86400000)
  const startOfWeek = new Date(startOfToday - 6 * 86400000)
  const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1)

  if (d >= startOfToday) return 'Today'
  if (d >= startOfYesterday) return 'Yesterday'
  if (d >= startOfWeek) return 'This Week'
  if (d >= startOfMonth) return 'This Month'
  return d.toLocaleString('en-IN', { month: 'long', year: 'numeric' })
}

function groupEvents(events) {
  const groups = {}
  events.forEach(ev => {
    const g = getDateGroup(ev.created_at || ev.timestamp)
    if (!groups[g]) groups[g] = []
    groups[g].push(ev)
  })
  return groups
}

function renderDetails(event) {
  const { event_type, details = {}, metadata = {} } = event
  const data = details || metadata || {}

  switch (event_type) {
    case 'symptom_logged':
      return (
        <div className="ht-event-details">
          {data.symptom && <span className="ht-detail-chip ht-chip-amber">🤒 {data.symptom}</span>}
          {data.severity && <span className="ht-detail-chip ht-chip-muted">Severity: {data.severity}/10</span>}
          {data.body_part && <span className="ht-detail-chip ht-chip-muted">📍 {data.body_part}</span>}
          {data.note && <p className="ht-detail-note">"{data.note}"</p>}
        </div>
      )
    case 'progress_logged':
      return (
        <div className="ht-event-details">
          {data.weight_kg && <span className="ht-detail-chip ht-chip-teal">⚖️ {data.weight_kg} kg</span>}
          {data.mood && <span className="ht-detail-chip ht-chip-teal">😊 Mood: {data.mood}</span>}
          {data.adherence_percent != null && (
            <div className="ht-adherence-bar">
              <span className="ht-adherence-label">Plan adherence</span>
              <div className="ht-bar-track">
                <div className="ht-bar-fill" style={{ width: `${data.adherence_percent}%` }} />
              </div>
              <span className="ht-adherence-pct">{data.adherence_percent}%</span>
            </div>
          )}
        </div>
      )
    case 'plan_generated':
      return (
        <div className="ht-event-details">
          {data.plan_type && <span className="ht-detail-chip ht-chip-primary">📋 {data.plan_type}</span>}
          {data.model_used && <span className="ht-detail-chip ht-chip-muted">{data.model_used}</span>}
        </div>
      )
    case 'adaptation_triggered':
      return (
        <div className="ht-event-details">
          {data.plan_type && <span className="ht-detail-chip ht-chip-sage">🔄 {data.plan_type}</span>}
          {data.model_used && <span className="ht-detail-chip ht-chip-muted">{data.model_used}</span>}
        </div>
      )
    case 'reminder_set':
      return (
        <div className="ht-event-details">
          {data.reminder && <span className="ht-detail-chip ht-chip-muted">⏰ {data.reminder}</span>}
        </div>
      )
    case 'adaptation_failed':
      return (
        <div className="ht-event-details">
          {data.error && <span className="ht-detail-chip ht-chip-rose">⚠️ {data.error}</span>}
          {data.reason && <p className="ht-detail-note">{data.reason}</p>}
        </div>
      )
    default:
      if (Object.keys(data).length === 0) return null
      return (
        <div className="ht-event-details">
          {Object.entries(data).slice(0, 4).map(([k, v]) => (
            typeof v === 'string' || typeof v === 'number'
              ? <span key={k} className="ht-detail-chip ht-chip-muted">{k}: {v}</span>
              : null
          ))}
        </div>
      )
  }
}

/* ─── Skeleton ───────────────────────────────────────── */
function TimelineSkeleton() {
  return (
    <div className="ht-skeleton-wrap" aria-busy="true" aria-label="Loading timeline">
      {Array.from({ length: 5 }).map((_, i) => (
        <div className="ht-skeleton-item" key={i}>
          <div className="ht-skeleton-dot skeleton" />
          <div className="ht-skeleton-card">
            <SkeletonLine width="40%" height="12px" style={{ marginBottom: '10px' }} />
            <SkeletonLine width="65%" height="18px" style={{ marginBottom: '8px' }} />
            <SkeletonLine width="80%" height="12px" />
          </div>
        </div>
      ))}
    </div>
  )
}

/* ─── Progress Summary Card ──────────────────────────── */
function ProgressSummary({ summary }) {
  if (!summary || !summary.current) return null

  const c = summary.current
  const TREND_LABELS = {
    losing_weight:  { label: '↓ Losing', icon: '📉', special: 'declining' },
    gaining_weight: { label: '↑ Gaining', icon: '📈', special: 'improving' },
    stable:         { label: '→ Stable', icon: '➡️', special: 'stable' },
  }
  const trendInfo = TREND_LABELS[summary.trend] || { label: '→ Stable', icon: '➡️', special: 'stable' }

  const stats = [
    { label: 'Weight', value: c.weight_kg ? `${c.weight_kg} kg` : '—', icon: '⚖️' },
    { label: 'BMI', value: c.bmi ? c.bmi.toFixed(1) : '—', icon: '📐' },
    { label: 'Mood', value: c.mood || '—', icon: '😊' },
    { label: 'Adherence', value: c.adherence_percent != null ? `${c.adherence_percent}%` : '—', icon: '✅' },
    {
      label: 'Trend',
      value: trendInfo.label,
      icon: trendInfo.icon,
      special: trendInfo.special,
    },
  ]

  return (
    <motion.div
      className="ht-progress-strip"
      initial={{ opacity: 0, y: -16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="ht-progress-strip-label">
        <span className="ht-strip-icon">📊</span>
        <span>Progress Snapshot</span>
        {c.last_logged && (
          <span className="ht-strip-date">Updated {formatDateTime(c.last_logged)}</span>
        )}
      </div>
      <div className="ht-progress-stats">
        {stats.map(s => (
          <div key={s.label} className={`ht-stat-item${s.special ? ` ht-trend-${s.special}` : ''}`}>
            <span className="ht-stat-icon">{s.icon}</span>
            <div>
              <div className="ht-stat-value">{s.value}</div>
              <div className="ht-stat-label">{s.label}</div>
            </div>
          </div>
        ))}
      </div>
    </motion.div>
  )
}

/* ─── Event Card ─────────────────────────────────────── */
function EventCard({ event, index }) {
  const cfg = getEventConfig(event.event_type)
  const ts = event.created_at || event.timestamp

  return (
    <motion.div
      className="ht-event-row"
      initial={{ opacity: 0, x: 40 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.38, delay: index * 0.06, ease: [0.16, 1, 0.3, 1] }}
    >
      {/* Dot */}
      <div
        className="ht-event-dot"
        style={{ boxShadow: `0 0 0 3px var(--bg-surface), 0 0 12px ${cfg.glowColor}` }}
        aria-hidden="true"
      >
        <span className="ht-dot-icon">{cfg.icon}</span>
      </div>

      {/* Card */}
      <div
        className="ht-event-card"
        style={{
          background: cfg.bgColor,
          borderColor: cfg.borderColor,
        }}
      >
        <div className="ht-event-card-header">
          <div className="ht-event-meta">
            <span className={`badge ${cfg.badgeClass}`}>{cfg.label}</span>
            <span className="ht-event-time">{formatTime(ts)}</span>
          </div>
          {event.id && <span className="ht-event-id">#{String(event.id).slice(-6)}</span>}
        </div>

        {event.title && <h4 className="ht-event-title">{event.title}</h4>}
        {event.description && <p className="ht-event-desc">{event.description}</p>}

        {renderDetails(event)}
      </div>
    </motion.div>
  )
}

/* ─── Date Group Header ──────────────────────────────── */
function DateGroupHeader({ label }) {
  return (
    <motion.div
      className="ht-date-header"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <span className="ht-date-badge">{label}</span>
      <div className="ht-date-line" />
    </motion.div>
  )
}

/* ─── Empty State ────────────────────────────────────── */
function EmptyState({ filtered }) {
  return (
    <motion.div
      className="ht-empty"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="ht-empty-orb" aria-hidden="true">🌱</div>
      <h3 className="ht-empty-title">
        {filtered ? 'No events in this category' : 'Your health story begins here'}
      </h3>
      <p className="ht-empty-desc">
        {filtered
          ? 'Try selecting a different filter to see more events.'
          : 'Start logging progress and chat with Ayura AI. Your health timeline will fill up as you engage with the platform.'
        }
      </p>
      {!filtered && (
        <div className="ht-empty-actions">
          <a href="/checkin" className="btn btn-primary btn-sm">✅ Log Check-In</a>
          <a href="/chat" className="btn btn-secondary btn-sm">💬 Chat with Ayura</a>
        </div>
      )}
    </motion.div>
  )
}

/* ─── Main Component ─────────────────────────────────── */
export default function HealthTimeline() {
  const [activeFilter, setActiveFilter] = useState('all')

  const queryClient = useQueryClient()

  // Fetch progress summary
  const { data: summary } = useQuery({
    queryKey: ['timeline-summary'],
    queryFn: async () => {
      const res = await progressAPI.getSummary()
      return res.data
    },
    retry: false
  })

  // Fetch timeline events
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading: loading,
    error: queryError
  } = useInfiniteQuery({
    queryKey: ['timeline-events'],
    queryFn: async ({ pageParam = 0 }) => {
      const res = await API.get('/timeline', {
        params: { offset: pageParam * PAGE_SIZE, limit: PAGE_SIZE },
      })
      const incoming = Array.isArray(res.data)
        ? res.data
        : (res.data?.events || res.data?.items || [])
      
      return {
        events: incoming,
        nextOffset: incoming.length === PAGE_SIZE ? pageParam + 1 : null
      }
    },
    getNextPageParam: (lastPage) => lastPage.nextOffset,
    initialPageParam: 0,
    retry: false
  })

  const events = data?.pages.flatMap(page => page.events) || []
  const hasMore = hasNextPage
  const loadingMore = isFetchingNextPage

  const error = queryError?.response?.status !== 404 && queryError?.code !== 'ERR_NETWORK' 
    ? 'Could not load your health timeline. Please try again.' 
    : null

  const handleLoadMore = () => fetchNextPage()

  /* Filter logic */
  const filteredEvents = activeFilter === 'all'
    ? events
    : events.filter(ev => {
        const cfg = getEventConfig(ev.event_type)
        return cfg.filterKey === activeFilter
      })

  const grouped = groupEvents(filteredEvents)
  const groupOrder = Object.keys(grouped)
  const isFiltered = activeFilter !== 'all'

  return (
    <>
      <Helmet>
        <title>Health Timeline | Ayura AI</title>
        <meta
          name="description"
          content="Your complete chronological health history — symptoms, progress, plan adaptations, and more."
        />
      </Helmet>

      <div className="ht-root">
        {/* ── Page Header ── */}
        <motion.div
          className="ht-page-header"
          initial={{ opacity: 0, y: -16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
        >
          <div className="ht-page-header-left">
            <h1 className="ht-page-title">
              <span className="gradient-text">Health Timeline</span>
            </h1>
            <p className="ht-page-sub">
              Your complete chronological health story — symptoms, progress, and AI adaptations.
            </p>
          </div>
          <button
            className="btn btn-secondary btn-sm ht-refresh-btn"
            onClick={() => queryClient.invalidateQueries({ queryKey: ['timeline-events'] })}
            title="Refresh"
            aria-label="Refresh timeline"
          >
            ↻ Refresh
          </button>
        </motion.div>

        {/* ── Progress Summary Strip ── */}
        <ProgressSummary summary={summary} />

        {/* ── Filter Pills ── */}
        <motion.div
          className="ht-filters"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          role="group"
          aria-label="Filter events"
        >
          {FILTERS.map(f => (
            <button
              key={f.id}
              className={`ht-filter-pill${activeFilter === f.id ? ' active' : ''}`}
              onClick={() => setActiveFilter(f.id)}
              aria-pressed={activeFilter === f.id}
            >
              <span>{f.icon}</span> {f.label}
            </button>
          ))}
        </motion.div>

        {/* ── Error Banner ── */}
        <AnimatePresence>
          {error && (
            <motion.div
              className="ht-error-bar"
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
            >
              <span>⚠️ {error}</span>
              <button onClick={() => {}} aria-label="Dismiss error">✕</button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Timeline Body ── */}
        <div className="ht-body">
          {loading ? (
            <TimelineSkeleton />
          ) : filteredEvents.length === 0 ? (
            <EmptyState filtered={isFiltered} />
          ) : (
            <div className="ht-timeline">
              {/* Vertical Line */}
              <div className="ht-vline" aria-hidden="true" />

              <AnimatePresence mode="popLayout">
                {groupOrder.map(group => (
                  <React.Fragment key={group}>
                    <DateGroupHeader label={group} />
                    {grouped[group].map((ev, idx) => (
                      <EventCard key={ev.id ?? `${group}-${idx}`} event={ev} index={idx} />
                    ))}
                  </React.Fragment>
                ))}
              </AnimatePresence>
            </div>
          )}

          {/* ── Load More ── */}
          {!loading && hasMore && filteredEvents.length > 0 && (
            <motion.div
              className="ht-load-more-wrap"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
            >
              <button
                className="btn btn-secondary ht-load-more-btn"
                onClick={handleLoadMore}
                disabled={loadingMore}
              >
                {loadingMore ? (
                  <><span className="spinner" style={{ width: '16px', height: '16px', borderWidth: '2px' }} /> Loading…</>
                ) : (
                  '↓ Load More'
                )}
              </button>
            </motion.div>
          )}

          {/* ── End of timeline indicator ── */}
          {!loading && !hasMore && filteredEvents.length > 0 && (
            <motion.div
              className="ht-timeline-end"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
            >
              <div className="ht-end-dot" />
              <span>You're all caught up ✦</span>
            </motion.div>
          )}
        </div>
      </div>
    </>
  )
}
