// Shared by GymView and GymBlocks; kept out of the component file so fast
// refresh can treat that one as components only.
const BLOCK_DAYS = 28

/** Four weeks since the plan was written, or anything logged in week four. */
export function blockIsOver(plan, logs) {
  const generated = Date.parse(plan?.generated_at || '')
  const aged = Number.isFinite(generated) && Date.now() - generated >= BLOCK_DAYS * 864e5
  return aged || Object.keys(logs || {}).some(k => k.startsWith('4:'))
}

