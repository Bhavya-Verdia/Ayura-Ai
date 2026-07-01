import { useState, useEffect } from 'react'
import { m, AnimatePresence } from 'framer-motion'
import { WifiOff } from 'lucide-react'
import './OfflineBanner.css'

export default function OfflineBanner() {
  const [isOffline, setIsOffline] = useState(!navigator.onLine)

  useEffect(() => {
    const goOffline = () => setIsOffline(true)
    const goOnline  = () => setIsOffline(false)
    window.addEventListener('offline', goOffline)
    window.addEventListener('online',  goOnline)
    return () => {
      window.removeEventListener('offline', goOffline)
      window.removeEventListener('online',  goOnline)
    }
  }, [])

  return (
    <AnimatePresence>
      {isOffline && (
        <m.div
          className="offline-banner"
          role="alert"
          aria-live="assertive"
          initial={{ y: -48, opacity: 0 }}
          animate={{ y: 0,   opacity: 1 }}
          exit={{    y: -48, opacity: 0 }}
          transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
        >
          <WifiOff size={15} strokeWidth={2.2} />
          <span>You&rsquo;re offline — some features may be unavailable.</span>
        </m.div>
      )}
    </AnimatePresence>
  )
}
