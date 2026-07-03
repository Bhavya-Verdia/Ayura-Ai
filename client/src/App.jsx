import React, { Suspense, useEffect } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { AnimatePresence, m, useReducedMotion } from 'framer-motion'
import { Toaster } from 'sonner'
import { useAuth } from './providers/AuthContext'
import { useTheme } from './providers/ThemeProvider'
import LoadingScreen from './components/LoadingScreen'
import ScrollToTop from './components/ScrollToTop'
import ErrorBoundary from './components/ErrorBoundary'
import NoiseOverlay from './components/NoiseOverlay'
import VitalBackground from './components/VitalBackground'
import MeditationCanvas from './components/MeditationCanvas'
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts'
import useLowPowerMode from './hooks/useLowPowerMode'
import MainLayout from './layouts/MainLayout'
import ReloadPrompt from './components/ReloadPrompt'
import OfflineBanner from './components/OfflineBanner'
import './components/Components.css'

const Landing = React.lazy(() => import('./pages/Landing'))
const Login = React.lazy(() => import('./pages/Login'))
const Register = React.lazy(() => import('./pages/Register'))
const GoogleCallback = React.lazy(() => import('./pages/GoogleCallback'))
const GithubCallback = React.lazy(() => import('./pages/GithubCallback'))

const Onboarding = React.lazy(() => import('./pages/Onboarding'))
const Dashboard = React.lazy(() => import('./pages/Dashboard'))
const Settings = React.lazy(() => import('./pages/Settings'))
const ForgotPassword = React.lazy(() => import('./pages/ForgotPassword'))
const ResetPassword = React.lazy(() => import('./pages/ResetPassword'))
const VerifyEmail = React.lazy(() => import('./pages/VerifyEmail'))
const Admin = React.lazy(() => import('./pages/Admin'))
const NotFound = React.lazy(() => import('./pages/NotFound'))
const Terms = React.lazy(() => import('./pages/Terms'))
const Privacy = React.lazy(() => import('./pages/Privacy'))
const Remedies = React.lazy(() => import('./pages/Remedies'))
const HealthTimeline = React.lazy(() => import('./pages/HealthTimeline'))
const CheckIn = React.lazy(() => import('./pages/CheckIn'))
const Chat = React.lazy(() => import('./pages/Chat'))
const Community = React.lazy(() => import('./pages/Community'))
const DoshaQuiz = React.lazy(() => import('./pages/DoshaQuiz'))
const Notifications = React.lazy(() => import('./pages/Notifications'))
const Reminders = React.lazy(() => import('./pages/Reminders'))
const InteractionChecker = React.lazy(() => import('./pages/InteractionChecker'))
const Progress = React.lazy(() => import('./pages/Progress'))
const DoshaTest = React.lazy(() => import('./pages/DoshaTest'))

function FullPageSpinner() {
  return <LoadingScreen />
}

// Calm, meditative pages where the rising yoga/ॐ field belongs.
// Kept off data-dense app pages (dashboard, chat, settings…) for clarity + perf.
const CALM_BG_ROUTES = new Set([
  '/', '/dosha-test', '/login', '/register', '/forgot-password', '/reset-password', '/verify-email',
])

const pageVariants = {
  initial: { opacity: 0, y: 16, filter: 'blur(2px)' },
  animate: { opacity: 1, y: 0,  filter: 'blur(0px)' },
  exit:    { opacity: 0, y: -8, filter: 'blur(1px)' },
}

const pageVariantsReduced = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit:    { opacity: 0 },
}

const pageTransition      = { duration: 0.38, ease: [0.16, 1, 0.3, 1] }
const pageTransitionFast  = { duration: 0.15 }

function PageWrapper({ children }) {
  const prefersReducedMotion = useReducedMotion()
  const lowPower = useLowPowerMode()
  // On mobile/low-power devices, animating filter: blur() on every route change
  // is GPU-heavy and stutters. Fall back to the cheap opacity-only transition
  // there too — not just when the OS "reduce motion" flag is set.
  const cheap = prefersReducedMotion || lowPower
  return (
    <m.div
      variants={cheap ? pageVariantsReduced : pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={cheap ? pageTransitionFast : pageTransition}
      style={{ minHeight: '100dvh' }}
      id="main-content"
      tabIndex={-1}
    >
      <Suspense fallback={<FullPageSpinner />}>
        {children}
      </Suspense>
    </m.div>
  )
}

function PrivateRoute({ children, requireOnboardingComplete = false }) {
  const { user, loading } = useAuth()
  if (loading) return <FullPageSpinner />
  if (!user) return <Navigate to="/login" replace />

  if (requireOnboardingComplete && !user.onboarding_complete) {
    return <Navigate to="/onboarding" replace />
  }
  return children
}

function AdminRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <FullPageSpinner />
  if (!user || !user.is_admin) return <Navigate to="/dashboard" replace />
  return children
}

