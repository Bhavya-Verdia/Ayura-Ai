/**
 * Pose figures drawn from joint coordinates.
 *
 * A pose carries a `figure`: a handful of named joints in a 0-100 box, ground at
 * y=92. One renderer turns those into limbs, so every pose is drawn with the same
 * proportions, stroke weights and ground line — 113 poses look like one system
 * rather than 113 separate drawings. Authoring a pose means placing points, not
 * writing path syntax.
 *
 * The alternative was one hand-written SVG path per pose, which drifts in style
 * immediately and cannot be mirrored. Coordinates can: a bilateral pose is drawn
 * for the second side by flipping x, so 45 bilateral poses need no second figure.
 *
 * Joints are all optional. A pose lying on its side needs no separate left and
 * right limbs, and omitting them draws a cleaner figure than stacking two lines a
 * pixel apart.
 */

export const GROUND_Y = 92
export const HEAD_R = 5.5

// neck → pelvis, bending through spine if the pose gives one. Cat and Cow are the
// same skeleton apart from which way the spine curves, so a straight two-point
// spine cannot tell them apart — and 18 backbends have the same problem.
function spinePath({ neck, pelvis, spine }) {
  if (!neck || !pelvis) return null
  if (!spine) return `M${neck[0]} ${neck[1]} L${pelvis[0]} ${pelvis[1]}`
  // Quadratic control point placed so the curve passes through the given midpoint.
  const cx = 2 * spine[0] - (neck[0] + pelvis[0]) / 2
  const cy = 2 * spine[1] - (neck[1] + pelvis[1]) / 2
  return `M${neck[0]} ${neck[1]} Q${cx} ${cy} ${pelvis[0]} ${pelvis[1]}`
}

function limbPath(a, b, c) {
  if (!a || !b || !c) return null
  return `M${a[0]} ${a[1]} L${b[0]} ${b[1]} L${c[0]} ${c[1]}`
}

function segmentPath(a, b) {
  if (!a || !b) return null
  return `M${a[0]} ${a[1]} L${b[0]} ${b[1]}`
}

/**
 * @param {object} figure  joint map from the KB
 * @param {boolean} mirror flip horizontally (the second side of a bilateral pose)
 * @returns {{head: {cx,cy,r}, strokes: string[]}|null}
 */
export function buildPoseFigure(figure, mirror = false) {
  if (!figure || !figure.head) return null

  const f = mirror
    ? Object.fromEntries(Object.entries(figure).map(
        ([k, v]) => [k, Array.isArray(v) ? [100 - v[0], v[1]] : v]))
    : figure

  // Arms are drawn lighter than the spine and legs. Viewed side on, an arm and a
  // leg leaving the same point at similar angles are indistinguishable at equal
  // weight — the lunge and the forward fold both read as a tangle of sticks. The
  // weight difference is also how anatomical line drawings carry limb depth.
  const strokes = [
    { kind: 'trunk', d: spinePath(f) },
    // Shoulder and hip lines give the torso width. Skipped on side-on poses,
    // where the two sides sit on top of each other and the line is noise.
    { kind: 'trunk', d: segmentPath(f.shoulderL, f.shoulderR) },
    { kind: 'trunk', d: segmentPath(f.hipL, f.hipR) },
    { kind: 'arm', d: limbPath(f.shoulderL, f.elbowL, f.wristL) },
    { kind: 'arm', d: limbPath(f.shoulderR, f.elbowR, f.wristR) },
    { kind: 'leg', d: limbPath(f.hipL, f.kneeL, f.ankleL) },
    { kind: 'leg', d: limbPath(f.hipR, f.kneeR, f.ankleR) },
    // A side-on pose gives a single unsuffixed arm and leg, hung off the spine
    // ends so the limb is not left floating unattached. Drawn whenever present,
    // NOT only when the L/R pair is absent: an asymmetric pose legitimately mixes
    // the two — the lunge and the pyramid describe their back leg as hipL/kneeL/
    // ankleL and their front leg bare. Gating on the pair silently dropped that
    // front leg, and both poses rendered a limb short.
    { kind: 'arm', d: limbPath(f.neck, f.elbow, f.wrist) },
    { kind: 'leg', d: limbPath(f.pelvis, f.knee, f.ankle) },
  ].filter(s => s.d)

  return {
    head: { cx: f.head[0], cy: f.head[1], r: HEAD_R },
    strokes,
  }
}

export default buildPoseFigure
