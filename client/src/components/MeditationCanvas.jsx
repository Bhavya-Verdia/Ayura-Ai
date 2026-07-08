import { useRef, useEffect } from 'react'
import { useReducedMotion } from 'framer-motion'

/* ── Palette ──────────────────────────────────────────────────── */
const TEAL    = [92,171,116]
const VIOLET  = [230,162,60]
const SKY     = [96,  165, 250]
const AMBER   = [251, 191,  36]

const YOGA_COLORS    = [TEAL, TEAL, VIOLET, SKY]   // teal weighted 2×
const OM_COLORS      = [TEAL, VIOLET, AMBER]
const SPARKLE_COLORS = [TEAL, VIOLET, AMBER]

function rgba(rgb, a) { return `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${a})` }

/* ── Sprite builder ───────────────────────────────────────────── */
const YOGA_NOM_SIZES = [8, 11, 15, 19]   // px — kept deliberately small
const OM_NOM_SIZES   = [11, 16, 22, 28]  // Om glyphs can be a touch larger

function makeEmojiSprite(nomSize, rgb) {
  const emojiPx  = nomSize * 3.2
  const canvasPx = Math.ceil(emojiPx * 1.35)
  const off = document.createElement('canvas')
  off.width = off.height = canvasPx
  const c = off.getContext('2d')
  c.font         = `${emojiPx}px "Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji",sans-serif`
  c.textAlign    = 'center'
  c.textBaseline = 'middle'
  c.fillText('🧘', canvasPx / 2, canvasPx / 2)
  c.globalCompositeOperation = 'source-in'
  c.fillStyle = `rgb(${rgb.join(',')})`
  c.fillRect(0, 0, canvasPx, canvasPx)
  return { canvas: off, px: canvasPx }
}

function makeOmSprite(nomSize, rgb) {
  const textPx   = nomSize * 2.8
  const canvasPx = Math.ceil(textPx * 1.5)
  const off = document.createElement('canvas')
  off.width = off.height = canvasPx
  const c = off.getContext('2d')
  c.fillStyle    = `rgb(${rgb.join(',')})`
  c.font         = `bold ${textPx}px Georgia,"Noto Serif Devanagari",serif`
  c.textAlign    = 'center'
  c.textBaseline = 'middle'
  c.fillText('ॐ', canvasPx / 2, canvasPx / 2)
  return { canvas: off, px: canvasPx }
}

function buildSpriteMap() {
  const yoga = {}, om = {}
  const uniqueYogaColors = [TEAL, VIOLET, SKY]
  const uniqueOmColors   = [TEAL, VIOLET, AMBER]
  uniqueYogaColors.forEach(rgb => {
    const k = rgb.join(',')
    yoga[k] = {}
    YOGA_NOM_SIZES.forEach(sz => { yoga[k][sz] = makeEmojiSprite(sz, rgb) })
  })
  uniqueOmColors.forEach(rgb => {
    const k = rgb.join(',')
    om[k] = {}
    OM_NOM_SIZES.forEach(sz => { om[k][sz] = makeOmSprite(sz, rgb) })
  })
  return { yoga, om }
}

function closest(size, sizes) {
  return sizes.reduce((a, b) => Math.abs(b - size) < Math.abs(a - size) ? b : a)
}

/* ── Spawners ─────────────────────────────────────────────────── */
function spawnYoga(W, H) {
  const size = 7 + Math.random() * 13   // 7–20 px nominal
  return {
    kind:     'yoga',
    baseX:    Math.random() * W,
    y:        Math.random() * H,
    size,
    rgb:      YOGA_COLORS[Math.floor(Math.random() * YOGA_COLORS.length)],
    opacity:  0.07 + Math.random() * 0.16,
    speed:    12 + Math.random() * 22,
    swayAmp:  5  + Math.random() * 18,
    swayFreq: 0.12 + Math.random() * 0.28,
    phase:    Math.random() * Math.PI * 2,
    tilt:     (Math.random() - 0.5) * 0.18,
    glow:     Math.random() > 0.52,
  }
}

function spawnOm(W, H) {
  const size = 11 + Math.random() * 16  // 11–27 px nominal
  return {
    kind:     'om',
    baseX:    Math.random() * W,
    y:        Math.random() * H,
    size,
    rgb:      OM_COLORS[Math.floor(Math.random() * OM_COLORS.length)],
    opacity:  0.05 + Math.random() * 0.12,
    speed:    6  + Math.random() * 12,   // slower drift — more majestic
    swayAmp:  3  + Math.random() * 12,
    swayFreq: 0.07 + Math.random() * 0.18,
    phase:    Math.random() * Math.PI * 2,
    tilt:     (Math.random() - 0.5) * 0.10,
    glow:     Math.random() > 0.45,
  }
}

function spawnSparkle(W, H) {
  return {
    x:       Math.random() * W,
    y:       Math.random() * H,
    r:       0.6 + Math.random() * 1.4,
    rgb:     SPARKLE_COLORS[Math.floor(Math.random() * SPARKLE_COLORS.length)],
    phase:   Math.random() * Math.PI * 2,
    freq:    0.6 + Math.random() * 1.8,
    baseOpa: 0.12 + Math.random() * 0.40,
  }
}

