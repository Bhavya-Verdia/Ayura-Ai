import { m, AnimatePresence } from 'framer-motion'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { authAPI } from '../api/client'
import { Helmet } from 'react-helmet-async'
import { MailCheck } from 'lucide-react'
import { tr } from '../lib/tr'
import { Trans } from 'react-i18next'
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
      <Helmet><title>{tr('ui.forgotPassword.forgotPasswordAyuraAi', 'Forgot Password · Ayura AI')}</title></Helmet>

      <div className="auth-center">
        <div className="auth-card">
          <Link to="/" className="auth-brand">
            <img src="/favicon.svg" alt="" className="auth-brand-logo" />
            <span className="auth-brand-name"><Trans i18nKey="ui.forgotPassword.ayura0Ai0" defaults={"Ayura <0>AI</0>"} components={[<span />]} /></span>
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
                <h3 style={{ fontSize: '1.4rem', marginBottom: '8px' }}>{tr('ui.forgotPassword.checkYourEmail', 'Check your email')}</h3>
                <p style={{ color: 'var(--ayura-muted)', fontSize: '0.9rem', marginBottom: '24px', lineHeight: 1.6 }}><Trans i18nKey="ui.forgotPassword.weSentAPasswordReset" defaults={"We sent a password reset link to <0>{{email}}</0>"} values={{ email }} components={[<strong style={{ color: 'var(--ayura-teal)' }} />]} /></p>
                <Link to="/login" className="auth-submit" style={{ textDecoration: 'none', display: 'inline-flex', width: 'auto', padding: '0 28px' }}>
                  {tr('ui.forgotPassword.returnToSignIn', 'Return to Sign In')}
                </Link>
              </m.div>
            ) : (
              <m.div key="form" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <div className="auth-card-header">
                  <h1 className="auth-card-title"><Trans i18nKey="ui.forgotPassword.reset0Password0" defaults={"Reset <0>password</0>"} components={[<em />]} /></h1>
                  <p className="auth-card-sub">{tr('ui.forgotPassword.enterYourEmailAndWe', 'Enter your email and we’ll send you a reset link.')}</p>
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
                    <label className="auth-label" htmlFor="email">{tr('ui.forgotPassword.emailAddress', 'Email address')}</label>
                    <input
                      id="email"
                      className="auth-input"
                      type="email"
                      autoComplete="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder={tr('ui.forgotPassword.youExampleCom', 'you@example.com')}
                      required
                      disabled={status === 'loading'}
                    />
                  </div>

                  <m.button type="submit" className="auth-submit" disabled={status === 'loading'} whileTap={{ scale: 0.97 }}>
                    {status === 'loading' ? <span className="auth-spinner" /> : tr('ui.forgotPassword.sendResetLink', 'Send Reset Link →')}
                  </m.button>
                </form>
              </m.div>
            )}
          </AnimatePresence>

          <div className="auth-links">
            <p className="auth-links-text"><Trans i18nKey="ui.forgotPassword.rememberYourPassword0Sign" defaults={"Remember your password? <0>Sign in →</0>"} components={[<Link to="/login" className="auth-link" />]} /></p>
          </div>
        </div>
      </div>
    </div>
  )
}
