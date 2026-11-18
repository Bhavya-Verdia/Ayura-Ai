/* An in-page "are you sure?" in place of window.confirm.
 *
 * The native dialog blocks the whole page, cannot be styled or translated beyond
 * its message, and looks like a browser warning rather than part of the app. This
 * is the Reminders delete pattern made shared: the question appears where the
 * action was, focus moves to Cancel (the safe answer), and Escape cancels. */
import { useEffect, useRef } from 'react'
import './InlineConfirm.css'

export default function InlineConfirm({ message, confirmLabel, cancelLabel, onConfirm, onCancel, className = '' }) {
  const cancelRef = useRef(null)
  useEffect(() => { cancelRef.current?.focus() }, [])
  return (
    <div
      className={`inline-confirm ${className}`}
      role="alertdialog"
      aria-live="assertive"
      onKeyDown={e => { if (e.key === 'Escape') { e.stopPropagation(); onCancel() } }}
    >
      <span className="inline-confirm-msg">{message}</span>
      <div className="inline-confirm-actions">
        <button type="button" ref={cancelRef} className="btn btn-secondary btn-sm" onClick={onCancel}>{cancelLabel}</button>
        <button type="button" className="btn btn-sm inline-confirm-danger" onClick={onConfirm}>{confirmLabel}</button>
      </div>
    </div>
  )
}
