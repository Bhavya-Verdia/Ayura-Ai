import React, { Suspense, useEffect } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { m, useReducedMotion } from 'framer-motion'
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
import ReloadPrompt from './components/ReloadPrompt'
import OfflineBanner from './components/OfflineBanner'

// Lazy like the pages: the app shell (sidebar, command palette, feedback
// widget + Dashboard.css) is only for authenticated users — statically
// importing it shipped ~38KB of render-blocking CSS/JS to every anonymous
// Landing visitor.
const MainLayout = React.lazy(() => import('./layouts/MainLayout'))
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

// Calm, meditative pages where the rising yoga/ॐ field belongs.
// Kept off data-dense app pages (dashboard, chat, settings…) for clarity + perf.
const CALM_BG_ROUTES = new Set([
  '/', '/dosha-test', '/login', '/register', '/forgot-password', '/reset-password', '/verify-email',
])

// NO filter/blur in entrance variants — ever. An animated (or lingering
// blur(0px)) filter puts the ENTIRE page in one giant GPU render surface,
// which composites EMPTY for a frame on hover/selection/scroll invalidation:
// the app-wide flicker of 2026-07. Opacity+y read nearly identically.
const pageVariants = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
}

const pageVariantsReduced = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
}

const pageTransition      = { duration: 0.38, ease: [0.16, 1, 0.3, 1] }
const pageTransitionFast  = { duration: 0.15 }

function PageWrapper({ children, inLayout = false }) {
  const prefersReducedMotion = useReducedMotion()
  const lowPower = useLowPowerMode()
  // Animating filter: blur() on a route change repaints the whole page every
  // frame — fine on desktop GPUs, a visible hitch on phones. Touch devices get
  // the same-duration opacity fade instead (smooth beats blurry-and-janky);
  // reduced-motion users get it too.
  const touch = typeof window !== 'undefined' && !!window.matchMedia
    && window.matchMedia('(pointer: coarse), (max-width: 900px)').matches
  const cheap = prefersReducedMotion || lowPower || touch

  // Inside the app shell, MainLayout already animates route changes and owns
  // the Suspense boundary (with route-aware skeleton fallbacks). A second
  // motion div + Suspense here would double the entrance animation and steal
  // the fallback (full-screen spinner instead of skeletons) — so render just
  // the skip-link landmark.
  if (inLayout) {
    return (
      <div id="main-content" tabIndex={-1}>
        {children}
      </div>
    )
  }

  return (
    <m.div
      variants={cheap ? pageVariantsReduced : pageVariants}
      initial="initial"
      animate="animate"
      transition={cheap ? pageTransitionFast : pageTransition}
      style={{ minHeight: '100dvh' }}
      id="main-content"
      tabIndex={-1}
    >
      <Suspense fallback={<LoadingScreen />}>
        {children}
      </Suspense>
    </m.div>
  )
}

function PrivateRoute({ children, requireOnboardingComplete = false }) {
  const { user, loading } = useAuth()
  if (loading) return <LoadingScreen />
  if (!user) return <Navigate to="/login" replace />

  if (requireOnboardingComplete && !user.onboarding_complete) {
    return <Navigate to="/onboarding" replace />
  }
  return children
}

function AdminRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <LoadingScreen />
  if (!user || !user.is_admin) return <Navigate to="/dashboard" replace />
  return children
}

function OnboardingRoute({ children }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) return <LoadingScreen />
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
  if (loading) return <LoadingScreen />
  if (user) {
    return user.onboarding_complete ? <Navigate to="/dashboard" replace /> : <Navigate to="/onboarding" replace />
  }
  return children
}

export default function App() {
  const location = useLocation()
  const { theme } = useTheme()
  const lowPower = useLowPowerMode()
  useKeyboardShortcuts()

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [location.pathname])

  return (
    <>
      <a href="#main-content" className="skip-link">Skip to content</a>
      <VitalBackground />
      {/* MeditationCanvas (a full-viewport canvas redrawing every frame) was a
          confirmed contributor to the app-wide compositing flicker, so it stays
          retired. Do not re-mount without a cross-device (Mac + Android) flicker
          re-test on a real display. */}
      {false && !lowPower && CALM_BG_ROUTES.has(location.pathname) && <MeditationCanvas />}
      <ErrorBoundary>
        {/* Catches the lazy MainLayout itself; pages inside it fall to nearer
            boundaries (MainLayout's skeletons / PageWrapper's spinner). */}
        <Suspense fallback={<LoadingScreen />}>
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
              <Route path="/dashboard/*" element={<PageWrapper inLayout><Dashboard /></PageWrapper>} />
              <Route path="/progress" element={<PageWrapper inLayout><Progress /></PageWrapper>} />
              <Route path="/remedies" element={<PageWrapper inLayout><Remedies /></PageWrapper>} />
              <Route path="/timeline" element={<PageWrapper inLayout><HealthTimeline /></PageWrapper>} />
              <Route path="/checkin" element={<PageWrapper inLayout><CheckIn /></PageWrapper>} />
              <Route path="/chat" element={<PageWrapper inLayout><Chat /></PageWrapper>} />
              <Route path="/settings" element={<PageWrapper inLayout><Settings /></PageWrapper>} />
              <Route path="/community" element={<PageWrapper inLayout><Community /></PageWrapper>} />
              <Route path="/dosha-quiz" element={<PageWrapper inLayout><DoshaQuiz /></PageWrapper>} />
              <Route path="/notifications" element={<PageWrapper inLayout><Notifications /></PageWrapper>} />
              <Route path="/reminders" element={<PageWrapper inLayout><Reminders /></PageWrapper>} />
              <Route path="/interaction-check" element={<PageWrapper inLayout><InteractionChecker /></PageWrapper>} />
            </Route>
            
            <Route path="*" element={<PageWrapper><NotFound /></PageWrapper>} />
          </Routes>
        </Suspense>
      </ErrorBoundary>
    <ScrollToTop />
    {/* Static grain (feTurbulence baked into a 220px tiled data-URI) — a single
        static paint, safe to keep on. */}
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
            fontFamily: 'var(--font-ui)',
            backdropFilter: 'blur(24px)',
          },
          className: 'ayura-toast',
        }}
        richColors
      />
    </>
  )
}
