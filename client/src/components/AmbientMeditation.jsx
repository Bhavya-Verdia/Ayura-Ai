import { useEffect, useState } from 'react'
import { useReducedMotion } from 'framer-motion'
import './AmbientMeditation.css'

// Laptop/desktop only, by explicit user request (an intentional exception to the
// "mobile = identical desktop visuals" rule). `pointer: fine` excludes phones
// even in landscape ≥901px; the width floor excludes small windows. Mirrored by
// a CSS mobile-hide so prerendered HTML never flashes glyphs on a phone.
const DESKTOP_QUERY = '(min-width: 901px) and (pointer: fine)'

function useIsDesktop() {
  const [desktop, setDesktop] = useState(
    () => typeof window !== 'undefined' && !!window.matchMedia && window.matchMedia(DESKTOP_QUERY).matches
  )
  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return
    const mq = window.matchMedia(DESKTOP_QUERY)
    const update = () => setDesktop(mq.matches)
    update()
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, [])
  return desktop
}

/**
 * AmbientMeditation — a sparse field of Om marks (ॐ) and padmasana (lotus pose)
 * figures drifting slowly upward in the gutters beside the centred form card on
 * the auth + onboarding routes. DESKTOP ONLY.
 *
 * This is a GROUND-UP replacement for the retired MeditationCanvas, deliberately
 * NOT a full-viewport <canvas> that repainted every frame (the confirmed cause of
 * the 2026-07 app-wide compositing flicker). Here every glyph is a tiny DOM node
 * animated purely by CSS transform + opacity — the compositor just translates
 * each little layer, there is no rAF, no per-frame full-screen repaint, and no
 * animated filter/blur/mix-blend anywhere (the actual flicker trigger). The
 * container adds `contain: paint` + `isolation: isolate` so its painting can
 * never invalidate the rest of the page.
 *
 * Self-gates off touch / ≤900px via the DESKTOP_QUERY matchMedia above, plus
 * reduced-motion, so it only ever runs on a real laptop/desktop. Note it does
 * NOT use useLowPowerMode — that hook now checks reduced-motion ONLY (mobile
 * visual parity), so it would not keep this off phones.
 */

// Balanced Om + lotus-pose figure — both should read clearly as they float up.
const PATTERN = ['om', 'fig', 'om', 'fig', 'om']

// Om (ॐ) as a traced outline rather than a text glyph. The app's UI fonts carry
// no Devanagari, so the character fell back to whatever system face the OS had —
// stretched on this Mac, and a different shape again on Windows/Linux. This path
// is vectorised from the reference mark the user picked, so every platform gets
// the identical, correctly-proportioned symbol.
const OM_PATH = 'M8.91 27.13L17.12 38.34C17.12 38.34 22.2 34.55 25.43 33.23C28.66 31.91 31.93 31.26 34.73 31.13C37.54 31 39.13 31.34 40.74 32.53C42.36 33.73 43.16 35.89 43.54 37.64C43.93 39.38 43.6 40.7 42.84 42.04C42.09 43.38 42.82 44.03 39.44 44.94C36.06 45.86 24.42 47.05 24.42 47.05C24.42 47.05 27.6 57.33 30.43 60.16C33.26 62.99 37.2 60.87 39.84 62.46C42.48 64.06 44.02 66.19 44.84 68.87C45.67 71.55 45.81 74.1 44.34 77.08C42.88 80.05 39.97 83.03 36.84 85.09C33.7 87.14 31.36 88.29 27.23 88.29C23.1 88.29 18.04 87.07 14.31 85.09C10.59 83.1 9.51 81.55 6.91 77.48C4.3 73.4 0.1 62.86 0.1 62.86C0.1 62.86 1.87 77.5 4.8 83.68C7.74 89.87 10.87 93.62 16.12 96.6C21.36 99.57 28 100.21 33.43 99.9C38.87 99.59 42.37 97.15 45.75 94.89C49.12 92.64 50.13 90.58 51.85 87.59C53.58 84.6 54.59 81.81 55.16 78.58C55.72 75.35 55.67 72.94 54.95 69.97C54.24 67 51.25 62.36 51.25 62.36C51.25 62.36 56.68 63.74 59.56 63.46C62.44 63.19 63.7 64.31 66.97 60.86C70.23 57.41 74.42 48.31 77.38 44.64C80.33 40.97 81.14 41.13 83.08 40.84C85.03 40.55 86.56 41.04 87.99 43.04C89.42 45.04 90.38 48.25 90.89 51.75C91.4 55.26 91.41 58.73 90.79 62.16C90.17 65.59 89.85 67.61 87.49 70.47C85.12 73.33 81.09 76.73 77.88 77.78C74.67 78.82 72.94 77.83 69.97 76.18C67 74.52 61.66 68.77 61.66 68.77C61.66 68.77 61.49 71.19 62.66 73.87C63.84 76.55 65.44 80.7 68.07 83.38C70.69 86.06 73.27 87.85 76.98 88.49C80.68 89.13 84.87 88.41 88.29 86.89C91.7 85.36 93.54 83.36 95.6 80.18C97.65 77.01 98.77 73.77 99.5 69.57C100.23 65.37 100.24 61.77 99.6 57.26C98.96 52.74 98.03 48.74 96 44.94C93.96 41.15 91.53 38.59 88.49 36.54C85.44 34.48 82.37 34.01 79.38 33.73C76.39 33.46 76.5 31 72.17 35.04C67.84 39.07 60.22 51.46 55.76 55.76C51.3 60.05 50.42 58.73 47.85 58.46C45.28 58.18 41.74 54.25 41.74 54.25C41.74 54.25 47.86 50.56 49.75 47.35C51.64 44.14 52.09 40.17 52.05 36.74C52.02 33.3 50.93 31.23 49.55 28.63C48.17 26.02 46.62 24.23 44.54 22.52C42.47 20.82 41.34 20.02 38.24 19.32C35.14 18.62 33 17.29 27.63 18.72C22.25 20.15 8.91 27.13 8.91 27.13ZM42.54 8.11C42.54 8.11 44.77 13.89 45.95 16.22C47.12 18.55 47.46 19.04 48.95 20.82C50.44 22.6 52.24 24.51 54.05 25.93C55.87 27.34 56.6 27.74 58.86 28.53C61.12 29.32 63.82 29.97 66.37 30.23C68.92 30.49 71.01 30.15 72.77 29.93C74.53 29.71 74.75 29.49 75.98 29.03C77.21 28.57 77.72 28.55 79.48 27.43C81.24 26.31 85.59 22.92 85.59 22.92C85.59 22.92 85.39 22.23 84.08 20.52C82.78 18.81 78.48 13.61 78.48 13.61C78.48 13.61 74.9 16.38 73.37 17.32C71.85 18.25 71.34 18.35 70.17 18.72C69 19.09 68.49 19.25 66.97 19.32C65.44 19.39 63.77 19.39 61.86 19.12C59.95 18.84 58.3 18.41 56.56 17.82C54.81 17.23 53.99 16.85 52.35 15.92C50.72 14.98 49.45 14.14 47.65 12.71C45.85 11.28 42.54 8.11 42.54 8.11ZM60.86 0L53.35 8.01L61.96 15.12L69.57 7.01L60.86 0Z'

