import { useEffect, useCallback } from 'react'

/**
 * Registers global keyboard shortcuts.
 * - Escape: blur active element / close overlays
 * - Cmd+K / Ctrl+K: open the CommandPalette
 */
export function useKeyboardShortcuts() {
  const handleKeyDown = useCallback((e) => {
    // Escape — blur active element
    if (e.key === 'Escape') {
      const active = document.activeElement
      if (active && active !== document.body) active.blur()
    }

    // Cmd+K / Ctrl+K — open CommandPalette
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault()
      window.dispatchEvent(new CustomEvent('ayura:cmdK'))
    }
  }, [])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])
}
