import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import {
  LayoutDashboard, MessageCircle, Leaf, Activity,
  CheckSquare, Bell, Settings, Search, ChevronRight, ShieldCheck,
} from 'lucide-react'
import './CommandPalette.css'

const COMMANDS = [
  { id: 'dashboard',     label: 'Go to Dashboard',   Icon: LayoutDashboard, path: '/dashboard',     shortcut: 'G D' },
  { id: 'chat',          label: 'Open AI Assistant', Icon: MessageCircle,   path: '/chat',           shortcut: 'G C' },
  { id: 'remedies',      label: 'View Remedies',     Icon: Leaf,            path: '/remedies',       shortcut: 'G R' },
  { id: 'timeline',      label: 'Health Timeline',   Icon: Activity,        path: '/timeline',       shortcut: 'G T' },
  { id: 'checkin',       label: 'Weekly Check-In',   Icon: CheckSquare,     path: '/checkin',        shortcut: 'G K' },
  { id: 'interaction',   label: 'Herb Safety Checker', Icon: ShieldCheck,   path: '/interaction-check', shortcut: 'G H' },
  { id: 'notifications', label: 'Notifications',     Icon: Bell,            path: '/notifications',  shortcut: 'G N' },
  { id: 'settings',      label: 'Settings',          Icon: Settings,        path: '/settings',       shortcut: 'G S' },
]

export default function CommandPalette() {
  const [open, setOpen]       = useState(false)
  const [query, setQuery]     = useState('')
  const [activeIdx, setActiveIdx] = useState(0)
  const inputRef = useRef(null)
  const navigate = useNavigate()

  // Open on Cmd+K event dispatched by useKeyboardShortcuts
  useEffect(() => {
    const onOpen = () => { setOpen(true); setQuery(''); setActiveIdx(0) }
    window.addEventListener('ayura:cmdK', onOpen)
    return () => window.removeEventListener('ayura:cmdK', onOpen)
  }, [])

  // Auto-focus input
  useEffect(() => {
    if (open) {
      const t = setTimeout(() => inputRef.current?.focus(), 30)
      return () => clearTimeout(t)
    }
  }, [open])

  const close = useCallback(() => setOpen(false), [])

  const filtered = query.trim()
    ? COMMANDS.filter(c => c.label.toLowerCase().includes(query.toLowerCase()))
    : COMMANDS

  const handleSelect = useCallback((item) => {
    navigate(item.path)
    close()
  }, [navigate, close])

  function onKeyDown(e) {
    if (e.key === 'Escape') { close(); return }
    if (e.key === 'ArrowDown') { e.preventDefault(); setActiveIdx(i => Math.min(i + 1, filtered.length - 1)) }
    if (e.key === 'ArrowUp')   { e.preventDefault(); setActiveIdx(i => Math.max(i - 1, 0)) }
    if (e.key === 'Enter' && filtered[activeIdx]) handleSelect(filtered[activeIdx])
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            className="cmd-backdrop"
            onClick={close}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
          />
          <motion.div
            className="cmd-panel"
            role="dialog"
            aria-modal="true"
            aria-label="Command palette"
            initial={{ opacity: 0, scale: 0.96, y: -14 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -14 }}
            transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
          >
            {/* ── Search row ── */}
            <div className="cmd-search-row">
              <Search size={15} className="cmd-search-icon" strokeWidth={2.5} />
              <input
                ref={inputRef}
                className="cmd-input"
                placeholder="Jump to a page…"
                value={query}
                onChange={e => { setQuery(e.target.value); setActiveIdx(0) }}
                onKeyDown={onKeyDown}
                autoComplete="off"
                spellCheck={false}
              />
              <kbd className="cmd-esc-badge">ESC</kbd>
            </div>

            {/* ── Results ── */}
            <div className="cmd-results">
              {filtered.length === 0 ? (
                <div className="cmd-empty">No results for "{query}"</div>
              ) : (
                <>
                  <span className="cmd-section-label">Navigate</span>
                  {filtered.map((item, i) => {
                    const { Icon } = item
                    return (
                      <button
                        key={item.id}
                        className={`cmd-item${i === activeIdx ? ' active' : ''}`}
                        onClick={() => handleSelect(item)}
                        onMouseEnter={() => setActiveIdx(i)}
                      >
                        <div className="cmd-item-icon-wrap">
                          <Icon size={15} strokeWidth={2} />
                        </div>
                        <span className="cmd-item-label">{item.label}</span>
                        <kbd className="cmd-item-shortcut">{item.shortcut}</kbd>
                        <ChevronRight size={13} className="cmd-item-chevron" strokeWidth={2.5} />
                      </button>
                    )
                  })}
                </>
              )}
            </div>

            {/* ── Footer hints ── */}
            <div className="cmd-footer">
              <span className="cmd-hint"><kbd>↑↓</kbd> navigate</span>
              <span className="cmd-hint"><kbd>↵</kbd> open</span>
              <span className="cmd-hint"><kbd>⌘K</kbd> close</span>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
