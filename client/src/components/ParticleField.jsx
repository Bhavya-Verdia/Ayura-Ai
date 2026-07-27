import { useEffect, useMemo, useRef } from 'react'
import { useReducedMotion } from 'framer-motion'
import { useTheme } from '../providers/ThemeProvider'
import useLowPowerMode from '../hooks/useLowPowerMode'

/* ────────────────────────────────────────────────────────────────────────────
   Ambient particle field, rendered to a SINGLE <canvas>.

   This replaces a version that mounted one DOM element per particle — up to
   167 of them (160 dots + 7 orbs) on Onboarding / Settings / Admin — each with
   its own CSS keyframe animation.

   MEASURE BEFORE YOU BELIEVE THIS IS FASTER. Benchmarked on /settings (the
   heaviest case, 160 dots) at Pixel 5 + 4x CPU throttle, the DOM version cost
   nothing at steady state: 60fps, zero janky frames, and task latency
   identical with the field present vs. removed. CSS transform animations are
   compositor-driven, so the main thread does no per-frame work at all — while
   a canvas rAF loop necessarily does.

   What the canvas actually buys is therefore NOT frame rate:
     - 168 fewer DOM nodes (725 -> 557 elements on /settings), so less style
       recalc and a smaller tree to walk on every layout.
     - 167 fewer compositor layers. Each animated element gets its own GPU
       texture; that is invisible on a dev machine and is the thing most likely
       to bite a real low-memory phone, which is exactly where we cannot
       measure.
     - It can stop entirely when hidden (see the visibility/IntersectionObserver
       gating below) instead of animating behind another view.

   The trade is real main-thread work per frame. Keep the draw loop cheap: the
   glow is baked into pre-rendered sprites (never `shadowBlur` per particle per
   frame), orbs are pre-rendered once, and the backing store is DPR-capped.
   ──────────────────────────────────────────────────────────────────────────── */

function seededRandom(seed) {
  const value = Math.sin(seed * 12.9898) * 43758.5453
  return value - Math.floor(value)
}

/* CSS `ease-in-out` is cubic-bezier(0.42, 0, 0.58, 1). Smoothstep is within a
   couple of percent of it and needs no solver — on a 14-32s ambient drift the
   difference is not perceivable. */
const easeInOut = (t) => t * t * (3 - 2 * t)

/* Progress of a CSS `infinite alternate` animation at time `ms`, matching
   `animation-duration`/`animation-delay` semantics (delays here are negative,
   which offsets the start). Returns 0..1, ping-ponging. */
function alternateProgress(ms, durationMs, delayMs) {
  const cycles = (ms - delayMs) / durationMs
  const iteration = Math.floor(cycles)
  const frac = cycles - iteration
  // Odd iterations play backwards. ease-in-out is symmetric, so reversing the
  // input and easing is equivalent to easing and reversing the output.
  return easeInOut(iteration % 2 === 0 ? frac : 1 - frac)
}

/* A dot plus its glow, drawn ONCE into an offscreen canvas and then blitted.
   The DOM version used `box-shadow: 0 0 12px currentColor`; shadowBlur here is
   paid a handful of times at setup rather than 160x per frame. Sizes are
   quantised to 0.5px so a whole field needs ~8 sprites per colour. */
function makeDotSprite(size, fill, glow, blur) {
  const r = size / 2
  const pad = blur + 2
  const dim = Math.ceil((r + pad) * 2)
  const c = document.createElement('canvas')
  c.width = dim
  c.height = dim
  const g = c.getContext('2d')
  g.shadowColor = glow
  g.shadowBlur = blur
  g.fillStyle = fill
  g.beginPath()
  g.arc(dim / 2, dim / 2, r, 0, Math.PI * 2)
  g.fill()
  // A second pass deepens the glow the way a box-shadow reads against a dark
  // backdrop (the DOM version's shadow sits under a fully opaque dot).
  g.fill()
  return c
}

