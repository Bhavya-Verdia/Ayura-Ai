import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { HelmetProvider } from 'react-helmet-async'
import App from './App'
import { AuthProvider } from './providers/AuthContext'
import { ToastProvider } from './providers/ToastProvider'
import { ThemeProvider } from './providers/ThemeProvider'
import { QueryClient } from '@tanstack/react-query'
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client'
import { get, set, del } from 'idb-keyval'
import * as Sentry from "@sentry/react"
import './index.css'
import './i18n'

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN || "https://public@sentry.example.com/1",
  integrations: [
    Sentry.browserTracingIntegration(),
    Sentry.replayIntegration(),
  ],
  tracesSampleRate: 1.0,
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
});

const IDB_KEY = 'ayura_react_query_cache'

const idbPersister = {
  persistClient: async (client) => {
    await set(IDB_KEY, client)
  },
  restoreClient: async () => {
    return await get(IDB_KEY)
  },
  removeClient: async () => {
    await del(IDB_KEY)
  },
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      gcTime: 1000 * 60 * 60 * 24 * 7, // Keep cache for 7 days
      staleTime: 1000 * 60 * 5, // Data is fresh for 5 mins
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <HelmetProvider>
      <BrowserRouter>
        <PersistQueryClientProvider client={queryClient} persistOptions={{ persister: idbPersister, maxAge: 1000 * 60 * 60 * 24 * 7 }}>
          <AuthProvider>
            <ToastProvider>
              <ThemeProvider>
                <App />
              </ThemeProvider>
            </ToastProvider>
          </AuthProvider>
        </PersistQueryClientProvider>
      </BrowserRouter>
    </HelmetProvider>
  </React.StrictMode>
)
