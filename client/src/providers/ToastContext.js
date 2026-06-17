import { createContext } from 'react'

/**
 * Toast context — holds the toast function (addToast) provided by ToastProvider.
 * Used by pages/components via `useToast()`.
 */
export const ToastContext = createContext(null)
