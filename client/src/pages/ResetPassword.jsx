import { useState } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { m, AnimatePresence } from 'framer-motion'
import { authAPI } from '../api/client'
import { Helmet } from 'react-helmet-async'
import { CircleCheck } from 'lucide-react'
import './Auth.css'

export default function ResetPassword() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  const navigate = useNavigate()

  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [status, setStatus] = useState('idle')
  const [errorMsg, setErrorMsg] = useState('')

  if (!token) {
    return (
      <div className="auth-page" style={{ alignItems: 'center', justifyContent: 'center', background: '#F6FAFA' }}>
        <div style={{ textAlign: 'center' }}>
          <h2 style={{ fontFamily: "'Syne', sans-serif", fontSize: '2rem', color: '#0A1F1C' }}>Invalid Link</h2>
          <p style={{ color: '#4A7C76', margin: '16px 0 24px' }}>This password reset link is invalid or missing.</p>
          <Link to="/forgot-password" className="auth-submit-btn" style={{ textDecoration: 'none', display: 'inline-flex', padding: '0 24px', width: 'auto' }}>
            Request new link
          </Link>
        </div>
      </div>
    )
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (password !== confirmPassword) {
      setErrorMsg('Passwords do not match')
      return
    }
    if (password.length < 8) {
      setErrorMsg('Password must be at least 8 characters')
      return
    }

    setStatus('loading')
    setErrorMsg('')
    try {
      await authAPI.resetPassword(token, password)
      setStatus('success')
      setTimeout(() => navigate('/login'), 3000)
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Failed to reset password. Link may have expired.')
      setStatus('error')
    }
  }

  return (
    <div className="auth-page">
      <Helmet><title>Set New Password | Ayura AI</title></Helmet>

      {/* ── LEFT — brand panel ── */}
      <div className="auth-left">
        <div className="auth-left-orb-a" />
        <div className="auth-left-orb-b" />
        <div className="auth-left-noise" />

        <Link to="/" className="auth-brand-link">
          <img src="/favicon.svg" alt="Ayura AI Logo" className="auth-brand-mark" />
          <span className="auth-brand-text">Ayura AI</span>
        </Link>

        <div className="auth-left-body">
          <span className="auth-left-kicker">Secure your account</span>
          <h2 className="auth-left-title">
            Choose a new<br /><em>password</em>.
          </h2>
          <p className="auth-left-desc">
            Make sure it's at least 8 characters long. A strong password keeps your wellness data secure.
          </p>
        </div>
      </div>

      {/* ── RIGHT — form ── */}
      <div className="auth-right">
        <m.div
          className="auth-form-wrap"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="auth-form-header">
            <h1 className="auth-form-title">Set new password</h1>
            <p className="auth-form-subtitle">Enter your new password below to regain access.</p>
          </div>

          <AnimatePresence mode="wait">
            {status === 'success' ? (
              <m.div
                key="success"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                style={{ textAlign: 'center', padding: '12px 0' }}
              >
                <div style={{ color: '#0D9488', marginBottom: '12px', display: 'flex', justifyContent: 'center' }}><CircleCheck size={46} strokeWidth={1.6} /></div>
                <h3 style={{ fontFamily: "'Syne', sans-serif", fontSize: '1.4rem', color: '#0A1F1C', marginBottom: '8px' }}>Password updated</h3>
                <p style={{ color: '#4A7C76', fontSize: '0.9rem', marginBottom: '24px', lineHeight: 1.6 }}>
                  Your password has been changed successfully. Redirecting to login...
                </p>
                <Link to="/login" className="auth-submit-btn" style={{ textDecoration: 'none' }}>
                  Go to Sign In
                </Link>
              </m.div>
            ) : (
              <m.form
                key="form"
                className="auth-form"
                onSubmit={handleSubmit}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
              >
                <AnimatePresence>
                  {status === 'error' && (
                    <m.div
                      className="auth-error"
                      initial={{ opacity: 0, y: -8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                    >
                      {errorMsg}
                    </m.div>
                  )}
                </AnimatePresence>

                <div className="auth-input-group">
                  <label className="auth-label" htmlFor="password">New Password</label>
                  <input
                    id="password"
                    className="auth-input"
                    type="password"
                    autoComplete="new-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="At least 8 characters"
                    required
                    disabled={status === 'loading'}
                  />
                </div>
                
                <div className="auth-input-group">
                  <label className="auth-label" htmlFor="confirmPassword">Confirm Password</label>
                  <input
                    id="confirmPassword"
                    className="auth-input"
                    type="password"
                    autoComplete="new-password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Type your new password again"
                    required
                    disabled={status === 'loading'}
                  />
                </div>

                <m.button
                  type="submit"
                  className="auth-submit-btn"
                  disabled={status === 'loading'}
                  whileTap={{ scale: 0.97 }}
                >
                  {status === 'loading' ? (
                    <span className="spinner" style={{ width: '20px', height: '20px', borderWidth: '2px', borderTopColor: '#fff', borderColor: 'rgba(255,255,255,0.3)' }} />
                  ) : (
                    'Reset Password →'
                  )}
                </m.button>
              </m.form>
            )}
          </AnimatePresence>

        </m.div>
      </div>
    </div>
  )
}
