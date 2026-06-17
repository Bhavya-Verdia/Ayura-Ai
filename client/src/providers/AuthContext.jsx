/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useEffect } from 'react'
import {
  authAPI,
  profileAPI,
  clearAuthTokens,
  setAuthTokens,
} from '../api/client'

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
    } catch {
      clearAuthTokens()
      setUser(null)
      setProfile(null)
    } finally {
      setLoading(false)
    }
  }

  async function login(email, password) {
    const { data } = await authAPI.login({ email, password })
    setAuthTokens(data.access_token, data.refresh_token)
    await fetchProfile()
  }

  async function register(name, email, password, consent_given = false) {
    const { data } = await authAPI.register({ name, email, password, consent_given })
    setAuthTokens(data.access_token, data.refresh_token)
    await fetchProfile()
  }

  async function loginWithGoogle(code, state, redirectUri = `${window.location.origin}/auth/google/callback`) {
    const { data } = await authAPI.google({ code, state, redirect_uri: redirectUri })
    setAuthTokens(data.access_token, data.refresh_token)
    await fetchProfile()
  }

  async function loginWithGithub(code, redirectUri = `${window.location.origin}/auth/github/callback`) {
    const { data } = await authAPI.github({ code, redirect_uri: redirectUri })
    setAuthTokens(data.access_token, data.refresh_token)
    await fetchProfile()
  }

  async function loginWithOtp(phone_number, code) {
    const { data } = await authAPI.verifyOtp({ phone_number, code })
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
