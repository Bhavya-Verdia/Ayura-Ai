import React, { useEffect, useState } from 'react'
import { Award, RefreshCw, TrendingUp, ArrowUpCircle } from 'lucide-react'
import { workoutsAPI } from '../../api/client'
import { track, trackOnce, EVENTS } from '../../lib/analytics'

/**
 * The end of a block. Week four used to be the last page of the plan and
 * nothing came after it — someone who did not think to regenerate repeated
 * the deload week. This says what the block came to and starts the next one.
 */
export function GymBlockComplete({ plan, over, onRegenerate }) {
  const [summary, setSummary] = useState(null)
  const planId = plan?.plan_id
  useEffect(() => {
    if (!planId) return
    let live = true
    workoutsAPI.summary(planId).then(({ data }) => { if (live) setSummary(data) }).catch(() => {})
    return () => { live = false }
  }, [planId])
  const blockNo = plan?.user_summary?.block || 1
  useEffect(() => {
    if (over && planId) {
      trackOnce(`block-over:${planId}`, EVENTS.GYM_BLOCK_COMPLETE_SHOWN, { block: blockNo })
    }
  }, [over, planId, blockNo])

  const block = plan?.user_summary?.block || 1
  const builds = summary ? summary.progress : true
  // The engine adds a main-lift set once, going into block 2, and never in
  // pregnancy — which is maintained, not progressed.
  const extraSet = block === 1 && !/PREGNANCY/.test(plan?.disclaimer || '')
  const done = summary?.sessions_logged ?? 0
  const planned = summary?.sessions_planned ?? 0
  return (
    <div className={`gym-block-card${over ? ' over' : ''}`}>
      <span className="gym-checkin-title">
        <Award size={16} /> {over ? `Block ${block} complete` : `When you finish week 4`}
      </span>
      {summary && (
        <p className="gym-block-line">
          You logged <strong>{done} of {planned}</strong> sessions
          {summary.progressed?.length > 0 && <> — {summary.progressed.slice(0, 3)
            .map(p => `${p.exercise} +${p.change_percent}%`).join(', ')}</>}.
        </p>
      )}
      <p className="gym-block-line gym-block-next">
        {builds
          ? `Block ${block + 1} builds on it: your main lifts stay and start from the weights you logged${extraSet ? ', with one more set' : ''}, and one exercise a day is new.`
          : `Fewer than half the sessions were logged, so the next block repeats this one's structure from the weights you logged. Finish more of it and the one after will build.`}
      </p>
      {onRegenerate && (
        <button type="button" className="gym-log-save gym-checkin-rebuild"
          onClick={() => {
            track(EVENTS.GYM_NEXT_BLOCK_STARTED, { from_block: block, builds, early: !over,
              sessions_logged: summary?.sessions_logged ?? null,
              sessions_planned: summary?.sessions_planned ?? null })
            onRegenerate()
          }}>
          <RefreshCw size={12} /> {builds ? `Start block ${block + 1}` : 'Start the next block'}
        </button>
      )}
    </div>
  )
}

const fmt = (kg) => `${Math.round(kg)} kg`

/**
 * Every block trained, read from every gym plan rather than the six-week load
 * window, so month one still counts in month four. And, when the evidence is
 * there, an offer — never an automatic change — of the next level: intermediate
 * after three blocks, advanced after two more at intermediate.
 */
export function GymBlockHistory({ onRegenerate }) {
  const [data, setData] = useState(null)
  const [state, setState] = useState('idle')
  useEffect(() => {
    let live = true
    workoutsAPI.blocks().then(({ data }) => {
      if (!live) return
      setData(data)
      if (data?.level_up) {
        trackOnce(`level-up:${data.level_up.to}`, EVENTS.GYM_LEVEL_UP_OFFERED,
          { to: data.level_up.to, blocks: data.level_up.blocks })
      }
    }).catch(() => {})
    return () => { live = false }
  }, [])

  const blocks = data?.blocks || []
  if (!blocks.length) return null

  // A lift's estimated max, block by block, for the lifts measured most often.
  const series = {}
  blocks.forEach((b, i) => {
    Object.entries(b.best_lifts || {}).forEach(([id, l]) => {
      series[id] = series[id] || { name: l.name, points: [] }
      series[id].points.push({ block: i + 1, one_rm: l.one_rm })
    })
  })
  const trends = Object.values(series).filter(s => s.points.length >= 2)
    .sort((a, b) => b.points.length - a.points.length).slice(0, 4)

  const offer = data?.level_up
  const accept = async () => {
    setState('saving')
    try {
      await workoutsAPI.levelUp()
      setState('done')
      track(EVENTS.GYM_LEVEL_UP_ACCEPTED, { to: offer.to })
      onRegenerate?.()
    } catch {
      setState('error')
    }
  }

  return (
    <section className="gym-history" aria-labelledby="gym-history-title">
      <h3 id="gym-history-title" className="gym-tips-title"><TrendingUp size={14} /> Your blocks</h3>
      {offer && (
        <div className="gym-block-card over">
          <span className="gym-checkin-title"><ArrowUpCircle size={16} /> Ready for {offer.to} programming</span>
          <p className="gym-block-line">{offer.reason}</p>
          {offer.gains?.length > 0 && (
            <p className="gym-block-line">
              Across those blocks: {offer.gains.map(g => `${g.exercise} +${g.change_percent}%`).join(', ')}.
            </p>
          )}
          <button type="button" className="gym-log-save gym-checkin-rebuild" onClick={accept}
            disabled={state === 'saving'}>
            {state === 'saving' ? 'Saving…' : `Move to ${offer.to} and rebuild my plan`}
          </button>
          {state === 'error' && <p className="gym-log-error">Could not change it — try again.</p>}
        </div>
      )}
      <ol className="gym-history-list">
        {blocks.map((b, i) => (
          <li key={b.plan_id} className="gym-history-row">
            <span className="gym-history-k">Block {i + 1}{b.finished ? '' : ' · in progress'}</span>
            <span className="gym-history-v">
              {b.sessions_logged} of {b.sessions_planned} sessions
              {b.progressed?.[0] && ` · ${b.progressed[0].exercise} +${b.progressed[0].change_percent}%`}
            </span>
          </li>
        ))}
      </ol>
      {trends.length > 0 && (
        <div className="gym-history-trends">
          {trends.map(t => (
            <p key={t.name} className="gym-history-trend">
              <strong>{t.name}</strong>{' '}
              {t.points.map(p => fmt(p.one_rm)).join(' → ')}
            </p>
          ))}
          <p className="gym-history-note">Estimated one-rep max from your best logged set in each block.</p>
        </div>
      )}
    </section>
  )
}
