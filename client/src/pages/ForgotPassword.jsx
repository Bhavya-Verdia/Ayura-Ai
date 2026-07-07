import { m, AnimatePresence } from 'framer-motion'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { authAPI } from '../api/client'
import { Helmet } from 'react-helmet-async'
import { MailCheck } from 'lucide-react'
import './Auth.css'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState('idle')
  const [errorMsg, setErrorMsg] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setStatus('loading')
    setErrorMsg('')
    try {
      await authAPI.forgotPassword(email)
      setStatus('success')
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Something went wrong.')
      setStatus('error')
    }
  }

  return (
    <div className="auth-page">
      <Helmet><title>Forgot Password · Ayura AI</title></Helmet>

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
                  <MailCheck size={46} strokeWidth={1.6} />
                </div>
                <h3 style={{ fontSize: '1.4rem', marginBottom: '8px' }}>Check your email</h3>
                <p style={{ color: 'var(--ayura-muted)', fontSize: '0.9rem', marginBottom: '24px', lineHeight: 1.6 }}>
                  We sent a password reset link to <strong style={{ color: 'var(--ayura-teal)' }}>{email}</strong>
                </p>
                <Link to="/login" className="auth-submit" style={{ textDecoration: 'none', display: 'inline-flex', width: 'auto', padding: '0 28px' }}>
                  Return to Sign In
                </Link>
              </m.div>
            ) : (
              <m.div key="form" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <div className="auth-card-header">
                  <h1 className="auth-card-title">Reset <em>password</em></h1>
                  <p className="auth-card-sub">Enter your email and we&rsquo;ll send you a reset link.</p>
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
                    <label className="auth-label" htmlFor="email">Email address</label>
                    <input
                      id="email"
                      className="auth-input"
                      type="email"
                      autoComplete="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@example.com"
                      required
                      disabled={status === 'loading'}
                    />
                  </div>

                  <m.button type="submit" className="auth-submit" disabled={status === 'loading'} whileTap={{ scale: 0.97 }}>
                    {status === 'loading' ? <span className="auth-spinner" /> : 'Send Reset Link →'}
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
