/* Web push handlers, imported into the generated Workbox service worker via
 * workbox.importScripts (vite.config.js). Payload shape is set by the backend:
 * services/notification_service._send_push → { title, body, url }. */

self.addEventListener('push', (event) => {
  let data = {}
  try {
    data = event.data ? event.data.json() : {}
  } catch {
    data = { body: event.data ? event.data.text() : '' }
  }
  event.waitUntil(
    self.registration.showNotification(data.title || 'Ayura AI', {
      body: data.body || '',
      icon: '/pwa-192x192.png',
      badge: '/pwa-192x192.png',
      data: { url: data.url || '/notifications' },
      tag: data.tag || 'ayura-notification',
    })
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const url = (event.notification.data && event.notification.data.url) || '/'
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((wins) => {
      for (const win of wins) {
        if ('focus' in win) {
          win.navigate(url)
          return win.focus()
        }
      }
      return self.clients.openWindow(url)
    })
  )
})
