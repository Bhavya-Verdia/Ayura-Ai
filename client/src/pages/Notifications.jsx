import React, { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Helmet } from 'react-helmet-async'
import { notificationsAPI } from '../api/client'
import { Leaf, RefreshCw, AlarmClock, AlertTriangle, Bell, Sparkles, CheckCheck, Trash2 } from 'lucide-react'
import './Notifications.css'

// ── Type config ──────────────────────────────────────────────
const TYPE_CONFIG = {
  plan_ready:        { Icon: Leaf,          label: 'Plan Ready',      borderColor: 'var(--primary)',       glowColor: 'rgba(13,148,136,0.35)' },
  adaptation:        { Icon: RefreshCw,     label: 'Adaptation',      borderColor: 'var(--accent)',         glowColor: 'rgba(245,158,11,0.35)' },
  checkin_reminder:  { Icon: AlarmClock,    label: 'Check-In',        borderColor: 'var(--primary-light)',  glowColor: 'rgba(45,212,191,0.35)' },
  safety_alert:      { Icon: AlertTriangle, label: 'Safety Alert',    borderColor: 'var(--rose)',           glowColor: 'rgba(244,63,94,0.35)'  },
  default:           { Icon: Bell,          label: 'Notification',    borderColor: 'var(--text-muted)',     glowColor: 'rgba(94,138,133,0.25)' },
}

function getTypeConfig(type) {
  return TYPE_CONFIG[type] || TYPE_CONFIG.default
}

// ── Relative time ────────────────────────────────────────────
function relativeTime(dateStr) {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins  = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days  = Math.floor(diff / 86400000)
  if (mins  < 1)   return 'just now'
  if (mins  < 60)  return `${mins}m ago`
  if (hours < 24)  return `${hours}h ago`
  if (days  < 7)   return `${days}d ago`
  return new Date(dateStr).toLocaleDateString()
}

// ── Skeleton loader ──────────────────────────────────────────
function NotificationSkeleton() {
  return (
    <div className="notif-skeleton-wrap">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="notif-skeleton-item">
          <div className="notif-skeleton-icon skeleton" />
          <div className="notif-skeleton-body">
            <div className="notif-skeleton-title skeleton" />
            <div className="notif-skeleton-msg skeleton" />
          </div>
          <div className="notif-skeleton-time skeleton" />
        </div>
      ))}
    </div>
  )
}

// ── Notification card ────────────────────────────────────────
function NotificationCard({ notif, onMarkRead, onDelete, index }) {
  const cfg = getTypeConfig(notif.type)

  return (
    <motion.div
      layout
      className={`notif-card${notif.is_read ? '' : ' notif-card--unread'}`}
      style={{
        '--notif-border': cfg.borderColor,
        '--notif-glow':   cfg.glowColor,
      }}
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20, height: 0, marginBottom: 0 }}
      transition={{ duration: 0.35, delay: index * 0.04, ease: [0.16, 1, 0.3, 1] }}
      onClick={() => !notif.is_read && onMarkRead(notif.id)}
      role="button"
      tabIndex={0}
      onKeyDown={e => e.key === 'Enter' && !notif.is_read && onMarkRead(notif.id)}
      aria-label={`${notif.title}${notif.is_read ? '' : ' — click to mark as read'}`}
    >
      {/* Left border accent */}
      <div className="notif-card-accent" />

      {/* Icon */}
      <div className="notif-card-icon-wrap">
        <span className="notif-card-icon" aria-label={cfg.label} style={{ color: cfg.borderColor }}>
          <cfg.Icon size={18} strokeWidth={2} />
        </span>
        {!notif.is_read && <span className="notif-unread-dot" aria-label="Unread" />}
      </div>

      {/* Content */}
      <div className="notif-card-body">
        <div className="notif-card-top">
          <span className="notif-card-title">{notif.title}</span>
          <span className="notif-card-time">{relativeTime(notif.created_at)}</span>
        </div>
        <p className="notif-card-message">{notif.message}</p>
        <span className="notif-type-badge">{cfg.label}</span>
      </div>

      {/* Read indicator */}
      {!notif.is_read && (
        <div className="notif-read-hint">Tap to mark read</div>
      )}

      <button
        className="notif-delete-btn"
        onClick={(e) => { e.stopPropagation(); onDelete(notif.id) }}
        title="Delete notification"
        aria-label="Delete notification"
      >
        ✕
      </button>
    </motion.div>
  )
}

