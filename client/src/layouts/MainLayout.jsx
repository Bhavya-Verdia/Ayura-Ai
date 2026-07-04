import React, { useState, useEffect, useContext } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { m, AnimatePresence, useReducedMotion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { AuthContext } from '../providers/AuthContext'
import LoadingScreen from '../components/LoadingScreen'
import { SkeletonDashboard, SkeletonChat } from '../components/Skeleton'
import {
  LayoutDashboard, MessageCircle, Activity, CheckSquare,
  Settings, LogOut, Menu, X, Bell, TrendingUp, Users, AlarmClock, Brain, ShieldCheck
} from 'lucide-react'
import ScrollToTop from '../components/ScrollToTop'
import FeedbackWidget from '../components/FeedbackWidget'
import CommandPalette from '../components/CommandPalette'
import { DOSHA_COLOR } from '../constants/dosha'
import '../pages/Dashboard.css'
import './MainLayout.css'

// Sidebar nav — grouped logically: Home & AI → Track & Assess → Tools → Social & Account.
// The 7 wellness plans (routine, diet, yoga, gym, panchakarma, remedies, medicines) live
// on the Dashboard as generated plan cards, so they are intentionally NOT duplicated here.
const NAV_ITEMS = [
  // Home & AI
  { id: 'dashboard',    label: 'Dashboard',    Icon: LayoutDashboard, path: '/dashboard',     i18nKey: 'dashboard_title' },
  { id: 'chat',         label: 'AI Assistant', Icon: MessageCircle,   path: '/chat',           i18nKey: 'chat' },
  // Track & Assess
  { id: 'progress',     label: 'Progress',     Icon: TrendingUp,      path: '/progress',       i18nKey: 'progress' },
  { id: 'checkin',      label: 'Check-In',     Icon: CheckSquare,     path: '/checkin',        i18nKey: 'checkin' },
  { id: 'timeline',     label: 'Timeline',     Icon: Activity,        path: '/timeline',       i18nKey: 'timeline' },
  { id: 'dosha-quiz',   label: 'Dosha Quiz',   Icon: Brain,           path: '/dosha-quiz',     i18nKey: 'dosha_quiz' },
  // Tools
  { id: 'interaction',  label: 'Herb Safety',  Icon: ShieldCheck,     path: '/interaction-check', i18nKey: 'interaction_check' },
  { id: 'reminders',    label: 'Reminders',    Icon: AlarmClock,      path: '/reminders',      i18nKey: 'reminders' },
  // Social & Account
  { id: 'community',    label: 'Community',    Icon: Users,           path: '/community',      i18nKey: 'community' },
  { id: 'notifications',label: 'Notifications',Icon: Bell,            path: '/notifications',  i18nKey: 'notifications' },
  { id: 'settings',     label: 'Settings',     Icon: Settings,        path: '/settings',       i18nKey: 'settings' },
]

const BOTTOM_NAV = [
  { id: 'dashboard', label: 'Home',      Icon: LayoutDashboard, path: '/dashboard' },
  { id: 'chat',      label: 'AI Chat',   Icon: MessageCircle,   path: '/chat' },
  { id: 'progress',  label: 'Progress',  Icon: TrendingUp,      path: '/progress' },
  { id: 'community', label: 'Community', Icon: Users,           path: '/community' },
  { id: 'settings',  label: 'More',      Icon: Settings,        path: '/settings' },
]

export default function MainLayout() {
  const { user, logout } = useContext(AuthContext)
  const { t } = useTranslation()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  // Initialise synchronously from the real viewport so the first paint already
  // matches the device — avoids the flash where the desktop sidebar renders for
  // one frame on a phone before JS measures. (MainLayout is auth-only and never
  // prerendered, so `window` is always available here; guarded anyway.)
  const [isMobile, setIsMobile] = useState(
    () => typeof window !== 'undefined' && window.innerWidth < 900
  )

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 900)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  // Idle prefetch of the lazy chunks a logged-in user is most likely to hit
  // next (PlanViewer is behind every plan-card tap; the rest are the main
  // tabs). Vite dedupes by module URL, so these resolve to the same chunks the
  // router lazy-loads — after this warms the cache, navigation is instant even
  // on slow mobile connections. requestIdleCallback keeps it off the critical
  // path; Safari lacks it, so fall back to a timer.
  useEffect(() => {
    const idle = window.requestIdleCallback || ((cb) => setTimeout(cb, 2000))
    const cancel = window.cancelIdleCallback || clearTimeout
    const id = idle(() => {
      import('../components/PlanViewer')
      import('../pages/Chat')
      import('../pages/Progress')
      import('../pages/Community')
      import('../pages/Settings')
    })
    return () => cancel(id)
  }, [])

  const location = useLocation()
  const prefersReducedMotion = useReducedMotion()
  const doshaBadgeColor = DOSHA_COLOR[user?.dominant_dosha?.toLowerCase()] || DOSHA_COLOR.default
  const initials = user?.name ? user.name.split(' ').map(w => w[0]).join('').slice(0,2).toUpperCase() : 'AY'

  return (
    <div className="dash-root">
      {/* Mobile sidebar overlay */}
      {isMobile && sidebarOpen && (
        <m.button
          className="dash-overlay"
          onClick={() => setSidebarOpen(false)}
          aria-label="Close menu"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        />
      )}

      {/* ── SIDEBAR ── */}
      <aside className={`dash-sidebar${isMobile ? ` mobile${sidebarOpen ? ' open' : ''}` : ''}`}>
        {/* Brand */}
        <div className="dash-sidebar-brand">
          <img src="/favicon.svg" alt="Ayura AI Logo" className="dash-sidebar-brand-mark" />
          <span className="dash-sidebar-brand-text">Ayura AI</span>
        </div>

        {/* Profile card */}
        <div className="dash-sidebar-profile">
          <div
            className="dash-sidebar-avatar"
            style={{ background: `linear-gradient(135deg, ${doshaBadgeColor}44, ${doshaBadgeColor}22)`, border: `1px solid ${doshaBadgeColor}44` }}
          >
            {initials}
          </div>
          <div>
            <div className="dash-sidebar-name">{user?.name || 'User'}</div>
            {user?.dominant_dosha && (
              <div className="dash-sidebar-dosha" style={{ color: doshaBadgeColor }}>
                {user.dominant_dosha} dosha
              </div>
            )}
          </div>
        </div>

        {/* Navigation */}
        <nav className="dash-sidebar-nav">
          {NAV_ITEMS.map(item => {
            const { Icon } = item
            return (
              <NavLink
                key={item.id}
                to={item.path}
                className={({ isActive }) => `dash-nav-item${isActive ? ' active' : ''}`}
                onClick={() => { if (isMobile) setSidebarOpen(false) }}
              >
                {({ isActive }) => (
                  <>
                    <Icon size={18} strokeWidth={isActive ? 2.5 : 2} className="dash-nav-icon-svg" />
                    <span className="dash-nav-label">{t(item.i18nKey) || item.label}</span>
                    {isActive && (
                      <m.div
                        className="dash-nav-indicator"
                        initial={{ opacity: 0, scaleY: 0.4 }}
                        animate={{ opacity: 1, scaleY: 1 }}
                        transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
                      />
                    )}
                  </>
                )}
              </NavLink>
            )
          })}
        </nav>

        <button className="dash-sidebar-signout" onClick={logout}>
          <LogOut size={16} strokeWidth={2} />
          {t('logout') || 'Sign out'}
        </button>
      </aside>

      {/* ── MAIN CONTENT ── */}
      <div
        className={`dash-main-container${isMobile ? ' mobile' : ''}`}
        /* 100dvh (dynamic viewport) tracks Android/iOS URL-bar show/hide so the
           shell doesn't overflow or leave a gap when the bar animates. */
        style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100dvh', overflow: 'hidden' }}
      >
        {/* Mobile topbar */}
        {isMobile && (
          <div className="dash-mobile-bar" style={{ flexShrink: 0 }}>
            <button className="dash-hamburger" onClick={() => setSidebarOpen(true)} aria-label="Open menu">
              <Menu size={22} strokeWidth={2} color="var(--ayura-ink)" />
            </button>
            <div className="dash-mobile-brand">
              <img src="/favicon.svg" alt="Ayura AI Logo" className="dash-mobile-brand-mark" />
              <span className="dash-mobile-brand-text">Ayura AI</span>
            </div>
            <Link to="/notifications" className="dash-mobile-bell" aria-label="Notifications">
              <Bell size={20} strokeWidth={2} />
            </Link>
          </div>
        )}

        <AnimatePresence mode="wait" initial={false}>
          <m.div
            key={location.pathname}
            initial={prefersReducedMotion ? {} : { opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={prefersReducedMotion ? {} : { opacity: 0, y: -6 }}
            transition={prefersReducedMotion ? { duration: 0 } : { duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
            style={{ flex: 1, overflowY: 'auto', paddingBottom: isMobile ? 'calc(72px + env(safe-area-inset-bottom))' : 0, height: '100%' }}
          >
            <ScrollToTop />
            <React.Suspense fallback={
              location.pathname.startsWith('/dashboard')
                ? <SkeletonDashboard />
                : location.pathname.startsWith('/chat')
                ? <SkeletonChat />
                : <LoadingScreen />
            }>
              <Outlet />
            </React.Suspense>
            <FeedbackWidget />
          </m.div>
        </AnimatePresence>
      </div>

      {/* ── MOBILE BOTTOM TAB BAR ── */}
      {isMobile && (
        <nav className="mobile-bottom-nav">
          {BOTTOM_NAV.map(item => {
            const { Icon } = item
            return (
              <NavLink
                key={item.id}
                to={item.path}
                className={({ isActive }) => `mobile-bottom-tab${isActive ? ' active' : ''}`}
                onClick={() => setSidebarOpen(false)}
              >
                {({ isActive }) => (
                  <>
                    <m.div
                      animate={isActive ? { scale: 1.12, y: -2 } : { scale: 1, y: 0 }}
                      transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                    >
                      <Icon size={22} strokeWidth={isActive ? 2.5 : 2} />
                    </m.div>
                    <span>{item.label}</span>
                  </>
                )}
              </NavLink>
            )
          })}
        </nav>
      )}

      {/* ── COMMAND PALETTE ── */}
      <CommandPalette />
    </div>
  )
}