function OnboardingRoute({ children }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) return <FullPageSpinner />
  if (!user) return <Navigate to="/login" replace />
  // Allow re-entry if navigated explicitly (Settings page can link here)
  const isRetake = new URLSearchParams(location.search).get('retake') === 'true'
  if (user.onboarding_complete && location.pathname === '/onboarding' && !isRetake) {
    return <Navigate to="/dashboard" replace />
  }
  return children
}

function PublicRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <FullPageSpinner />
  if (user) {
    return user.onboarding_complete ? <Navigate to="/dashboard" replace /> : <Navigate to="/onboarding" replace />
  }
  return children
}

export default function App() {
  const location = useLocation()
  const { theme } = useTheme()
  useKeyboardShortcuts()

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [location.pathname])

  return (
    <>
      <a href="#main-content" className="skip-link">Skip to content</a>
      <VitalBackground />
      {CALM_BG_ROUTES.has(location.pathname) && <MeditationCanvas />}
      <ErrorBoundary>
        <AnimatePresence mode="wait">
          <Routes location={location}>
            <Route path="/" element={<PageWrapper><Landing /></PageWrapper>} />
            <Route path="/login" element={<PublicRoute><PageWrapper><Login /></PageWrapper></PublicRoute>} />
            <Route path="/register" element={<PublicRoute><PageWrapper><Register /></PageWrapper></PublicRoute>} />
            <Route path="/forgot-password" element={<PageWrapper><ForgotPassword /></PageWrapper>} />
            <Route path="/reset-password" element={<PageWrapper><ResetPassword /></PageWrapper>} />
            <Route path="/verify-email" element={<PageWrapper><VerifyEmail /></PageWrapper>} />
            <Route path="/dosha-test" element={<PageWrapper><DoshaTest /></PageWrapper>} />
            <Route path="/terms" element={<PageWrapper><Terms /></PageWrapper>} />
            <Route path="/privacy" element={<PageWrapper><Privacy /></PageWrapper>} />
            <Route path="/admin" element={<AdminRoute><PageWrapper><Admin /></PageWrapper></AdminRoute>} />
            <Route path="/auth/google/callback" element={<GoogleCallback />} />
            <Route path="/auth/github/callback" element={<GithubCallback />} />
            <Route path="/onboarding" element={<OnboardingRoute><PageWrapper><Onboarding /></PageWrapper></OnboardingRoute>} />
            
            <Route element={<PrivateRoute requireOnboardingComplete><MainLayout /></PrivateRoute>}>
              <Route path="/dashboard/*" element={<PageWrapper><Dashboard /></PageWrapper>} />
              <Route path="/progress" element={<PageWrapper><Progress /></PageWrapper>} />
              <Route path="/remedies" element={<PageWrapper><Remedies /></PageWrapper>} />
              <Route path="/timeline" element={<PageWrapper><HealthTimeline /></PageWrapper>} />
              <Route path="/checkin" element={<PageWrapper><CheckIn /></PageWrapper>} />
              <Route path="/chat" element={<PageWrapper><Chat /></PageWrapper>} />
              <Route path="/settings" element={<PageWrapper><Settings /></PageWrapper>} />
              <Route path="/community" element={<PageWrapper><Community /></PageWrapper>} />
              <Route path="/dosha-quiz" element={<PageWrapper><DoshaQuiz /></PageWrapper>} />
              <Route path="/notifications" element={<PageWrapper><Notifications /></PageWrapper>} />
              <Route path="/reminders" element={<PageWrapper><Reminders /></PageWrapper>} />
              <Route path="/interaction-check" element={<PageWrapper><InteractionChecker /></PageWrapper>} />
            </Route>
            
            <Route path="*" element={<PageWrapper><NotFound /></PageWrapper>} />
          </Routes>
        </AnimatePresence>
      </ErrorBoundary>
    <ScrollToTop />
    <NoiseOverlay />
    <OfflineBanner />
    <ReloadPrompt />
    <Toaster
        position="top-right"
        theme={theme || 'dark'}
        toastOptions={{
          style: {
            background: 'var(--glass-bg)',
            border: '1px solid var(--border-light)',
            color: 'var(--ayura-ink)',
            fontFamily: 'Manrope, sans-serif',
            backdropFilter: 'blur(24px)',
          },
          className: 'ayura-toast',
        }}
        richColors
      />
    </>
  )
}