/* ── Component ────────────────────────────────────────────────── */
export default function MeditationCanvas() {
  const canvasRef     = useRef(null)
  const reducedMotion = useReducedMotion()

  useEffect(() => {
    if (reducedMotion) return
    const canvas = canvasRef.current
    const ctx    = canvas.getContext('2d')
    const sprites = buildSpriteMap()

    let W, H, figures = [], sparkles = [], t = 0, lastTime = null, raf

    // Phones: soft glowy sprites survive a lower backing resolution invisibly,
    // and the slow drift reads identically at 30fps — half the shadowBlur
    // passes per second on the GPU that actually struggles with them.
    const coarse = window.matchMedia('(pointer: coarse), (max-width: 900px)').matches
    const MIN_FRAME_MS = coarse ? 31 : 0

    function resize() {
      // DPR-aware: render at device resolution (capped for perf) so the
      // sprites stay crisp on retina, then work in CSS pixels via setTransform.
      const dpr = Math.min(window.devicePixelRatio || 1, coarse ? 1.25 : 2)
      W = window.innerWidth
      H = window.innerHeight
      canvas.width  = Math.round(W * dpr)
      canvas.height = Math.round(H * dpr)
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      const area = W * H

      // 70 % yoga, 30 % Om. Counts scale with viewport area but are kept sparse
      // for an elegant, breathable field (denser read as busy/cluttered) and
      // capped so large/4K displays don't spawn hundreds of shadow-blurred
      // sprites (shadowBlur is the single most expensive canvas op per frame).
      const total    = Math.min(Math.round(area / 46000), 60)
      const yogaCount = Math.round(total * 0.70)
      const omCount   = total - yogaCount

      figures = [
        ...Array.from({ length: yogaCount }, () => spawnYoga(W, H)),
        ...Array.from({ length: omCount   }, () => spawnOm(W, H)),
      ]
      sparkles = Array.from({ length: Math.min(Math.round(area / 13000), 120) }, () => spawnSparkle(W, H))
    }

    function frame(now) {
      if (MIN_FRAME_MS && lastTime && now - lastTime < MIN_FRAME_MS) {
        raf = requestAnimationFrame(frame)
        return
      }
      const dt = lastTime ? Math.min((now - lastTime) / 1000, 0.05) : 0.016
      lastTime  = now
      t        += dt

      ctx.clearRect(0, 0, W, H)

      // sparkles
      sparkles.forEach(s => {
        const opa = s.baseOpa * (0.5 + 0.5 * Math.sin(t * s.freq + s.phase))
        ctx.save()
        ctx.globalAlpha = opa
        ctx.fillStyle   = rgba(s.rgb, 1)
        ctx.shadowBlur  = 4
        ctx.shadowColor = rgba(s.rgb, 0.85)
        ctx.beginPath(); ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2); ctx.fill()
        ctx.restore()
      })

      // yoga & om figures
      figures.forEach(fig => {
        fig.y -= fig.speed * dt
        const x = fig.baseX + Math.sin(t * fig.swayFreq + fig.phase) * fig.swayAmp

        const map     = fig.kind === 'yoga' ? sprites.yoga : sprites.om
        const nomSzs  = fig.kind === 'yoga' ? YOGA_NOM_SIZES : OM_NOM_SIZES
        const nomSz   = closest(fig.size, nomSzs)
        const sprite  = map[fig.rgb.join(',')][nomSz]
        const drawPx  = sprite.px * (fig.size / nomSz)

        ctx.save()
        ctx.globalAlpha = fig.opacity
        if (fig.glow) { ctx.shadowBlur = fig.size * 2.6; ctx.shadowColor = rgba(fig.rgb, 0.70) }
        ctx.translate(x, fig.y)
        if (fig.tilt) ctx.rotate(fig.tilt)
        ctx.drawImage(sprite.canvas, -drawPx / 2, -drawPx / 2, drawPx, drawPx)
        ctx.restore()

        if (fig.y < -drawPx) {
          fig.baseX = Math.random() * W
          fig.y     = H + drawPx + Math.random() * 100
          fig.phase = Math.random() * Math.PI * 2
        }
      })

      raf = requestAnimationFrame(frame)
    }

    // Pause the rAF loop while the tab is backgrounded — no point burning the
    // GPU/CPU on an invisible canvas, and it avoids a huge dt jump on return.
    function onVisibility() {
      if (document.hidden) {
        cancelAnimationFrame(raf)
        raf = null
      } else if (!raf) {
        lastTime = null
        raf = requestAnimationFrame(frame)
      }
    }

    resize()
    window.addEventListener('resize', resize)
    document.addEventListener('visibilitychange', onVisibility)
    raf = requestAnimationFrame(frame)
    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', resize)
      document.removeEventListener('visibilitychange', onVisibility)
    }
  }, [reducedMotion])

  return (
    <canvas ref={canvasRef} aria-hidden="true"
      style={{ position:'fixed', inset:0, width:'100%', height:'100%',
               zIndex:0, pointerEvents:'none', opacity:0.90 }} />
  )
}
