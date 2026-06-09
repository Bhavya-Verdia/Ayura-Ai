import { useState, useEffect, useRef } from 'react'

/**
 * CountUp — animates from 0 → `to` when the element enters the viewport.
 *
 * Usage:
 *   <CountUp to={10000} suffix="+" prefix="" duration={1800} />
 *   <CountUp to={360} suffix="°" />
 */
export function useCountUp(target, duration = 1600, start = false) {
  const [count, setCount] = useState(0)
  const frameRef = useRef(null)

  useEffect(() => {
    if (!start) return
    let startTime = null
    const startVal = 0
    const endVal = target

    const step = (timestamp) => {
      if (!startTime) startTime = timestamp
      const elapsed = timestamp - startTime
      const progress = Math.min(elapsed / duration, 1)
      // ease-out-expo
      const eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress)
      setCount(Math.floor(startVal + (endVal - startVal) * eased))
      if (progress < 1) {
        frameRef.current = requestAnimationFrame(step)
      }
    }

    frameRef.current = requestAnimationFrame(step)
    return () => cancelAnimationFrame(frameRef.current)
  }, [target, duration, start])

  return count
}

export default function CountUp({
  to,
  suffix = '',
  prefix = '',
  duration = 1600,
  className = '',
}) {
  const ref = useRef(null)
  const [started, setStarted] = useState(false)
  const count = useCountUp(to, duration, started)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setStarted(true)
          obs.unobserve(el)
        }
      },
      { threshold: 0.4 }
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  return (
    <span ref={ref} className={className}>
      {prefix}{count.toLocaleString()}{suffix}
    </span>
  )
}
