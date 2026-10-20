/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import {
  authAPI,
  profileAPI,
  clearAuthTokens,
  setAuthTokens,
} from '../api/client'
import { resetQueryCache } from '../queryClient'
import { identifyUser, resetAnalytics } from '../lib/analytics'
import { markReturningUser, clearReturningUser, isReturningUser } from '../lib/sessionHint'

export const AuthContext = createContext(null)

function mapProfileToUser(data) {
  return {
    id: data.id,
    name: data.name,
    email: data.email,
    avatar: data.avatar_url,
    onboarding_complete: Boolean(data.onboarding_complete),
    dominant_dosha: data.dominant_dosha,
    is_admin: Boolean(data.is_admin),
  }
}

// Pages an anonymous visitor reads without a session. On these, a browser that
// has never been signed in (lib/sessionHint.js) skips the boot /profile/me
// check: for a first-time visitor it was two failed requests (profile 401,
// refresh 401) on every landing page view, and its answer arriving while the
// prerendered page was still hydrating made React redraw the page. The check
// runs as soon as the visitor opens any other route.
//
// Safe because every sign-in writes the hint (fetchProfile, below) and has
// done since 2026-08-11, while a session lasts 7 days: a browser holding a
// live session cookie and no hint is one whose site storage was cleared. That
// visitor sees the signed-out landing page until they open the app.
const ANONYMOUS_PATHS = new Set([
  '/', '/dosha-test', '/terms', '/privacy', '/login', '/register', '/forgot-password',
])

export function AuthProvider({ children }) {
  const { pathname } = useLocation()
  const [user, setUser]       = useState(null)
  const [profile, setProfile] = useState(null)
  // Null until the first check has run. Starts settled only where the check
  // is skipped, so a guarded route never renders once with no user and no
  // pending check (which would redirect a signed-in user to /login).
  const [checked, setChecked] = useState(() => ANONYMOUS_PATHS.has(pathname) && !isReturningUser() ? false : null)
  const needsCheck = checked === null || (checked === false && !ANONYMOUS_PATHS.has(pathname))
  // needsCheck stays true until fetchProfile settles `checked`, so this is
  // the loading state; login() calling fetchProfile leaves it alone.
  const loading = needsCheck

  useEffect(() => {
    if (needsCheck) fetchProfile()
  }, [needsCheck])

  useEffect(() => {
    const handleAuthExpired = () => {
      clearAuthTokens()
      setUser(null)
      setProfile(null)
      resetAnalytics()
      clearReturningUser()
      resetQueryCache()
    }
    window.addEventListener('auth-expired', handleAuthExpired)
    return () => window.removeEventListener('auth-expired', handleAuthExpired)
  }, [])

  async function fetchProfile() {
    try {
      const { data } = await profileAPI.getMe()
      setProfile(data)
      setUser(mapProfileToUser(data))
      // Every login path (email, Google, GitHub, OTP) funnels through here, so
      // this is the one place identity needs binding. Id only — never the email
      // or any profile field, per the privacy contract in lib/analytics.js.
      identifyUser(data.id)
      // Same reason this is the one place to record that this browser has a
      // session at all, so the NEXT cold load can fetch the app shell's chunks
      // in parallel with this request rather than after it (see App.jsx).
      markReturningUser()
    } catch {
      clearAuthTokens()
      setUser(null)
      setProfile(null)
      // No session here — stop prefetching the shell on future loads until
      // there is one again.
      clearReturningUser()
    } finally {
      setChecked(true)
    }
  }

  async function login(email, password) {
    const { data } = await authAPI.login({ email, password })
    // Wipe any cache left by a previous account on this browser before loading
    // the new identity, so plans/profile/etc. never bleed across accounts.
    await resetQueryCache()
    setAuthTokens(data.access_token, data.refresh_token)
    await fetchProfile()
  }

  async function register(name, email, password, consent_given = false) {
    // No session is issued on registration — the user must verify their email and
    // then log in. Returns { message, requires_verification }.
    const { data } = await authAPI.register({ name, email, password, consent_given })
    return data
  }

  async function loginWithGoogle(code, state, redirectUri = `${window.location.origin}/auth/google/callback`) {
    const { data } = await authAPI.google({ code, state, redirect_uri: redirectUri })
    await resetQueryCache()
    setAuthTokens(data.access_token, data.refresh_token)
    await fetchProfile()
  }

  async function loginWithGithub(code, state, redirectUri = `${window.location.origin}/auth/github/callback`) {
    const { data } = await authAPI.github({ code, state, redirect_uri: redirectUri })
    await resetQueryCache()
    setAuthTokens(data.access_token, data.refresh_token)
    await fetchProfile()
  }

  async function loginWithOtp(phone_number, code) {
    const { data } = await authAPI.verifyOtp({ phone_number, code })
    await resetQueryCache()
    setAuthTokens(data.access_token, data.refresh_token)
    await fetchProfile()
  }

  async function updateProfile(updates) {
    const { data } = await profileAPI.updateMe(updates)
    setProfile(data)
    setUser(mapProfileToUser(data))
    return data
  }

  async function logout() {
    try {
      await authAPI.logout()
    } catch {
      // Local cleanup still matters if the server is unreachable.
    }
    clearAuthTokens()
    setUser(null)
    setProfile(null)
    // Unbind identity so a second user on a shared device isn't attributed to
    // the first, mirroring the query-cache reset directly below.
    resetAnalytics()
    clearReturningUser()
    await resetQueryCache()
  }
  return (
    <AuthContext.Provider value={{
      user, profile, loading,
      login, register, loginWithGoogle, loginWithGithub, loginWithOtp, logout, updateProfile, fetchProfile,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
