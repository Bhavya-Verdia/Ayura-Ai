import { useEffect, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { rewardsAPI } from '../api/client'
import { track, EVENTS } from '../lib/analytics'

// The streak and badges, shared by the dashboard and the Progress page through one
// query key. Every successful mutation invalidates ['rewards'] (queryClient.js), and
// logs written outside a mutation are picked up by the short staleTime.
export function useRewards({ announce = false } = {}) {
  const qc = useQueryClient()
  const announced = useRef(false)
  const query = useQuery({
    queryKey: ['rewards'],
    queryFn: () => rewardsAPI.get().then(r => r.data),
    staleTime: 15 * 1000,
    retry: 1,
  })
  const data = query.data
  useEffect(() => {
    if (!announce || announced.current || !Array.isArray(data?.new) || !data.new.length) return
    announced.current = true
    const byId = Object.fromEntries((Array.isArray(data.badges) ? data.badges : []).map(b => [b.id, b]))
    const earned = data.new.map(id => byId[id]).filter(Boolean)
    // One toast, however many: someone who already qualifies for four badges the
    // first time this loads should not get four notifications stacked at once.
    if (earned.length === 1) {
      toast.success(`Badge earned: ${earned[0].title}`, { description: earned[0].desc, duration: 6000 })
    } else if (earned.length > 1) {
      toast.success(`${earned.length} badges earned`, { description: earned.map(b => b.title).join(' · '), duration: 7000 })
    }
    // The badge id names a habit (a streak length, a first log), never a health fact.
    for (const b of earned) track(EVENTS.BADGE_EARNED, { badge: b.id })
    rewardsAPI.markSeen().then(() => qc.invalidateQueries({ queryKey: ['rewards'] })).catch(() => {})
  }, [announce, data, qc])
  return query
}
