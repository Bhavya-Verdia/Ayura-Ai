import { useEffect } from 'react'

/**
 * CursorGlow — A soft radial light that follows the cursor.
 * Uses CSS custom properties (--cx, --cy) set on the body.
 * The actual visual is a ::before pseudo-element injected globally.
 */
export default function CursorGlow() {
  useEffect(() => {
    const onMove = (e) => {
      document.body.style.setProperty('--cx', `${e.clientX}px`)
      document.body.style.setProperty('--cy', `${e.clientY}px`)
    }

    window.addEventListener('mousemove', onMove, { passive: true })
    return () => window.removeEventListener('mousemove', onMove)
  }, [])

  return (
    <style>{`
      body {
        --cx: 50vw;
        --cy: 50vh;
      }
      body::after {
        content: '';
        position: fixed;
        pointer-events: none;
        z-index: 9999;
        top: 0; left: 0;
        width: 100vw; height: 100vh;
        background: radial-gradient(
          400px circle at var(--cx) var(--cy),
          rgba(45,212,191,0.05) 0%,
          transparent 70%
        );
        transition: background 0.1s ease;
      }
      [data-theme='light'] body::after {
        background: radial-gradient(
          400px circle at var(--cx) var(--cy),
          rgba(13,148,136,0.06) 0%,
          transparent 70%
        );
      }
      @media (prefers-reduced-motion: reduce) {
        body::after { display: none; }
      }
    `}</style>
  )
}
