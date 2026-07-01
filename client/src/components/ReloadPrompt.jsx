import { useEffect } from 'react'
import { useRegisterSW } from 'virtual:pwa-register/react'
import { toast } from 'sonner'

export default function ReloadPrompt() {
  const {
    offlineReady: [offlineReady, setOfflineReady],
    needRefresh: [needRefresh],
    updateServiceWorker,
  } = useRegisterSW({
    onRegisterError(error) {
      console.error('SW registration error', error)
    },
  })

  useEffect(() => {
    if (offlineReady) {
      toast.success('App is ready to work offline.')
      setOfflineReady(false)
    }
  }, [offlineReady, setOfflineReady])

  useEffect(() => {
    if (needRefresh) {
      toast.info('A new version is available!', {
        duration: Infinity,
        action: {
          label: 'Reload',
          onClick: () => updateServiceWorker(true),
        },
      })
    }
  }, [needRefresh, updateServiceWorker])

  return null // Renderless component, handles logic only
}
