import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ToastContext } from '../providers/ToastContext'

let toastId = 0

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const addToast = useCallback((message, type = 'info', duration = 4000) => {
    const id = ++toastId
    setToasts(prev => [...prev, { id, message, type }])
    if (duration > 0) {
      setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== id))
      }, duration)
    }
    return id
  }, [])

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  // Reassign as a callable with methods
  const toastFn = useCallback((msg, type, dur) => addToast(msg, type, dur), [addToast])
  toastFn.success = (msg, dur) => addToast(msg, 'success', dur)
  toastFn.error = (msg, dur) => addToast(msg, 'error', dur)
  toastFn.info = (msg, dur) => addToast(msg, 'info', dur)
  toastFn.warning = (msg, dur) => addToast(msg, 'warning', dur)

  const icons = { success: '✅', error: '❌', warning: '⚠️', info: '💡' }

  return (
    <ToastContext.Provider value={toastFn}>
      {children}
      <div className="toast-container" aria-live="polite">
        <AnimatePresence>
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              className={`toast toast-${t.type}`}
              initial={{ opacity: 0, x: 80, scale: 0.9 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 80, scale: 0.9 }}
              transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
              layout
            >
              <span className="toast-icon">{icons[t.type] || icons.info}</span>
              <span className="toast-msg">{t.message}</span>
              <button className="toast-close" onClick={() => removeToast(t.id)} aria-label="Dismiss">
                ✕
              </button>
              <motion.div
                className="toast-progress"
                initial={{ scaleX: 1 }}
                animate={{ scaleX: 0 }}
                transition={{ duration: 4, ease: 'linear' }}
              />
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  )
}
