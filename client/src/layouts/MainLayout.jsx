import React, { useState, useEffect, useContext } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { AuthContext } from '../providers/AuthContext'
import LoadingScreen from '../components/LoadingScreen'
import {
  LayoutDashboard, MessageCircle, Leaf, Activity, CheckSquare,
  Settings, LogOut, Menu, X, Bell
} from 'lucide-react'
import '../pages/Dashboard.css'
import './MainLayout.css'

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard',    Icon: LayoutDashboard, path: '/dashboard',     i18nKey: 'dashboard_title' },
  { id: 'chat',      label: 'AI Assistant', Icon: MessageCircle,   path: '/chat',           i18nKey: 'chat' },
  { id: 'remedies',  label: 'Remedies',     Icon: Leaf,            path: '/remedies',       i18nKey: 'home_remedies' },
  { id: 'timeline',  label: 'Timeline',     Icon: Activity,        path: '/timeline',       i18nKey: 'timeline' },
  { id: 'checkin',   label: 'Check-In',     Icon: CheckSquare,     path: '/checkin',        i18nKey: 'checkin' },
  { id: 'settings',  label: 'Settings',     Icon: Settings,        path: '/settings',       i18nKey: 'settings' },
]

const BOTTOM_NAV = [
  { id: 'dashboard', label: 'Home',      Icon: LayoutDashboard, path: '/dashboard' },
  { id: 'chat',      label: 'AI Chat',   Icon: MessageCircle,   path: '/chat' },
  { id: 'checkin',   label: 'Check-In',  Icon: CheckSquare,     path: '/checkin' },
  { id: 'remedies',  label: 'Remedies',  Icon: Leaf,            path: '/remedies' },
  { id: 'settings',  label: 'More',      Icon: Settings,        path: '/settings' },
]

const DOSHA_COLOR = { vata: '#818CF8', pitta: '#FB923C', kapha: '#2DD4BF' }

export default function MainLayout() {
  const { user, logout } = useContext(AuthContext)
  const { t } = useTranslation()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 900)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  const doshaBadgeColor = DOSHA_COLOR[user?.dominant_dosha?.toLowerCase()] || '#2DD4BF'
  const initials = user?.name ? user.name.split(' ').map(w => w[0]).join('').slice(0,2).toUpperCase() : 'AY'

  return (
    <div className="dash-root">
      {/* Mobile sidebar overlay */}
      {isMobile && sidebarOpen && (
        <motion.button
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
                    {isActive && <motion.div className="dash-nav-indicator" layoutId="navIndicator" />}
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
        style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}
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
          </div>
        )}

        <div style={{ flex: 1, overflowY: 'auto', paddingBottom: isMobile ? '72px' : 0 }}>
          <React.Suspense fallback={<LoadingScreen />}>
            <Outlet />
          </React.Suspense>
        </div>
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
                <Icon size={22} strokeWidth={2} />
                <span>{item.label}</span>
              </NavLink>
            )
          })}
        </nav>
      )}
    </div>
  )
}