function OmIcon({ size }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="currentColor" aria-hidden="true">
      <path fillRule="evenodd" d={OM_PATH} />
    </svg>
  )
}

// Padmasana (lotus pose) silhouette, vector-traced from the reference image the
// user chose — same method as the Om. Hand-drawing this figure failed four times
// over two sessions (it read as a robe, a bell, a lamp, or a generic user
// avatar); tracing a real pose keeps the proportions honest. The two enclosed
// gaps between the arms and the torso are what carry the read — those triangles
// are the difference between "seated meditator" and "blob".
//
// The hands are left as the source drew them. A chin-mudra ring was tried and
// removed: the fingers are ~7 units across, sub-pixel at sprite scale, so it had
// to be stylised into a knob-plus-hole that read as heavier and worse.
const PDM_ASPECT = 0.8269
const PDM_PATH = 'M36.19 0.35C34.52 0.7 33.86 1.45 32.87 2.45C31.87 3.44 31.22 3.72 30.77 5.77C30.32 7.82 30.13 11.3 30.42 13.64C30.71 15.98 32.53 16.74 32.34 18.53C32.15 20.33 30.11 21.28 29.37 23.43C28.63 25.57 29.96 28.35 28.32 30.24C26.69 32.14 22.47 32.33 20.45 33.74C18.44 35.15 18.75 32.58 17.31 37.94C15.87 43.29 14.06 57.55 12.59 62.94C11.11 68.32 11.35 63.21 9.27 67.31C7.18 71.41 2.89 80.54 1.22 85.31C-0.44 90.09 -0.11 91.24 0.17 93.36C0.46 95.47 1.16 95.8 2.8 96.85C4.43 97.91 2.26 99.7 9.09 99.13C15.92 98.55 30.23 93.67 40.03 93.71C49.84 93.74 55.79 98.24 62.59 99.3C69.38 100.36 73.48 100.31 77.1 99.48C80.72 98.64 81.32 96.42 82.34 94.76C83.37 93.09 82.92 92.15 82.69 90.38C82.47 88.62 82.53 87.22 81.12 85.14C79.71 83.06 77.85 83 75 79.02C72.15 75.05 68.32 71.41 65.56 63.46C62.8 55.51 61.79 41.4 59.97 35.66C58.14 29.93 57.77 33.16 55.59 32.17C53.41 31.17 50.13 31.33 48.08 30.24C46.03 29.16 45.21 27.76 44.41 26.22C43.6 24.69 43.23 24.06 43.71 21.85C44.19 19.64 46.68 17.46 47.03 14.16C47.38 10.86 46.56 6.35 45.63 3.85C44.7 1.35 43.69 1.17 41.96 0.52C40.23 -0.12 37.86 -0 36.19 0.35ZM23.95 52.8C23.95 52.8 25.25 53.69 25.7 55.07C26.15 56.45 26.3 58.07 26.4 60.31C26.49 62.56 26.35 65.58 26.22 67.31C26.1 69.04 25.96 68.95 25.7 69.76C25.44 70.56 25.75 70.17 24.83 71.68C23.9 73.18 21.88 76.79 20.63 77.97C19.38 79.16 18.68 77.95 18.01 78.15C17.33 78.34 17.18 78.67 16.96 79.02C16.73 79.37 16.91 79.78 16.78 80.07C16.66 80.36 16.8 80.4 16.26 80.59C15.71 80.79 15 80.73 13.81 81.12C12.63 81.5 10.69 82.4 9.79 82.69C8.89 82.98 9.24 82.88 8.92 82.69C8.6 82.5 8.17 82 8.04 81.64C7.91 81.29 7 82.08 8.22 80.77C9.43 79.46 13.02 76.3 14.69 74.48C16.35 72.65 16.57 72.09 17.31 70.8C18.04 69.52 18.23 68.96 18.71 67.48C19.19 66.01 19.39 64.4 19.93 62.76C20.47 61.13 21.1 60.3 21.68 58.57C22.26 56.84 22.66 54.38 23.08 53.32C23.49 52.26 23.95 52.8 23.95 52.8ZM53.85 51.75C53.85 51.75 54 50.73 54.55 52.27C55.09 53.81 55.47 56.45 56.82 60.14C58.16 63.83 60.64 69.65 61.89 72.38C63.14 75.1 63.03 74.23 63.64 75C64.25 75.77 63.74 75.39 65.21 76.57C66.68 77.76 70.49 80.47 71.68 81.47C72.86 82.46 71.77 81.8 71.68 81.99C71.58 82.19 72.12 82.74 71.15 82.52C70.19 82.29 67.59 81.54 66.43 80.77C65.28 80 65.53 78.93 64.86 78.32C64.19 77.71 63.5 77.9 62.76 77.45C62.03 77 61.61 76.23 60.84 75.87C60.07 75.52 59.4 75.46 58.57 75.52C57.73 75.59 56.93 76.32 56.29 76.22C55.65 76.13 55.68 75.99 55.07 75C54.46 74.01 53.61 72.53 52.97 70.8C52.33 69.07 51.73 68.6 51.57 65.56C51.41 62.51 51.68 56.73 52.1 54.2C52.51 51.66 53.85 51.75 53.85 51.75Z'

