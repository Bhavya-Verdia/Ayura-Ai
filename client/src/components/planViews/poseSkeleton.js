/**
 * Pose figures drawn from joint coordinates.
 *
 * A pose carries a `figure`: a handful of named joints in a 0-100 box, ground at
 * y=92. One renderer turns those into a body, so every pose is drawn with the
 * same proportions and ground line — 113 poses look like one system rather than
 * 113 separate drawings. Authoring a pose means placing points, not writing path
 * syntax, and a bilateral pose is drawn for its second side by flipping x, so 45
 * bilateral poses need no second figure.
 *
 * Drawn as a FILLED body, not a wire frame. The first version stroked the bones
 * at uniform width and read as a stick figure — accurate and cheap-looking. Each
 * bone is now a quad that tapers from the proximal joint to the distal one, with
 * a disc at each joint to round the articulation; overlapping shapes in one fill
 * colour merge into a silhouette, so no path union is needed.
 *
 * Its ceiling is a competent schematic. Front-facing poses in particular still
 * read as a constructed figure, because they are one. This is the fallback layer
 * for poses that have no commissioned artwork — not a substitute for it.
 *
 * Joints are all optional. A pose lying on its side needs no separate left and
 * right limbs, and omitting them draws a cleaner figure than stacking two shapes
 * a pixel apart.
 */

export const GROUND_Y = 92

// Limb widths, proximal → distal. Hands and feet are deliberately narrow: at
// forearm width they pool into a blob wherever two of them meet, which is every
// prayer position.
const W = {
  torso: 11, hip: 8.5, neck: 5.2,
  upperArm: 4.6, foreArm: 3.4, hand: 2.0,
  thigh: 6.4, calf: 4.6, foot: 2.6,
}
const HEAD_R = 6.4

const sub = (a, b) => [a[0] - b[0], a[1] - b[1]]
const norm = (v) => {
  const l = Math.hypot(v[0], v[1]) || 1
  return [v[0] / l, v[1] / l]
}

function bone(a, b, wa, wb) {
  if (!a || !b) return ''
  const d = norm(sub(b, a))
  const n = [-d[1], d[0]]
  const edge = (pt, w, side) =>
    `${pt[0] + n[0] * w * side / 2} ${pt[1] + n[1] * w * side / 2}`
  return `M${edge(a, wa, 1)} L${edge(b, wb, 1)} L${edge(b, wb, -1)} L${edge(a, wa, -1)} Z`
}

function disc(c, r) {
  if (!c) return ''
  return `M${c[0] - r} ${c[1]} a${r} ${r} 0 1 0 ${r * 2} 0 a${r} ${r} 0 1 0 ${-r * 2} 0 Z`
}

function chain(points, widths) {
  let d = ''
  for (let i = 0; i < points.length - 1; i++) {
    if (!points[i] || !points[i + 1]) continue
    d += bone(points[i], points[i + 1], widths[i], widths[i + 1])
    d += disc(points[i], widths[i] / 2)
  }
  const last = points[points.length - 1]
  if (last) d += disc(last, widths[widths.length - 1] / 2)
  return d
}

/**
 * @param {object} figure  joint map from the KB
 * @param {boolean} mirror flip horizontally (the second side of a bilateral pose)
 * @returns {{d: string}|null} one filled path
 */
export function buildPoseFigure(figure, mirror = false) {
  if (!figure || !figure.head) return null

  const f = mirror
    ? Object.fromEntries(Object.entries(figure).map(
        ([k, v]) => [k, Array.isArray(v) ? [100 - v[0], v[1]] : v]))
    : figure

  let d = ''

  // Torso: a quad when the pose carries shoulder and hip width, otherwise a
  // tapered bone along the spine — bent through `spine` so Cat and Cow keep the
  // curve that is the only thing telling them apart.
  if (f.shoulderL && f.shoulderR && f.hipL && f.hipR) {
    // Widened away from the spine axis: the joints are centres, so a quad drawn
    // straight through them is barely one head across and reads as spindly.
    const widen = (a, b, by) => {
      const dir = norm(sub(b, a))
      return [[a[0] - dir[0] * by, a[1] - dir[1] * by],
              [b[0] + dir[0] * by, b[1] + dir[1] * by]]
    }
    const [sL, sR] = widen(f.shoulderL, f.shoulderR, 2.2)
    const [hL, hR] = widen(f.hipL, f.hipR, 1.2)
    const pt = (v) => `${v[0]} ${v[1]}`
    d += `M${pt(sL)} L${pt(sR)} L${pt(hR)} L${pt(hL)} Z`
  } else if (f.spine) {
    d += chain([f.neck, f.spine, f.pelvis], [W.neck + 3, W.torso, W.hip])
  } else {
    d += chain([f.neck, f.pelvis], [W.neck + 3, W.hip])
  }

  d += chain([f.head, f.neck], [HEAD_R * 1.1, W.neck])
  d += disc(f.head, HEAD_R)

  d += chain([f.shoulderL, f.elbowL, f.wristL], [W.upperArm, W.foreArm, W.hand])
  d += chain([f.shoulderR, f.elbowR, f.wristR], [W.upperArm, W.foreArm, W.hand])
  d += chain([f.hipL, f.kneeL, f.ankleL], [W.thigh, W.calf, W.foot])
  d += chain([f.hipR, f.kneeR, f.ankleR], [W.thigh, W.calf, W.foot])
  // The unsuffixed limbs hang off the spine ends. Drawn whenever present, NOT
  // only when the L/R pair is absent: an asymmetric pose legitimately mixes the
  // two — the lunge and the pyramid describe their back leg as hipL/kneeL/ankleL
  // and their front leg bare, and gating on the pair rendered them a leg short.
  d += chain([f.neck, f.elbow, f.wrist], [W.upperArm, W.foreArm, W.hand])
  d += chain([f.pelvis, f.knee, f.ankle], [W.thigh, W.calf, W.foot])

  return { d }
}

export default buildPoseFigure
