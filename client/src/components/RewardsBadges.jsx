import { Link } from 'react-router-dom'
import {
  Sparkles, ScrollText, Salad, Dumbbell, Flower2, ClipboardCheck, Flame, Sun, CalendarCheck, Lock, Award,
} from 'lucide-react'
import './RewardsBadges.css'

// The badge catalogue lives on the server (services/rewards.py); this only draws it.
// Every icon name the server uses must be in this map — test_rewards.py checks.
const ICONS = { Sparkles, ScrollText, Salad, Dumbbell, Flower2, ClipboardCheck, Flame, Sun, CalendarCheck }

const CATEGORY = { start: 'Getting started', rhythm: 'Rhythm', reflect: 'Reflection', complete: 'Completion' }

function Badge({ b }) {
  const Icon = ICONS[b.icon] || Award
  const pct = Math.round((b.progress.have / b.progress.need) * 100)
  return (
    <li className={`rwd-badge${b.earned ? ' is-earned' : ''}`}
      aria-label={`${b.title}: ${b.earned ? 'earned' : `${b.progress.have} of ${b.progress.need}`}`}>
      <span className="rwd-badge-icon" aria-hidden="true">
        {b.earned ? <Icon size={20} strokeWidth={1.9} /> : <Lock size={16} strokeWidth={1.9} />}
      </span>
      <span className="rwd-badge-title">{b.title}</span>
      <span className="rwd-badge-desc">{b.desc}</span>
      {!b.earned && b.progress.need > 1 && (
        <span className="rwd-badge-progress" aria-hidden="true">
          <span style={{ width: `${pct}%` }} />
        </span>
      )}
      {b.earned && b.earned_at && (
        <span className="rwd-badge-date">{new Date(b.earned_at).toLocaleDateString()}</span>
      )}
    </li>
  )
}

// The full catalogue, grouped, for the Progress page.
export function BadgeGrid({ data }) {
  if (!Array.isArray(data?.badges)) return null
  const groups = {}
  for (const b of data.badges) (groups[b.category] ||= []).push(b)
  return (
    <section className="rwd-section" id="badges" aria-labelledby="rwd-title">
      <h2 id="rwd-title" className="rwd-title">
        <Award size={18} /> Badges <span className="rwd-count">{data.earned_count} of {data.badges.length}</span>
      </h2>
      <p className="rwd-sub">
        Earned by logging — a meal, a workout, a practice, your progress or a check-in. Never for
        weight, calories or how hard you trained.
      </p>
      {Object.entries(groups).map(([cat, list]) => (
        <div key={cat} className="rwd-group">
          <h3 className="rwd-group-title">{CATEGORY[cat] || cat}</h3>
          <ul className="rwd-grid">{list.map(b => <Badge key={b.id} b={b} />)}</ul>
        </div>
      ))}
    </section>
  )
}

// One line for the dashboard: earned count, the closest badge and how far off it is.
export function BadgeStrip({ data }) {
  if (!Array.isArray(data?.badges)) return null
  const next = data.next
  const recent = data.badges.filter(b => b.earned).slice(-3)
  return (
    <div className="rwd-strip">
      <div className="rwd-strip-earned">
        {recent.map(b => {
          const Icon = ICONS[b.icon] || Award
          return <span key={b.id} className="rwd-strip-icon" title={b.title}><Icon size={14} /></span>
        })}
        <span>{data.earned_count} of {data.badges.length} badges</span>
      </div>
      {next && (
        <div className="rwd-strip-next">
          <span>Next: <b>{next.title}</b>{next.progress.need > 1 ? ` · ${next.progress.have}/${next.progress.need}` : ''}</span>
          <span className="rwd-badge-progress" aria-hidden="true">
            <span style={{ width: `${Math.round((next.progress.have / next.progress.need) * 100)}%` }} />
          </span>
        </div>
      )}
      <Link to="/progress#badges" className="rwd-strip-link">All badges →</Link>
    </div>
  )
}
