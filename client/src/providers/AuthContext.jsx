/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useEffect } from 'react'
import {
  authAPI,
  profileAPI,
  clearAuthTokens,
  setAuthTokens,
} from '../api/client'
import { resetQueryCache } from '../queryClient'
import { identifyUser, resetAnalytics } from '../lib/analytics'
import { markReturningUser, clearReturningUser } from '../lib/sessionHint'

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

export function AuthProvider({ children }) {
  const [user, setUser]       = useState(null)
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)

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
    fetchProfile()
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
      setLoading(false)
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
