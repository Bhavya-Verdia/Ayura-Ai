import { motion, AnimatePresence } from 'framer-motion'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../providers/AuthContext'
import { Helmet } from 'react-helmet-async'
import { Eye, EyeOff } from 'lucide-react'
import './Auth.css'

const GOOGLE_ENABLED  = Boolean(import.meta.env.VITE_GOOGLE_CLIENT_ID)
const GITHUB_ENABLED  = Boolean(import.meta.env.VITE_GITHUB_CLIENT_ID)

async function googleUrl() {
  const { data } = await import('../api/client').then(m => m.authAPI.getGoogleUrl())
  return data.url
}
async function githubUrl() {
  // Hit the server so it sets the httponly `oauth_state` cookie that
  // POST /auth/github validates against (mirrors googleUrl()). Building the
  // URL client-side left the cookie unset → every callback 400'd on CSRF.
  const { data } = await import('../api/client').then(m => m.authAPI.getGithubUrl())
  return data.url
}

export default function Register() {
  const [name,         setName]         = useState('')
  const [email,        setEmail]        = useState('')
  const [password,     setPassword]     = useState('')
  const [showPw,       setShowPw]       = useState(false)
  const [consentGiven, setConsentGiven] = useState(false)
  const [error,        setError]        = useState('')
  const [loading,      setLoading]      = useState(false)
  const [submitted,    setSubmitted]    = useState(false)
  const { register } = useAuth()

  async function handleSubmit(e) {
    e.preventDefault(); setError(''); setLoading(true)
    try { await register(name, email, password, consentGiven); setSubmitted(true) }
    catch (err) {
      let msg = err.response?.data?.detail
      if (Array.isArray(msg)) msg = msg.map(m => m.msg).join(', ')
      setError(msg || 'Failed to create account. Please try again.')
    }
    finally { setLoading(false) }
  }

  return (
    <div className="auth-page">
      <Helmet><title>Create Account · Ayura AI</title></Helmet>

      <div className="auth-center">
        <div className="auth-card">
          {/* ॐ watermark */}
          <span className="auth-card-om" aria-hidden="true">ॐ</span>

          {/* Brand */}
          <Link to="/" className="auth-brand">
            <img src="/favicon.svg" alt="Ayura AI" className="auth-brand-logo" />
            <span className="auth-brand-name">Ayura <span>AI</span></span>
          </Link>

          {submitted ? (
            <>
              <div className="auth-card-header" style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '2.8rem', marginBottom: '12px' }}>ॐ</div>
                <h1 className="auth-card-title">Check your inbox</h1>
                <p className="auth-card-sub">
                  We sent a verification link to <strong style={{ color: 'var(--ayura-teal)' }}>{email}</strong>.
                  Click it to activate your account, then sign in.
                </p>
              </div>
              <div className="auth-links" style={{ marginTop: '8px' }}>
                <p className="auth-links-text">
                  Already verified? <Link to="/login" className="auth-link">Sign in →</Link>
                </p>
              </div>
            </>
          ) : (
            <>
              {/* Title */}
              <div className="auth-card-header">
                <h1 className="auth-card-title">Begin your <em>journey</em></h1>
                <p className="auth-card-sub">Create your free Ayura AI account.</p>
              </div>

              {/* Social OAuth */}
              {(GOOGLE_ENABLED || GITHUB_ENABLED) && (
                <div className="auth-social-row">
                  {GOOGLE_ENABLED && (
                    <button className="auth-social-btn"
                      onClick={async e => { e.preventDefault(); try { window.location.href = await googleUrl() } catch { setError('Google sign-up failed.') } }}
                      aria-label="Sign up with Google">
                      <svg width="17" height="17" viewBox="0 0 24 24">
                        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                      </svg>
                      Google
                    </button>
                  )}
                  {GITHUB_ENABLED && (
                    <button className="auth-social-btn"
                      onClick={async e => { e.preventDefault(); try { window.location.href = await githubUrl() } catch { setError('GitHub sign-up failed.') } }}
                      aria-label="Sign up with GitHub">
                      <svg width="17" height="17" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.44 9.8 8.21 11.39.6.11.79-.26.79-.58v-2.23c-3.34.73-4.03-1.42-4.03-1.42-.55-1.39-1.33-1.76-1.33-1.76-1.09-.74.08-.73.08-.73 1.2.08 1.84 1.24 1.84 1.24 1.07 1.83 2.81 1.30 3.49 1.00.11-.78.42-1.31.76-1.61-2.67-.30-5.47-1.33-5.47-5.93 0-1.31.47-2.38 1.24-3.22-.12-.30-.54-1.52.12-3.18 0 0 1.01-.32 3.30 1.23a11.5 11.5 0 0 1 3.00-.40c1.02.005 2.05.14 3.00.40 2.29-1.55 3.30-1.23 3.30-1.23.66 1.66.24 2.88.12 3.18.77.84 1.24 1.91 1.24 3.22 0 4.61-2.81 5.63-5.48 5.92.43.37.82 1.10.82 2.22v3.29c0 .32.19.69.80.58C20.57 21.8 24 17.3 24 12c0-6.63-5.37-12-12-12z"/>
                      </svg>
                      GitHub
                    </button>
                  )}
                </div>
              )}
              {(GOOGLE_ENABLED || GITHUB_ENABLED) && (
                <div className="auth-or">or sign up with email</div>
              )}

              {/* Error */}
              <AnimatePresence mode="wait">
                {error && (
                  <motion.div className="auth-error" key="err"
                    initial={{ opacity:0, y:-6 }} animate={{ opacity:1, y:0 }}
                    exit={{ opacity:0 }} transition={{ duration:0.20 }}>
                    {error}
                  </motion.div>
                )}
              </AnimatePresence>

              <div id="recaptcha-container" />

              {/* Form */}
              <form className="auth-form" onSubmit={handleSubmit}>
                <div className="auth-field">
                  <label className="auth-label" htmlFor="name">Full name</label>
                  <input id="name" className="auth-input" type="text"
                    value={name} onChange={e => setName(e.target.value)}
                    placeholder="Jane Doe" required />
                </div>

                <div className="auth-field">
                  <label className="auth-label" htmlFor="reg-email">Email address</label>
                  <input id="reg-email" className="auth-input" type="email"
                    value={email} onChange={e => setEmail(e.target.value)}
                    placeholder="you@example.com" required />
                </div>

                <div className="auth-field">
                  <label className="auth-label" htmlFor="reg-password">Password</label>
                  <div className="auth-pw-row">
                    <input id="reg-password" className="auth-input"
                      type={showPw ? 'text' : 'password'}
                      value={password} onChange={e => setPassword(e.target.value)}
                      placeholder="At least 8 characters" required />
                    <button type="button" className="auth-pw-eye"
                      onClick={() => setShowPw(v => !v)} tabIndex={-1}>
                      {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
                    </button>
                  </div>
                </div>

                <label className="auth-consent">
                  <input type="checkbox" checked={consentGiven}
                    onChange={e => setConsentGiven(e.target.checked)} required />
                  <span>
                    I agree to the{' '}
                    <Link to="/terms" className="auth-link" target="_blank" rel="noopener noreferrer">Terms</Link>
                    {' '}&amp;{' '}
                    <Link to="/privacy" className="auth-link" target="_blank" rel="noopener noreferrer">Privacy Policy</Link>
                    {' '}and consent to processing of my health data.
                  </span>
                </label>

                <motion.button type="submit" className="auth-submit"
                  disabled={loading || !consentGiven} whileTap={{ scale: 0.97 }}>
                  {loading ? <span className="auth-spinner" /> : 'Create Account →'}
                </motion.button>
              </form>

              <div className="auth-links">
                <p className="auth-disclaimer">
                  Ayura AI provides wellness guidance, not medical care.
                </p>
                <p className="auth-links-text">
                  Already have an account? <Link to="/login" className="auth-link">Sign in →</Link>
                </p>
              </div>
            </>
          )}
        </div>

        {/* Footer ॐ */}
        <span className="auth-foot-om" aria-hidden="true">ॐ</span>
      </div>
    </div>
  )
}
