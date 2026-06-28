import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../providers/AuthContext'

export default function GoogleCallback() {
  const navigate = useNavigate()
  const { loginWithGoogle } = useAuth()
  // The OAuth code + state cookie are single-use. loginWithGoogle isn't memoized,
  // so a successful exchange updates auth state → AuthContext re-renders → this
  // effect re-fires with the same (now-consumed) code; the 2nd call 400s on CSRF
  // and its .catch wins the navigation, bouncing a logged-in user to
  // /login?error=google_failed. Guard so we exchange exactly once.
  const exchangedRef = useRef(false)

  useEffect(() => {
    if (exchangedRef.current) return
    exchangedRef.current = true

    const params = new URLSearchParams(window.location.search)
    const code = params.get('code')
    const state = params.get('state')
    if (!code || !state) {
      console.error("Missing code or state parameter");
      navigate('/login?error=invalid_callback');
      return;
    }

    const redirectUri = import.meta.env.VITE_GOOGLE_REDIRECT_URI || `${window.location.origin}/auth/google/callback`

    loginWithGoogle(code, state, redirectUri)
      .then(() => navigate('/dashboard'))
      .catch(() => navigate('/login?error=google_failed'))
  }, [loginWithGoogle, navigate])

  return (
    <div style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', minHeight:'100vh', gap:'16px' }}>
      <div className="spinner" />
      <p style={{ color:'var(--text-secondary)' }}>Signing you in with Google…</p>
    </div>
  )
}
