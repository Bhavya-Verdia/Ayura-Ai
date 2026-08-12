/**
 * Naming convention for asanas, pranayama and meditation techniques.
 *
 * The Sanskrit name leads and the English name follows underneath. Sanskrit is
 * the name a teacher actually says on the mat and the name the classical texts
 * use, so on an Ayurvedic app it is the real name of the pose — English is the
 * gloss, not the other way round.
 *
 * Kept in one place because the same pair is rendered in six spots (plan rows,
 * warm-up and cool-down lists, the session player, and the drop-a-pose chips),
 * and a convention applied five times out of six looks like a bug.
 */

/** The name shown first: Sanskrit where we have it, English as the fallback. */
export function primaryName(item = {}) {
  const sanskrit = (item.sanskrit_name || '').trim()
  return sanskrit || englishOf(item) || ''
}

/**
 * The name shown underneath — English, unless it is the only name we have (in
 * which case it is already the primary and repeating it would be noise).
 */
export function secondaryName(item = {}) {
  const sanskrit = (item.sanskrit_name || '').trim()
  const english = englishOf(item)
  if (!sanskrit || !english) return null
  return sanskrit === english ? null : english
}

function englishOf(item) {
  return (item.pose_name || item.technique_name || item.english_name || '').trim()
}
