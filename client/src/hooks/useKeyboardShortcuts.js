import { useEffect, useCallback } from 'react'

/**
 * Registers global keyboard shortcuts.
 * - Escape: closes modals/overlays by blurring active element
 * - Ctrl+K / Cmd+K: focuses the first visible search/text input
 */
export function useKeyboardShortcuts() {
  const handleKeyDown = useCallback((e) => {
    // Escape — blur active element / close overlays
    if (e.key === 'Escape') {
      const active = document.activeElement
      if (active && active !== document.body) {
        active.blur()
      }
    }

    // Ctrl+K or Cmd+K — focus search/chat input
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault()
      // Try chat input first, then any visible text input
      const chatInput = document.querySelector('.chat-text-input')
      const searchInput = document.querySelector('input[type="text"]:not([type="hidden"])')
      const target = chatInput || searchInput
      if (target) {
        target.focus()
        target.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }
    }
  }, [])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])
}