/* `radial-gradient(closest-side, color 0%, transparent 88%)` on a circle. */
function makeOrbSprite(size, color) {
  const dim = Math.ceil(size)
  const c = document.createElement('canvas')
  c.width = dim
  c.height = dim
  const g = c.getContext('2d')
  const grad = g.createRadialGradient(dim / 2, dim / 2, 0, dim / 2, dim / 2, dim / 2)
  grad.addColorStop(0, color)
  grad.addColorStop(0.88, 'transparent')
  grad.addColorStop(1, 'transparent')
  g.fillStyle = grad
  g.fillRect(0, 0, dim, dim)
  return c
}

export default function ParticleField({
  count = 120,
  color1 = '#06b6d4',
  color2 = '#8b5cf6',
  spread = 18,
  style = {},
  className = '',
}) {
  const { theme } = useTheme()
  const prefersReducedMotion = useReducedMotion()
  const lowPower = useLowPowerMode()
  const wrapRef = useRef(null)
  const canvasRef = useRef(null)

  // Phones get the same field density as the laptop for a consistent look;
  // only reduced-motion thins the field (and drops the orbs below).
  const particleCount = lowPower ? Math.min(count, 22) : Math.min(count, 160)
  const isLight = theme === 'light'

  // Identical seeded geometry to the DOM version, so the field is pixel-for-
  // pixel the same arrangement it has always been.
  const particles = useMemo(() => {
    return Array.from({ length: particleCount }, (_, index) => {
      const depth = seededRandom(index + 201)
      const drift = 12 + seededRandom(index + 301) * spread
      return {
        x: seededRandom(index + 1) * 100,
        y: seededRandom(index + 101) * 100,
        size: 1 + depth * 3.4,
        opacity: 0.18 + depth * (isLight ? 0.22 : 0.46),
        duration: 14 + seededRandom(index + 401) * 18,
        delay: seededRandom(index + 501) * -18,
        driftX: (seededRandom(index + 601) - 0.5) * drift,
        driftY: (seededRandom(index + 701) - 0.5) * drift,
        color: seededRandom(index + 801) > 0.5 ? color1 : color2,
      }
    })
  }, [color1, color2, particleCount, spread, isLight])

  const orbs = useMemo(() => {
    if (lowPower) return []
    return Array.from({ length: 7 }, (_, index) => ({
      x: seededRandom(index + 901) * 100,
      y: seededRandom(index + 1001) * 100,
      size: 90 + seededRandom(index + 1101) * 150,
      duration: 18 + seededRandom(index + 1201) * 20,
      delay: seededRandom(index + 1301) * -18,
      color: seededRandom(index + 1401) > 0.5 ? color1 : color2,
    }))
  }, [color1, color2, lowPower])

  useEffect(() => {
    const canvas = canvasRef.current
    const wrap = wrapRef.current
    if (!canvas || !wrap) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Cap the backing store at 2x. These are soft, sub-5px dots — a 3x phone
    // DPR would more than double the fill cost for no visible gain.
    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    let w = 0
    let h = 0

    const resize = () => {
      const rect = wrap.getBoundingClientRect()
      w = rect.width
      h = rect.height
      canvas.width = Math.max(1, Math.round(w * dpr))
      canvas.height = Math.max(1, Math.round(h * dpr))
      canvas.style.width = `${w}px`
      canvas.style.height = `${h}px`
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }
    resize()

    // Light theme swapped the glow for a fixed muted green
    // (.particle-field-light .particle-dot in index.css); dark glows in the
    // particle's own colour.
    const dotBlur = isLight ? 10 : 12
    const glowFor = (c) => (isLight ? 'rgba(47,143,91,0.24)' : c)

    const dotSprites = new Map()
    const dotSprite = (size, color) => {
      const q = Math.round(size * 2) / 2
      const key = `${color}|${q}`
      let s = dotSprites.get(key)
      if (!s) {
        s = makeDotSprite(q, color, glowFor(color), dotBlur)
        dotSprites.set(key, s)
      }
      return s
    }
    const orbSprites = orbs.map((o) => makeOrbSprite(o.size, o.color))
    const orbAlpha = isLight ? 0.12 : 0.09

    const draw = (ms) => {
      ctx.clearRect(0, 0, w, h)

      for (let i = 0; i < orbs.length; i++) {
        const o = orbs[i]
        // @keyframes particle-orb-float: translate3d(-16,-10) scale(.92)
        //                             -> translate3d( 18, 14) scale(1.08)
        const p = prefersReducedMotion ? 0 : alternateProgress(ms, o.duration * 1000, o.delay * 1000)
        const tx = -16 + p * 34
        const ty = -10 + p * 24
        const sc = prefersReducedMotion ? 1 : 0.92 + p * 0.16
        const s = orbSprites[i]
        const d = o.size * sc
        ctx.globalAlpha = orbAlpha
        ctx.drawImage(s, (o.x / 100) * w + tx - d / 2, (o.y / 100) * h + ty - d / 2, d, d)
      }

      for (let i = 0; i < particles.length; i++) {
        const p0 = particles[i]
        // @keyframes particle-drift: translate3d(0,0) scale(.92)
        //                         -> translate3d(driftX, driftY) scale(1.08)
        const p = prefersReducedMotion ? 0 : alternateProgress(ms, p0.duration * 1000, p0.delay * 1000)
        const tx = p * p0.driftX
        const ty = p * p0.driftY
        const sc = prefersReducedMotion ? 1 : 0.92 + p * 0.16
        const s = dotSprite(p0.size, p0.color)
        // The sprite is the dot PLUS its glow padding, so it must be blitted at
        // the sprite's own aspect, scaled by the animation — not at dot size.
        const d = s.width * sc
        ctx.globalAlpha = prefersReducedMotion ? p0.opacity * 0.5 : p0.opacity
        ctx.drawImage(s, (p0.x / 100) * w + tx - d / 2, (p0.y / 100) * h + ty - d / 2, d, d)
      }
      ctx.globalAlpha = 1
    }

    // Static single paint when the user asked for reduced motion — no loop.
    if (prefersReducedMotion) {
      draw(0)
      const ro = new ResizeObserver(() => { resize(); draw(0) })
      ro.observe(wrap)
      return () => ro.disconnect()
    }

    let raf = 0
    let running = false
    const start = performance.now()
    const tick = (t) => {
      draw(t - start)
      raf = requestAnimationFrame(tick)
    }
    const play = () => { if (!running) { running = true; raf = requestAnimationFrame(tick) } }
    const stop = () => { if (running) { running = false; cancelAnimationFrame(raf) } }

    // Don't burn frames on a field nobody can see. The DOM version kept
    // animating while scrolled off-screen or on a background tab.
    const io = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting && !document.hidden) play(); else stop() },
      { threshold: 0 }
    )
    io.observe(wrap)
    const onVisibility = () => { if (document.hidden) stop(); else play() }
    document.addEventListener('visibilitychange', onVisibility)

    const ro = new ResizeObserver(() => resize())
    ro.observe(wrap)

    return () => {
      stop()
      io.disconnect()
      ro.disconnect()
      document.removeEventListener('visibilitychange', onVisibility)
    }
  }, [particles, orbs, isLight, prefersReducedMotion])

  return (
    <div
      ref={wrapRef}
      className={`particle-field-wrap particle-field-${theme} ${className}`.trim()}
      style={{
        position: 'absolute',
        inset: 0,
        zIndex: 0,
        pointerEvents: 'none',
        overflow: 'hidden',
        ...style,
      }}
      aria-hidden="true"
    >
      <canvas ref={canvasRef} className="pf-canvas" />
    </div>
  )
}