// ── Main component ───────────────────────────────────────────
export default function Notifications() {
  const [notifications, setNotifications] = useState([])
  const [loading, setLoading]             = useState(true)
  const [markingAll, setMarkingAll]       = useState(false)
  const [error, setError]                 = useState(null)

  const unreadCount = notifications.filter(n => !n.is_read).length

  const fetchNotifications = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const res = await notificationsAPI.list(0, 50)
      const data = Array.isArray(res.data) ? res.data : (res.data?.notifications ?? [])
      // Sort newest first
      setNotifications(data.sort((a, b) => new Date(b.created_at) - new Date(a.created_at)))
    } catch (err) {
      console.error('Failed to load notifications:', err)
      setError('Could not load notifications. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchNotifications() }, [fetchNotifications])

  const handleMarkRead = useCallback(async (id) => {
    // Optimistic update
    setNotifications(prev =>
      prev.map(n => n.id === id ? { ...n, is_read: true } : n)
    )
    try {
      await notificationsAPI.markRead(id)
    } catch {
      // Revert on failure
      setNotifications(prev =>
        prev.map(n => n.id === id ? { ...n, is_read: false } : n)
      )
    }
  }, [])

  const handleDelete = useCallback(async (id) => {
    const prev = notifications
    setNotifications(cur => cur.filter(n => n.id !== id))
    try {
      await notificationsAPI.remove(id)
    } catch {
      setNotifications(prev)
    }
  }, [notifications])

  const handleClearAll = useCallback(async () => {
    if (notifications.length === 0) return
    if (!window.confirm('Clear all notifications? This cannot be undone.')) return
    const prev = notifications
    setNotifications([])
    try {
      await notificationsAPI.clearAll()
    } catch {
      setNotifications(prev)
    }
  }, [notifications])

  const handleMarkAllRead = useCallback(async () => {
    if (markingAll || unreadCount === 0) return
    setMarkingAll(true)
    // Optimistic update
    setNotifications(prev => prev.map(n => ({ ...n, is_read: true })))
    try {
      await notificationsAPI.markAllRead()
    } catch {
      // Revert on failure
      fetchNotifications()
    } finally {
      setMarkingAll(false)
    }
  }, [markingAll, unreadCount, fetchNotifications])

  return (
    <>
      <Helmet>
        <title>Notifications — Ayura AI</title>
        <meta name="description" content="View your Ayura AI health notifications, plan updates, and reminders." />
      </Helmet>

      <div className="notif-root">
        {/* Background orbs */}
        <div className="notif-orb notif-orb-a" aria-hidden="true" />
        <div className="notif-orb notif-orb-b" aria-hidden="true" />

        <div className="notif-container">
          {/* Header */}
          <motion.div
            className="notif-header"
            initial={{ opacity: 0, y: -16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            <div className="notif-header-left">
              <h1 className="notif-page-title gradient-text">Notifications</h1>
              <p className="notif-page-sub">Stay on top of your wellness journey</p>
            </div>
            <div className="notif-header-right">
              {unreadCount > 0 && (
                <motion.span
                  className="notif-count-badge"
                  key={unreadCount}
                  initial={{ scale: 0.7, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                >
                  {unreadCount} unread
                </motion.span>
              )}
              <motion.button
                className="btn btn-secondary btn-sm notif-mark-all-btn"
                onClick={handleMarkAllRead}
                disabled={markingAll || unreadCount === 0}
                whileTap={{ scale: 0.95 }}
              >
                {markingAll ? (
                  <><span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} /> Marking…</>
                ) : (
                  <><CheckCheck size={14} strokeWidth={2.2} /> Mark all read</>
                )}
              </motion.button>
              {notifications.length > 0 && (
                <motion.button
                  className="btn btn-secondary btn-sm notif-clear-all-btn"
                  onClick={handleClearAll}
                  whileTap={{ scale: 0.95 }}
                >
                  <Trash2 size={14} strokeWidth={2} /> Clear all
                </motion.button>
              )}
            </div>
          </motion.div>

          {/* Error */}
          <AnimatePresence>
            {error && (
              <motion.div
                className="notif-error"
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
              >
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}><AlertTriangle size={15} strokeWidth={2} /> {error}</span>
                <button onClick={fetchNotifications} className="notif-retry-btn">Retry</button>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Content */}
          {loading ? (
            <NotificationSkeleton />
          ) : notifications.length === 0 ? (
            <motion.div
              className="notif-empty"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            >
              <div className="notif-empty-icon"><Sparkles size={30} strokeWidth={1.6} /></div>
              <h2 className="notif-empty-title">You're all caught up!</h2>
              <p className="notif-empty-sub">No notifications right now. Check back later.</p>
            </motion.div>
          ) : (
            <div className="notif-list">
              <AnimatePresence mode="popLayout">
                {notifications.map((notif, i) => (
                  <NotificationCard
                    key={notif.id}
                    notif={notif}
                    onMarkRead={handleMarkRead}
                    onDelete={handleDelete}
                    index={i}
                  />
                ))}
              </AnimatePresence>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
