// Single source of truth for dosha accent colors.
//
// These mirror the --vata-color / --pitta-color / --kapha-color CSS tokens in
// index.css (dark-theme values). They are kept as hex (not `var(--…)`) because
// most callers append an alpha suffix, e.g. `${color}44`, which only works on a
// literal hex string. For plain color/background usage in JSX you may prefer the
// theme-flipping CSS token directly.
//
// Do NOT redefine these maps locally — every dosha color in the app resolves here
// so the same dosha always renders the same color across pages.
export const DOSHA_COLOR = {
  vata:    '#a08cf0', // air/ether — soft lavender
  pitta:   '#e0863f', // fire — terracotta
  kapha:   '#5cab74', // earth/water — herbal green
  default: '#5cab74', // herbal-green accent for "tridoshic"/unknown
}

// Theme-flipping counterpart, for when the dosha colour is used as TEXT.
// The hexes above are the dark-theme values; used as ink on a light surface
// they measured 2.14-4.22:1 (pitta on the near-white plan cards is the worst).
// `--{dosha}-ink` carries a deepened light value, so this clears AA in both
// themes. Keep using DOSHA_COLOR for `${hex}44` tints — alpha suffixes need a
// literal hex, and a translucent tint reads fine either way.
export const doshaInk = (dosha) => {
  const key = (dosha || '').toLowerCase()
  return ['vata', 'pitta', 'kapha'].includes(key) ? `var(--${key}-ink)` : 'var(--kapha-ink)'
}

// Alias for remedy/medicine views, which key on "universal" instead of "default".
export const DOSHA_COLORS_R = {
  vata:      DOSHA_COLOR.vata,
  pitta:     DOSHA_COLOR.pitta,
  kapha:     DOSHA_COLOR.kapha,
  universal: DOSHA_COLOR.default,
}
