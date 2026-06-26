import { motion, AnimatePresence } from 'framer-motion'
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
      <Helmet><title>Forgot Password | Ayura AI</title></Helmet>

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
          <span className="auth-left-kicker">Account Recovery</span>
          <h2 className="auth-left-title">
            Let's get you<br /><em>back on track</em>.
          </h2>
          <p className="auth-left-desc">
            Enter the email associated with your account, and we will send you a secure link to reset your password.
          </p>
        </div>
      </div>

      {/* ── RIGHT — form ── */}
      <div className="auth-right">
        <motion.div
          className="auth-form-wrap"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="auth-form-header">
            <h1 className="auth-form-title">Reset Password</h1>
            <p className="auth-form-subtitle">Enter your email and we'll send you a link to reset your password.</p>
          </div>

          <AnimatePresence mode="wait">
            {status === 'success' ? (
              <motion.div
                key="success"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                style={{ textAlign: 'center', padding: '12px 0' }}
              >
                <div style={{ color: '#0D9488', marginBottom: '12px', display: 'flex', justifyContent: 'center' }}><MailCheck size={46} strokeWidth={1.6} /></div>
                <h3 style={{ fontFamily: "'Syne', sans-serif", fontSize: '1.4rem', color: '#0A1F1C', marginBottom: '8px' }}>Check your email</h3>
                <p style={{ color: '#4A7C76', fontSize: '0.9rem', marginBottom: '24px', lineHeight: 1.6 }}>
                  We sent a password reset link to <strong style={{ color: '#0D9488' }}>{email}</strong>
                </p>
                <Link to="/login" className="auth-submit-btn" style={{ textDecoration: 'none' }}>
                  Return to Sign In
                </Link>
              </motion.div>
            ) : (
              <motion.form
                key="form"
                className="auth-form"
                onSubmit={handleSubmit}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
              >
                <AnimatePresence>
                  {status === 'error' && (
                    <motion.div
                      className="auth-error"
                      initial={{ opacity: 0, y: -8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                    >
                      {errorMsg}
                    </motion.div>
                  )}
                </AnimatePresence>

                <div className="auth-input-group">
                  <label className="auth-label" htmlFor="email">Email Address</label>
                  <input
                    id="email"
                    className="auth-input"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    required
                    disabled={status === 'loading'}
                  />
                </div>

                <motion.button
                  type="submit"
                  className="auth-submit-btn"
                  disabled={status === 'loading'}
                  whileTap={{ scale: 0.97 }}
                >
                  {status === 'loading' ? (
                    <span className="spinner" style={{ width: '20px', height: '20px', borderWidth: '2px', borderTopColor: '#fff', borderColor: 'rgba(255,255,255,0.3)' }} />
                  ) : (
                    'Send Reset Link →'
                  )}
                </motion.button>
              </motion.form>
            )}
          </AnimatePresence>

          <div className="auth-bottom-links">
            <p className="auth-bottom-link-text">
              Remember your password? <Link to="/login" className="auth-link">Sign in</Link>
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
