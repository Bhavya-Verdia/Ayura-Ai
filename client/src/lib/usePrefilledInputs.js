import { useLayoutEffect } from 'react'

/* A prerendered form (/login, /register) is on screen before React adopts it,
 * so it can be typed into, or filled by a password manager, first. React does
 * not read those values: state stays empty, and the next render of a
 * controlled input writes that empty state back over what the visitor sees.
 * Measured before this existed: the fields showed the typed email and password,
 * and Sign in sent {"email":"","password":""}.
 *
 * Once, on mount, copy any value already in a field into its state. `fields`
 * maps a selector inside the form to that field's setter; a checkbox passes
 * its checked state. A no-op for a form React drew itself.
 */
export function usePrefilledInputs(formRef, fields) {
  useLayoutEffect(() => {
    const form = formRef.current
    if (!form) return
    for (const [selector, set] of Object.entries(fields)) {
      const el = form.querySelector(selector)
      if (!el) continue
      if (el.type === 'checkbox') {
        if (el.checked) set(true)
      } else if (el.value) {
        set(el.value)
      }
    }
    // Once: later values arrive through onChange.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
}
