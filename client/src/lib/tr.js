/* Translate a screen string: `tr('settings.saveProfile', 'Save Profile', { name })`.
 *
 * The English is the default and lives at the call, so a key that is missing from a
 * locale shows English rather than a key. `scripts/i18n-strings.mjs` reads every
 * call back into `locales/en.json`, and `server/tests/test_ui_i18n.py` holds the
 * other locales to the same keys and placeholders.
 *
 * It reads the i18n singleton, not a hook, so module-level tables can use it from a
 * getter. The app is keyed on the language (App.jsx), so a change re-renders every
 * screen. */
import i18n from '../i18n'

export function tr(key, english, vars) {
  return i18n.t(key, { defaultValue: english, ...(vars || {}) })
}
