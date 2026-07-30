import React, { useState, useEffect, useContext } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { m, AnimatePresence, useReducedMotion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { AuthContext } from '../providers/AuthContext'
import { useTheme } from '../providers/ThemeProvider'
import LoadingScreen from '../components/LoadingScreen'
import { SkeletonDashboard, SkeletonChat } from '../components/Skeleton'
import {
  LayoutDashboard, MessageCircle, Activity, CheckSquare,
  Settings, LogOut, Menu, X, Bell, TrendingUp, Users, AlarmClock, Brain, ShieldCheck, Soup,
  MessageSquare, Sun, Moon
} from 'lucide-react'
import ScrollToTop from '../components/ScrollToTop'
import FeedbackWidget from '../components/FeedbackWidget'
import CommandPalette from '../components/CommandPalette'
import { DOSHA_COLOR } from '../constants/dosha'
import '../pages/Dashboard.css'
import './MainLayout.css'

// Sidebar nav — grouped logically: Home & AI → Track & Assess → Tools → Social & Account.
// The wellness plans (routine, diet, yoga, gym, panchakarma) live on the Dashboard as
// generated plan cards, so they are intentionally NOT duplicated here. Remedies is the
// exception: /remedies is the canonical home for BOTH remedies and medicines — it is
// where symptoms are chosen (the generator needs them) and the only surface that shows
// both plans together — so it earns a permanent Tools entry.
const NAV_ITEMS = [
  // Home & AI
  { id: 'dashboard',    label: 'Dashboard',    Icon: LayoutDashboard, path: '/dashboard',     i18nKey: 'dashboard_title' },
  { id: 'chat',         label: 'AI Assistant', Icon: MessageCircle,   path: '/chat',           i18nKey: 'chat' },
  // Track & Assess. `startsGroup` draws a hairline rule above the item — the
  // three groups below were only ever comments in this file, so the rendered
  // sidebar was 12 undifferentiated rows. A rule costs ~9px of height each,
  // where a labelled section header would have cost ~30px and overflowed.
  { id: 'progress',     label: 'Progress',     Icon: TrendingUp,      path: '/progress',       i18nKey: 'progress', startsGroup: true },
  { id: 'checkin',      label: 'Check-In',     Icon: CheckSquare,     path: '/checkin',        i18nKey: 'checkin' },
  { id: 'timeline',     label: 'Timeline',     Icon: Activity,        path: '/timeline',       i18nKey: 'timeline' },
  { id: 'dosha-quiz',   label: 'Dosha Quiz',   Icon: Brain,           path: '/dosha-quiz',     i18nKey: 'dosha_quiz' },
  // Tools
  { id: 'remedies',     label: 'Remedies',     Icon: Soup,            path: '/remedies',       i18nKey: 'remedies', startsGroup: true },
  { id: 'interaction',  label: 'Herb Safety',  Icon: ShieldCheck,     path: '/interaction-check', i18nKey: 'interaction_check' },
  { id: 'reminders',    label: 'Reminders',    Icon: AlarmClock,      path: '/reminders',      i18nKey: 'reminders' },
  // Social & Account
  { id: 'community',    label: 'Community',    Icon: Users,           path: '/community',      i18nKey: 'community', startsGroup: true },
  { id: 'notifications',label: 'Notifications',Icon: Bell,            path: '/notifications',  i18nKey: 'notifications' },
  { id: 'settings',     label: 'Settings',     Icon: Settings,        path: '/settings',       i18nKey: 'settings' },
]

// Exactly the breakpoint the layout CSS uses (`@media (max-width: 900px)` in
// Dashboard.css / index.css). The old JS test was `innerWidth < 900`, which
// EXCLUDED 900 — so at exactly 900px CSS applied the mobile drawer/tab-bar
// rules while JS still rendered the desktop sidebar.
const MOBILE_QUERY = '(max-width: 900px)'

const BOTTOM_NAV = [
  { id: 'dashboard', label: 'Home',      Icon: LayoutDashboard, path: '/dashboard' },
  { id: 'chat',      label: 'AI Chat',   Icon: MessageCircle,   path: '/chat' },
  { id: 'progress',  label: 'Progress',  Icon: TrendingUp,      path: '/progress' },
  { id: 'community', label: 'Community', Icon: Users,           path: '/community' },
  { id: 'settings',  label: 'More',      Icon: Settings,        path: '/settings' },
]

export default function MainLayout() {
  const { user, logout } = useContext(AuthContext)
  const { theme, setThemeAnimated } = useTheme()
  const { t } = useTranslation()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  // Initialise synchronously from the real viewport so the first paint already
  // matches the device — avoids the flash where the desktop sidebar renders for
  // one frame on a phone before JS measures. (MainLayout is auth-only and never
  // prerendered, so `window` is always available here; guarded anyway.)
  const [isMobile, setIsMobile] = useState(
    () => typeof window !== 'undefined' && window.matchMedia(MOBILE_QUERY).matches
  )

  // matchMedia, NOT a `resize` listener: Android fires `resize` on every
  // URL-bar show/hide, i.e. continuously while scrolling, so the old handler
  // ran a layout read (innerWidth) + setState on the whole shell mid-scroll.
  // A media-query listener fires only when the breakpoint is actually crossed.
  useEffect(() => {
    const mq = window.matchMedia(MOBILE_QUERY)
    const update = () => setIsMobile(mq.matches)
    update()
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
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
      const warm = (p) => p.catch(() => {}) // prefetch failure must stay silent
      warm(import('../components/PlanViewer'))
      warm(import('../pages/Chat'))
      warm(import('../pages/Progress'))
      warm(import('../pages/Community'))
      warm(import('../pages/Settings'))
    })
    return () => cancel(id)
  }, [])

  const location = useLocation()
  const isChatRoute = location.pathname.startsWith('/chat')
  const prefersReducedMotion = useReducedMotion()
  const doshaBadgeColor = DOSHA_COLOR[user?.dominant_dosha?.toLowerCase()] || DOSHA_COLOR.default
  const initials = user?.name ? user.name.split(' ').map(w => w[0]).join('').slice(0,2).toUpperCase() : 'AY'

  return (
    <div className="dash-root">
      {/* Mobile sidebar overlay */}
      <AnimatePresence>
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
      </AnimatePresence>

      {/* ── SIDEBAR ── */}
      <aside className={`dash-sidebar${isMobile ? ` mobile${sidebarOpen ? ' open' : ''}` : ''}`}>
        {/* Brand */}
        {/* The theme toggle used to be a lone right-aligned pill in its own band
            at the top of the DASHBOARD ONLY — an otherwise empty strip on one
            page, and no way to flip theme from any other. It rides the brand
            row's spare horizontal space instead: available on every authed
            page, and it costs the sidebar no extra height. (Settings still has
            the explicit Dark/Light pair; this is the quick toggle.) */}
        <div className="dash-sidebar-brand">
          <img src="/favicon.svg" alt="Ayura AI Logo" className="dash-sidebar-brand-mark" />
          <span className="dash-sidebar-brand-text">Ayura AI</span>
          <button
            type="button"
            className="dash-sidebar-theme-toggle"
            onClick={(e) => setThemeAnimated(theme === 'dark' ? 'light' : 'dark', e)}
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {theme === 'dark' ? <Sun size={16} strokeWidth={2} /> : <Moon size={16} strokeWidth={2} />}
          </button>
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
                className={({ isActive }) => `dash-nav-item${isActive ? ' active' : ''}${item.startsGroup ? ' starts-group' : ''}`}
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

        {/* Feedback lives here, in the sidebar, rather than in a floating FAB:
            a fixed overlay button won the hit-test against whatever scrolled
            under it (see FeedbackWidget.jsx). The sidebar is chrome, so it can
            never cover page content. Also mirrored in Settings. */}
        <button
          className="dash-sidebar-signout dash-sidebar-feedback"
          onClick={() => window.dispatchEvent(new CustomEvent('ayura:open-feedback'))}
        >
          <MessageSquare size={16} strokeWidth={2} />
          {t('send_feedback') || 'Send feedback'}
        </button>

        <button className="dash-sidebar-signout" onClick={logout}>
          <LogOut size={16} strokeWidth={2} />
          {t('logout') || 'Sign out'}
        </button>
      </aside>

      {/* ── MAIN CONTENT ── */}
      {/* `fill-viewport-h` (index.css), not an inline height: this height is
          load-bearing — it is what makes the column below it scroll instead of
          the page — and the dynamic viewport unit that tracks the Android/iOS
          URL bar needs a `100vh` base to fall back to. An inline style object
          has one key per property, so it cannot express that pair. */}
      <div
        className={`dash-main-container fill-viewport-h${isMobile ? ' mobile' : ''}`}
        style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}
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

        {/* `mode="wait"` holds the incoming route until the outgoing one has
            finished exiting, so a tab tap cost exit + enter back to back. The
            exit is now a fast fade (no y-drift) — on a phone, where the tap is
            the only feedback you get, total perceived latency matters more than
            the outgoing flourish. */}
        <AnimatePresence mode="wait" initial={false}>
          <m.div
            key={location.pathname}
            initial={prefersReducedMotion ? {} : { opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={prefersReducedMotion ? {} : { opacity: 0 }}
            transition={prefersReducedMotion
              ? { duration: 0 }
              : { duration: 0.24, ease: [0.16, 1, 0.3, 1], opacity: { duration: 0.1 } }}
            /* Bottom padding clears BOTH the fixed tab bar (64px+safe) and the
               floating feedback FAB above it (bottom 64+safe+18, 56px tall) so
               end-of-scroll content — pose tags, the remedies tab strip — never
               sits trapped under the FAB on phones. Chat is the exception: it
               is not a scrolling document but a fixed-height panel with its own
               inner scroller, and FeedbackWidget.css already hides the FAB
               there — so the extra ~76px only shrank the message area and
               floated the composer above the tab bar for no reason.

               overscroll-behavior: contain stops a flick past the end of this
               scroller from chaining into the document — which on Android is
               what triggers pull-to-refresh mid-scroll, and on iOS is the
               whole-page rubber-band under the fixed tab bar. */
            style={{
              flex: 1,
              overflowY: 'auto',
              overscrollBehavior: 'contain',
              WebkitOverflowScrolling: 'touch',
              paddingBottom: isMobile
                ? `calc(${isChatRoute ? '64px' : '140px'} + env(safe-area-inset-bottom))`
                : 0,
              height: '100%',
            }}
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
