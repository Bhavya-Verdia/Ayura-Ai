/* Web push subscription helpers.
 *
 * Flow: backend exposes the VAPID public key; the browser's PushManager
 * creates a per-device subscription against it; we store that subscription
 * server-side so the notification service can reach this device.
 */
import client from '../api/client'

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = window.atob(base64)
  return Uint8Array.from([...raw].map((ch) => ch.charCodeAt(0)))
}

function pushSupported() {
  return 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window
}

/** Current device state: 'unsupported' | 'denied' | 'subscribed' | 'off' */
export async function pushStatus() {
  if (!pushSupported()) return 'unsupported'
  if (Notification.permission === 'denied') return 'denied'
  const reg = await navigator.serviceWorker.getRegistration()
  const sub = await reg?.pushManager.getSubscription()
  return sub ? 'subscribed' : 'off'
}

/** Ask permission, create the browser subscription, and register it server-side.
 *  Returns 'subscribed' | 'denied' | 'unsupported' | 'unavailable'. */
export async function enablePush() {
  if (!pushSupported()) return 'unsupported'
  const { data } = await client.get('/push/vapid-public-key')
  if (!data?.enabled) return 'unavailable'
  const permission = await Notification.requestPermission()
  if (permission !== 'granted') return 'denied'
  const reg = await navigator.serviceWorker.ready
  const sub =
    (await reg.pushManager.getSubscription()) ||
    (await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(data.public_key),
    }))
  await client.post('/push/subscribe', sub.toJSON())
  return 'subscribed'
}

/** Drop the browser subscription and remove it server-side. */
export async function disablePush() {
  const reg = await navigator.serviceWorker.getRegistration()
  const sub = await reg?.pushManager.getSubscription()
  if (!sub) return
  const endpoint = sub.endpoint
  await sub.unsubscribe()
  await client.delete('/push/subscribe', { data: { endpoint } }).catch(() => {})
}
