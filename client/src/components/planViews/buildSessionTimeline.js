/**
 * Flatten a generated yoga session into the ordered list of timed segments a
 * practitioner actually moves through.
 *
 * The plan is structured by section (warmup / main / cooldown) with separate
 * blocks for Surya Namaskar, pranayama and dharana. A practice is linear, and a
 * bilateral pose is two things you do, not one — so this expands unilateral
 * poses into a right and a left segment. Reading the plan, you could miss that;
 * practising it, the app has to tell you when to switch.
 */

import { primaryName, secondaryName } from './poseNames'

const SECTION_LABEL = {
  surya_namaskar: 'Surya Namaskar',
  warmup: 'Warm-up',
  main: 'Main practice',
  cooldown: 'Cool-down',
  pranayama: 'Pranayama',
  dharana: 'Meditation',
  final_relaxation: 'Final relaxation',
}

export const SEGMENT_KIND = {
  FLOW: 'flow',
  POSE: 'pose',
  BREATH: 'breath',
  MEDITATION: 'meditation',
}

function poseSegments(pose, section) {
  const base = {
    kind: SEGMENT_KIND.POSE,
    section,
    sectionLabel: SECTION_LABEL[section],
    poseId: pose.pose_id,
    title: primaryName(pose),
    subtitle: secondaryName(pose),
    instructions: pose.instructions || [],
    modification: pose.modification,
    breathCue: pose.pranayama_sync,
    rationale: pose.ayurvedic_rationale,
    imageUrl: pose.image_url,
    figure: pose.figure,
    category: pose.category,
    benefits: pose.primary_benefits || [],
  }

  const hold = pose.duration_seconds || 30
  if (!pose.bilateral) return [{ ...base, seconds: hold, side: null }]

  // Both sides, announced separately. A single combined countdown would leave
  // the practitioner guessing when to switch.
  const name = primaryName(pose)
  // The drawn figure is mirrored for the second side rather than needing a second
  // set of coordinates — the whole reason poses are stored as joints.
  return [
    { ...base, seconds: hold, side: 'right', title: `${name} — right side` },
    { ...base, seconds: hold, side: 'left', title: `${name} — left side`, mirror: true },
  ]
}

export function buildSessionTimeline(session) {
  if (!session) return []
  const segments = []

  const sns = session.surya_namaskar
  if (sns) {
    segments.push({
      kind: SEGMENT_KIND.FLOW,
      section: 'surya_namaskar',
      sectionLabel: SECTION_LABEL.surya_namaskar,
      title: 'Surya Namaskar',
      subtitle: `${sns.rounds} round${sns.rounds > 1 ? 's' : ''} · ${sns.pace} pace`,
      seconds: Math.round((sns.duration_minutes || 0) * 60),
      steps: sns.steps || [],
      note: sns.pace_note,
      safetyNotes: sns.safety_notes || [],
      seniorModification: sns.senior_modification,
    })
  }

  for (const p of session.warmup || []) segments.push(...poseSegments(p, 'warmup'))
  for (const p of session.main_sequence || []) segments.push(...poseSegments(p, 'main'))

  // Savasana closes the practice, after the breathwork and the meditation — not
  // in the middle of the cooldown, which would have the practitioner settle into
  // full relaxation and then get up again to do pranayama.
  const cooldown = session.cooldown || []
  for (const p of cooldown.filter(p => !p.final_relaxation)) {
    segments.push(...poseSegments(p, 'cooldown'))
  }

  for (const pr of session.pranayama_section || []) {
    segments.push({
      kind: SEGMENT_KIND.BREATH,
      section: 'pranayama',
      sectionLabel: SECTION_LABEL.pranayama,
      title: primaryName(pr),
      subtitle: secondaryName(pr),
      seconds: Math.round((pr.duration_minutes || 0) * 60),
      instructions: pr.instructions || [],
      note: pr.dosha_note,
    })
  }

  const dh = session.dharana_section
  if (dh) {
    segments.push({
      kind: SEGMENT_KIND.MEDITATION,
      section: 'dharana',
      sectionLabel: SECTION_LABEL.dharana,
      title: dh.sanskrit_name || dh.technique,
      subtitle: dh.sanskrit_name ? dh.technique : null,
      seconds: Math.round((dh.duration_minutes || 0) * 60),
      instructions: dh.instructions || [],
      note: dh.dosha_note,
      reference: dh.classical_reference,
    })
  }

  for (const p of cooldown.filter(p => p.final_relaxation)) {
    segments.push(...poseSegments(p, 'final_relaxation'))
  }

  return segments.filter(s => s.seconds > 0)
}

export function timelineTotalSeconds(segments) {
  return segments.reduce((sum, s) => sum + s.seconds, 0)
}

export function formatClock(totalSeconds) {
  const s = Math.max(0, Math.round(totalSeconds))
  const m = Math.floor(s / 60)
  return `${m}:${String(s % 60).padStart(2, '0')}`
}
