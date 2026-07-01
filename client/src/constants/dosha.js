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
  vata:    '#818cf8',
  pitta:   '#fb923c',
  kapha:   '#34d399',
  default: '#2dd4bf', // teal accent for "tridoshic"/unknown
}

// Alias for remedy/medicine views, which key on "universal" instead of "default".
export const DOSHA_COLORS_R = {
  vata:      DOSHA_COLOR.vata,
  pitta:     DOSHA_COLOR.pitta,
  kapha:     DOSHA_COLOR.kapha,
  universal: DOSHA_COLOR.default,
}
