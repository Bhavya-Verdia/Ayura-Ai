import React, { useState } from 'react'
import { buildPoseFigure, GROUND_Y } from './poseSkeleton'

/**
 * Pose imagery with a guaranteed fallback.
 *
 * 49 of 113 poses have no image at all, and the 64 that do are hotlinked from
 * two third-party hosts that can disappear or start blocking at any time. Either
 * way the pose card used to render nothing where the figure should be. This
 * draws a category diagram instead, so every pose shows something deliberate
 * rather than a gap or a broken-image icon.
 *
 * The diagram is abstract on purpose — it reads as a schematic of the shape,
 * not as a photograph of a pose that we do not have.
 */

// One schematic per category: a horizon line plus a simplified body line.
const FIGURES = {
  standing:     'M50 88 L50 44 M50 44 L38 26 M50 44 L62 26 M50 62 L36 88 M50 62 L64 88',
  balancing:    'M50 88 L50 46 M50 46 L34 30 M50 46 L66 30 M50 64 L38 88 M50 64 L62 72 L48 78',
  seated:       'M32 78 L68 78 M50 78 L50 44 M50 44 L36 34 M50 44 L64 34 M32 78 Q50 70 68 78',
  forward_fold: 'M50 88 L50 58 M50 58 Q50 44 36 42 M36 42 L30 50 M50 58 Q50 44 64 42 M64 42 L70 50',
  backbend:     'M34 88 L34 62 Q50 40 66 62 L66 88 M50 46 L50 34',
  twist:        'M50 88 L50 48 M50 48 Q64 42 70 52 M50 56 Q36 50 30 60 M50 48 L50 40',
  inversion:    'M50 20 L50 62 M50 62 L36 84 M50 62 L64 84 M50 34 L34 46 M50 34 L66 46',
  supine:       'M24 66 L76 66 M30 66 L30 58 M46 66 Q52 54 60 60 M70 66 L70 60',
  prone:        'M24 70 L76 70 M32 70 Q46 56 62 62 L74 62 M40 70 L40 64',
  restorative:  'M22 68 L78 68 M32 68 Q50 56 68 68 M50 60 L50 52',
}

const CATEGORY_LABEL = {
  standing: 'Standing', balancing: 'Balance', seated: 'Seated',
  forward_fold: 'Forward fold', backbend: 'Backbend', twist: 'Twist',
  inversion: 'Inversion', supine: 'Supine', prone: 'Prone',
  restorative: 'Restorative',
}

function PoseDiagram({ category, name }) {
  const path = FIGURES[category] || FIGURES.standing
  return (
    <div className="pose-figure-fallback" role="img"
         aria-label={`${name} — ${CATEGORY_LABEL[category] || 'pose'} diagram`}>
      <svg viewBox="0 0 100 100" aria-hidden="true" focusable="false">
        <line className="pose-figure-ground" x1="14" y1="92" x2="86" y2="92" />
        <path className="pose-figure-body" d={path} />
      </svg>
      <span className="pose-figure-caption">{CATEGORY_LABEL[category] || 'Pose'}</span>
    </div>
  )
}

/**
 * Drawn pose figures are OFF.
 *
 * 12 of 113 poses were drawn, which is ~27% of the pose cards in a session: a
 * day's list showed five drawn figures among eleven category diagrams, and a
 * partially-illustrated list reads as broken in a way a uniformly plain one does
 * not. Consistency beats a better-looking minority. (The "36% of slots" figure
 * that made 12 poses sound like a reasonable first batch counted repetition —
 * Savasana appears in every session — so it flattered the coverage against what
 * a user actually scrolls past.)
 *
 * Everything needed to turn this back on is intact and tested: joint data in
 * yoga_poses.json, the renderer in poseSkeleton.js, validation in
 * test_yoga_practice_quality.py, and the engine still sends `figure` with each
 * pose. Flip this flag once the library is complete — roughly 60-80 poses, which
 * is where a session reads as consistently illustrated — or delete the lot if
 * commissioned artwork replaces it.
 */
const USE_DRAWN_FIGURES = false

function PoseSkeleton({ figure, name, mirror }) {
  const built = buildPoseFigure(figure, mirror)
  if (!built) return null
  return (
    <div className="pose-figure-fallback pose-figure-skeleton" role="img" aria-label={name}>
      <svg viewBox="0 0 100 100" aria-hidden="true" focusable="false">
        <line className="pose-figure-ground" x1="8" y1={GROUND_Y} x2="92" y2={GROUND_Y} />
        {/* One path: overlapping filled shapes in a single colour merge visually,
            so the body needs no union and no per-limb elements. */}
        <path className="pose-figure-silhouette" d={built.d} />
      </svg>
    </div>
  )
}

export function PoseFigure({ imageUrl, name, category, figure, mirror = false, className = '' }) {
  const [failed, setFailed] = useState(false)
  // The seed library shipped some literal "https://..." placeholders.
  const usable = imageUrl && !imageUrl.startsWith('https://...') && !failed

  if (!usable && figure && USE_DRAWN_FIGURES) {
    return <PoseSkeleton figure={figure} name={name} mirror={mirror} />
  }
  if (!usable) return <PoseDiagram category={category} name={name} />

  return (
    <img
      src={imageUrl}
      alt={name}
      className={`yoga-pose-image ${className}`}
      loading="lazy"
      decoding="async"
      onError={() => setFailed(true)}
    />
  )
}

export default PoseFigure
