import { motion } from 'framer-motion'
import { useEffect, useState, useRef, Suspense } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { authAPI } from '../api/client'
import { Helmet } from 'react-helmet-async'
import { CircleCheck, CircleX } from 'lucide-react'
import React from 'react'
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
      <Helmet><title>Verify Email | Ayura AI</title></Helmet>
    <div className="auth-page">
      <Suspense fallback={null}>
        <LazyParticleField count={60} spread={20} style={{ opacity: 0.4 }} />
      </Suspense>

      <div className="auth-orb auth-orb-a" />
      <div className="auth-orb auth-orb-b" />

      <motion.div
        className="auth-shell"
        initial={{ opacity: 0, y: 24, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
      >
        <div className="auth-brand-block">
          <Link to="/" className="auth-brand">
            <img src="/favicon.svg" alt="Ayura AI Logo" className="auth-brand-mark" />
            <span className="auth-brand-text">Ayura AI</span>
          </Link>
        </div>

        <div className="auth-card" style={{ textAlign: 'center', padding: '32px 26px' }}>
          {status === 'loading' && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <div className="spinner" style={{ margin: '0 auto 20px', width: '40px', height: '40px' }} />
              <h3 style={{ fontFamily: "'Syne', sans-serif" }}>Verifying your email...</h3>
              <p style={{ color: 'var(--auth-muted)', fontSize: '0.9rem' }}>Please wait a moment.</p>
            </motion.div>
          )}

          {status === 'success' && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            >
              <div style={{ color: 'var(--ayura-sage, #4ade80)', marginBottom: '12px', display: 'flex', justifyContent: 'center' }}><CircleCheck size={52} strokeWidth={1.6} /></div>
              <h3 style={{ fontFamily: "'Syne', sans-serif", marginBottom: '8px' }}>Email Verified!</h3>
              <p style={{ color: 'var(--auth-muted)', fontSize: '0.9rem', marginBottom: '24px' }}>
                Your account is fully activated.
              </p>
              <Link to="/dashboard" className="btn btn-primary btn-full btn-lg">
                Go to Dashboard
              </Link>
            </motion.div>
          )}

          {status === 'error' && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5 }}
            >
              <div style={{ color: '#fb7185', marginBottom: '12px', display: 'flex', justifyContent: 'center' }}><CircleX size={52} strokeWidth={1.6} /></div>
              <h3 style={{ fontFamily: "'Syne', sans-serif", marginBottom: '8px', color: '#fb7185' }}>Verification Failed</h3>
              <p style={{ color: '#fb7185', marginBottom: '24px', fontSize: '0.9rem' }}>{errorMsg}</p>
              <Link to="/login" className="btn btn-secondary btn-full btn-lg">
                Back to Login
              </Link>
            </motion.div>
          )}
        </div>
      </motion.div>
    </div>
    </>
  )
}
