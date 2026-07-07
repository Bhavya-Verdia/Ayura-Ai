import { useState, useEffect, useRef } from 'react'
import { m, AnimatePresence } from 'framer-motion'

// The app shell (MainLayout) scrolls an inner overflow container, not the
// window — so walk up from a sentinel node to find the actual scroller.
// Public pages (Landing etc.) scroll the window; null means "use window".
function findScrollParent(el) {
  // Stop before <body>/<html>: `overflow-x: hidden` on body computes its
  // overflow-y to `auto` even though the viewport is what actually scrolls.
  for (let node = el?.parentElement; node && node !== document.body; node = node.parentElement) {
    const { overflowY } = getComputedStyle(node)
    if (overflowY === 'auto' || overflowY === 'scroll') return node
  }
  return null
}

export default function ScrollToTop() {
  const sentinelRef = useRef(null)
  const scrollerRef = useRef(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const scroller = findScrollParent(sentinelRef.current)
    scrollerRef.current = scroller
    const target = scroller || window
    const getY = () => (scroller ? scroller.scrollTop : window.scrollY)
    const handleScroll = () => setVisible(getY() > 400)
    handleScroll()
    target.addEventListener('scroll', handleScroll, { passive: true })
    return () => target.removeEventListener('scroll', handleScroll)
  }, [])

  function scrollUp() {
    ;(scrollerRef.current || window).scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <>
      <span ref={sentinelRef} hidden aria-hidden="true" />
      <AnimatePresence>
        {visible && (
          <m.button
            className="scroll-to-top"
            onClick={scrollUp}
            initial={{ opacity: 0, scale: 0.8, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.8, y: 20 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            aria-label="Scroll to top"
            title="Back to top"
          >
            ↑
          </m.button>
        )}
      </AnimatePresence>
    </>
  )
}
