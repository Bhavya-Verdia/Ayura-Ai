import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { Suspense } from 'react'
import { Helmet } from 'react-helmet-async'
import React from 'react'
import '../pages/Auth.css'

const LazyParticleField = React.lazy(() => import('../components/ParticleField'))

export default function NotFound() {
  return (
    <>
      <Helmet><title>Page Not Found | Ayura AI</title></Helmet>
    <div className="auth-page" style={{ flexDirection: 'column', gap: '20px', textAlign: 'center' }}>
      <Suspense fallback={null}>
        <LazyParticleField count={50} spread={20} style={{ opacity: 0.35 }} />
      </Suspense>

      <div className="auth-orb auth-orb-a" />
      <div className="auth-orb auth-orb-b" />

      <motion.div
        style={{ position: 'relative', zIndex: 2 }}
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
      >
        <motion.div
          style={{ fontSize: '6rem', marginBottom: '8px', lineHeight: 1 }}
          animate={{ y: [0, -8, 0] }}
          transition={{ duration: 3, ease: 'easeInOut', repeat: Infinity }}
        >
          🌀
        </motion.div>
        <h1 style={{ fontFamily: "'Syne', sans-serif", fontSize: 'clamp(3rem, 8vw, 5rem)', margin: '0 0 8px', background: 'linear-gradient(135deg, #8ef8dc, #64e2ff)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
          404
        </h1>
        <p style={{ fontSize: '1.1rem', color: '#9eb2d2', maxWidth: '400px', margin: '0 auto 24px' }}>
          This page has wandered off the path. Let's guide you back to balance.
        </p>
        <div style={{ display: 'flex', gap: '10px', justifyContent: 'center', flexWrap: 'wrap' }}>
          <Link to="/" className="btn btn-primary" style={{ borderRadius: '12px', fontWeight: 700 }}>
            ← Return Home
          </Link>
          <Link to="/dashboard" className="btn btn-secondary" style={{ borderRadius: '12px', fontWeight: 700, borderColor: 'rgba(149,197,255,.4)', color: '#d9ebff', background: 'rgba(11,28,48,.78)' }}>
            Dashboard
          </Link>
        </div>
      </motion.div>
    </div>
    </>
  )
}
