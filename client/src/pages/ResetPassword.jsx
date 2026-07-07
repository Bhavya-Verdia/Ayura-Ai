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
      <div className="auth-page">
        <Helmet><title>Set New Password · Ayura AI</title></Helmet>
        <div className="auth-center">
          <div className="auth-card" style={{ textAlign: 'center' }}>
            <span className="auth-card-om" aria-hidden="true">ॐ</span>
            <Link to="/" className="auth-brand">
              <img src="/favicon.svg" alt="Ayura AI" className="auth-brand-logo" />
              <span className="auth-brand-name">Ayura <span>AI</span></span>
            </Link>
            <div className="auth-card-header">
              <h1 className="auth-card-title">Invalid <em>link</em></h1>
              <p className="auth-card-sub">This password reset link is invalid or missing.</p>
            </div>
            <Link to="/forgot-password" className="auth-submit" style={{ textDecoration: 'none', display: 'inline-flex', width: 'auto', padding: '0 28px' }}>
              Request new link
            </Link>
          </div>
        </div>
      </div>
    )
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (password !== confirmPassword) {
      setErrorMsg('Passwords do not match')
      setStatus('error')
      return
    }
    if (password.length < 8) {
      setErrorMsg('Password must be at least 8 characters')
      setStatus('error')
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
      <Helmet><title>Set New Password · Ayura AI</title></Helmet>

      <div className="auth-center">
        <div className="auth-card">
          <span className="auth-card-om" aria-hidden="true">ॐ</span>

          <Link to="/" className="auth-brand">
            <img src="/favicon.svg" alt="Ayura AI" className="auth-brand-logo" />
            <span className="auth-brand-name">Ayura <span>AI</span></span>
          </Link>

          <AnimatePresence mode="wait">
            {status === 'success' ? (
              <m.div
                key="success"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                style={{ textAlign: 'center', padding: '12px 0' }}
              >
                <div style={{ color: 'var(--ayura-emerald)', marginBottom: '12px', display: 'flex', justifyContent: 'center' }}>
                  <CircleCheck size={46} strokeWidth={1.6} />
                </div>
                <h3 style={{ fontSize: '1.4rem', marginBottom: '8px' }}>Password updated</h3>
                <p style={{ color: 'var(--ayura-muted)', fontSize: '0.9rem', marginBottom: '24px', lineHeight: 1.6 }}>
                  Your password has been changed successfully. Redirecting to login&hellip;
                </p>
                <Link to="/login" className="auth-submit" style={{ textDecoration: 'none', display: 'inline-flex', width: 'auto', padding: '0 28px' }}>
                  Go to Sign In
                </Link>
              </m.div>
            ) : (
              <m.div key="form" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <div className="auth-card-header">
                  <h1 className="auth-card-title">Set new <em>password</em></h1>
                  <p className="auth-card-sub">Make it at least 8 characters to keep your wellness data secure.</p>
                </div>

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

                <form className="auth-form" onSubmit={handleSubmit}>
                  <div className="auth-field">
                    <label className="auth-label" htmlFor="password">New password</label>
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

                  <div className="auth-field">
                    <label className="auth-label" htmlFor="confirmPassword">Confirm password</label>
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

                  <m.button type="submit" className="auth-submit" disabled={status === 'loading'} whileTap={{ scale: 0.97 }}>
                    {status === 'loading' ? <span className="auth-spinner" /> : 'Reset Password →'}
                  </m.button>
                </form>
              </m.div>
            )}
          </AnimatePresence>

          <div className="auth-links">
            <p className="auth-links-text">
              Remember your password? <Link to="/login" className="auth-link">Sign in →</Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
