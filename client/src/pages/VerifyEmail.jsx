import { m } from 'framer-motion'
import { useEffect, useState, useRef, Suspense } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { authAPI } from '../api/client'
import { Helmet } from 'react-helmet-async'
import { CircleCheck, CircleX } from 'lucide-react'
import React from 'react'
import { tr } from '../lib/tr'
import { Trans } from 'react-i18next'
import './Auth.css'

const LazyParticleField = React.lazy(() => import('../components/ParticleField'))

export default function VerifyEmail() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  const [status, setStatus] = useState(token ? 'loading' : 'error')
  const [errorMsg, setErrorMsg] = useState(token ? '' : 'No verification token found in URL.')
  const hasAttempted = useRef(false)

  useEffect(() => {
    if (!token) return
    if (hasAttempted.current) return
    hasAttempted.current = true

    const verify = async () => {
      try {
        await authAPI.verifyEmail(token)
        setStatus('success')
      } catch (err) {
        setStatus('error')
        setErrorMsg(err.response?.data?.detail || 'Verification failed. The link may have expired.')
      }
    }
    verify()
  }, [token])

  return (
    <>
      <Helmet><title>{tr('ui.verifyEmail.verifyEmailAyuraAi', 'Verify Email | Ayura AI')}</title></Helmet>
    <div className="auth-page">
      <Suspense fallback={null}>
        <LazyParticleField count={60} spread={20} style={{ opacity: 0.4 }} />
      </Suspense>

      <m.div
        className="auth-center"
        initial={{ opacity: 0, y: 24, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
      >
        <div className="auth-card" style={{ textAlign: 'center' }}>
          <Link to="/" className="auth-brand">
            <img src="/favicon.svg" alt="" className="auth-brand-logo" />
            <span className="auth-brand-name"><Trans i18nKey="ui.verifyEmail.ayura0Ai0" defaults={"Ayura <0>AI</0>"} components={[<span />]} /></span>
          </Link>

          {status === 'loading' && (
            <m.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <div className="spinner" style={{ margin: '0 auto 20px', width: '40px', height: '40px' }} />
              <h1 style={{ fontSize: 'var(--fs-h3)' }}>{tr('ui.verifyEmail.verifyingYourEmail', 'Verifying your email...')}</h1>
              <p style={{ color: 'var(--auth-muted)', fontSize: '0.9rem' }}>{tr('ui.verifyEmail.pleaseWaitAMoment', 'Please wait a moment.')}</p>
            </m.div>
          )}

          {status === 'success' && (
            <m.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            >
              <div style={{ color: 'var(--ayura-sage, #4ade80)', marginBottom: '12px', display: 'flex', justifyContent: 'center' }}><CircleCheck size={52} strokeWidth={1.6} /></div>
              <h1 style={{ fontSize: 'var(--fs-h3)', marginBottom: '8px' }}>{tr('ui.verifyEmail.emailVerified', 'Email Verified!')}</h1>
              <p style={{ color: 'var(--auth-muted)', fontSize: '0.9rem', marginBottom: '24px' }}>
                {tr('ui.verifyEmail.yourAccountIsFullyActivated', 'Your account is fully activated.')}
              </p>
              <Link to="/dashboard" className="btn btn-primary btn-full btn-lg">
                {tr('ui.verifyEmail.goToDashboard', 'Go to Dashboard')}
              </Link>
            </m.div>
          )}

          {status === 'error' && (
            <m.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5 }}
            >
              <div style={{ color: 'var(--ayura-rose)', marginBottom: '12px', display: 'flex', justifyContent: 'center' }}><CircleX size={52} strokeWidth={1.6} /></div>
              <h1 style={{ fontSize: 'var(--fs-h3)', marginBottom: '8px', color: 'var(--ayura-rose)' }}>{tr('ui.verifyEmail.verificationFailed', 'Verification Failed')}</h1>
              <p style={{ color: 'var(--ayura-rose)', marginBottom: '24px', fontSize: '0.9rem' }}>{errorMsg}</p>
              <Link to="/login" className="btn btn-secondary btn-full btn-lg">
                {tr('ui.verifyEmail.backToLogin', 'Back to Login')}
              </Link>
            </m.div>
          )}
        </div>
      </m.div>
    </div>
    </>
  )
}

