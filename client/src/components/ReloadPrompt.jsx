import { useEffect, useContext } from 'react'
import { useRegisterSW } from 'virtual:pwa-register/react'
import { ToastContext } from '../providers/ToastContext'

export default function ReloadPrompt() {
  const {
    offlineReady: [offlineReady, setOfflineReady],
    needRefresh: [needRefresh],
    updateServiceWorker,
  } = useRegisterSW({
    onRegistered() {
      console.log('SW Registered')
    },
    onRegisterError(error) {
      console.log('SW registration error', error)
    },
  })

  const toast = useContext(ToastContext)

  useEffect(() => {
    if (offlineReady) {
      toast.success('App is ready to work offline.')
      setOfflineReady(false)
    }
  }, [offlineReady, toast, setOfflineReady])

  useEffect(() => {
    if (needRefresh) {
      toast.info(
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <span>A new version is available!</span>
          <button 
            onClick={() => updateServiceWorker(true)}
            style={{
              padding: '6px 12px',
              background: 'var(--primary-500)',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.85rem'
            }}
          >
            Reload to Update
          </button>
        </div>,
        { duration: 0 } // Don't auto-dismiss
      )
      
      // Cleanup happens manually via the button triggering a full page reload
    }
  }, [needRefresh, toast, updateServiceWorker])

  return null // Renderless component, handles logic only
}
