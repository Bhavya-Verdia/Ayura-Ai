/* eslint-disable react-refresh/only-export-components */
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'

const ThemeContext = createContext()
export const useTheme = () => useContext(ThemeContext)

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(localStorage.getItem('ayura_theme') || 'dark')

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('ayura_theme', theme)
  }, [theme])

  // Instant theme switch — no animation. (A View-Transitions circular reveal,
  // then a custom clip-path disc reveal, were both tried and removed: they read
  // as slow / "stuck for a moment" because of the whole-page snapshot + re-render
  // they hid behind the sweep. Theme should flip immediately, like a language
  // toggle.) We set the data-theme attribute synchronously so the recolour lands
  // this frame regardless of React's re-render timing; setTheme keeps the React
  // state (toggle icon, persistence) in sync via the effect above.
  const setThemeAnimated = useCallback((next) => {
    if (next === theme) return
    if (typeof document !== 'undefined') {
      document.documentElement.setAttribute('data-theme', next)
    }
    setTheme(next)
  }, [theme])

  return (
    <ThemeContext.Provider value={{ theme, setTheme, setThemeAnimated }}>
      {children}
    </ThemeContext.Provider>
  )
}
