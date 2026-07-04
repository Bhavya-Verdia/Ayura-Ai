/* eslint-disable react-refresh/only-export-components */
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { flushSync } from 'react-dom'

const ThemeContext = createContext()
export const useTheme = () => useContext(ThemeContext)

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(localStorage.getItem('ayura_theme') || 'dark')

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('ayura_theme', theme)
  }, [theme])

  // Theme switch as a circular reveal sweeping out from the click point.
  // Progressive enhancement: browsers without the View Transitions API (or
  // users with reduced motion) get the plain instant switch. The transition is
  // browser-composited (one snapshot + clip-path), so it's cheap even on phones.
  const setThemeAnimated = useCallback((next, ev) => {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (!document.startViewTransition || reduced || next === theme) {
      setTheme(next)
      return
    }
    const x = ev?.clientX ?? window.innerWidth / 2
    const y = ev?.clientY ?? 64
    const r = Math.hypot(Math.max(x, window.innerWidth - x), Math.max(y, window.innerHeight - y))
    const vt = document.startViewTransition(() => {
      // The API snapshots the DOM synchronously around this callback.
      flushSync(() => setTheme(next))
    })
    vt.ready.then(() => {
      document.documentElement.animate(
        { clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${r}px at ${x}px ${y}px)`] },
        { duration: 550, easing: 'cubic-bezier(0.22, 1, 0.36, 1)', pseudoElement: '::view-transition-new(root)' },
      )
    }).catch(() => {})
  }, [theme])

  // Global mouse tracking for glows
  useEffect(() => {
    const handleMouseMove = (e) => {
      document.documentElement.style.setProperty('--mouse-x', `${e.clientX}px`)
      document.documentElement.style.setProperty('--mouse-y', `${e.clientY}px`)
    }
    window.addEventListener('mousemove', handleMouseMove, { passive: true })
    return () => window.removeEventListener('mousemove', handleMouseMove)
  }, [])

  return (
    <ThemeContext.Provider value={{ theme, setTheme, setThemeAnimated }}>
      {children}
    </ThemeContext.Provider>
  )
}
