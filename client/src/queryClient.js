import { QueryClient } from '@tanstack/react-query'
import { get, set, del } from 'idb-keyval'

// Single IndexedDB key holding the persisted React Query cache. The cache is NOT
// scoped per user, so it MUST be wiped whenever the authenticated identity
// changes (login / logout) — otherwise a second account on the same browser
// would be served the previous user's cached data (plans, profile, etc.).
const IDB_KEY = 'ayura_react_query_cache'

export const idbPersister = {
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

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      gcTime: 1000 * 60 * 60 * 24 * 7, // Keep cache for 7 days
      staleTime: 1000 * 60 * 5, // Data is fresh for 5 mins
    },
  },
})

// Drop both the in-memory queries and the persisted IndexedDB copy. Call this on
// any auth identity change so one user never sees another user's cached data.
export async function resetQueryCache() {
  queryClient.clear()
  try {
    await idbPersister.removeClient()
  } catch {
    // IDB may be unavailable (private mode); in-memory clear still applied.
  }
}