function FigureIcon({ size }) {
  return (
    <svg
      height={size}
      width={size * PDM_ASPECT}
      viewBox="0 0 82.69 100"
      fill="currentColor"
      aria-hidden="true"
    >
      <path fillRule="evenodd" d={PDM_PATH} />
    </svg>
  )
}

// Layout is generated ONCE at module load (not during render — keeps the
// component pure and lint-clean, and a stable field across navigations is fine).
const rnd = (a, b) => a + Math.random() * (b - a)
const SPRITES = Array.from({ length: 22 }, (_, i) => {
  const kind = PATTERN[i % PATTERN.length]
  // Auth/onboarding pages centre a form card and these glyphs float IN FRONT of
  // the page (z-index 2), so keep them in the empty LEFT/RIGHT gutters — clear of
  // the card. Tight ranges + small drift below keep them off the card edges.
  // The right bound stops short of the edge because `left` positions the sprite's
  // LEFT edge — pushing it past ~95vw clipped glyphs in half against the
  // overflow:hidden container.
  const left = i % 2 === 0 ? rnd(1.5, 18) : rnd(80, 94.5)
  return {
    id: i,
    kind,
    left,                                           // vw
    // ONE size for both kinds: `size` is a HEIGHT, and both glyphs fill their
    // viewBox vertically, so an Om and an asana drawn at the same value render at
    // the same visual height (the asana is simply narrower, at ~0.83 aspect).
    size: rnd(34, 54),
    duration: rnd(22, 40),                          // s — slow float, but visibly moving
    delay: -rnd(0, 40),                             // negative → mid-flight on first paint
    drift: rnd(-26, 26),                            // px lateral sway (small — stay in the gutter)
    spin: rnd(-10, 10),                             // deg gentle rotate
    peak: kind === 'om' ? rnd(0.7, 0.95) : rnd(0.62, 0.85),
  }
})

export default function AmbientMeditation() {
  const isDesktop = useIsDesktop()
  const reduced = useReducedMotion()
  if (!isDesktop || reduced) return null

  return (
    <div className="ambient-med" aria-hidden="true">
      {SPRITES.map((s) => (
        <span
          key={s.id}
          className={`ambient-med-sprite ambient-med-${s.kind}`}
          style={{
            left: `${s.left}vw`,
            animationDuration: `${s.duration}s`,
            animationDelay: `${s.delay}s`,
            '--drift': `${s.drift}px`,
            '--spin': `${s.spin}deg`,
            '--peak': s.peak,
          }}
        >
          {s.kind === 'om' ? <OmIcon size={s.size} /> : <FigureIcon size={s.size} />}
        </span>
      ))}
    </div>
  )
}
