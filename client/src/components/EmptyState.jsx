import { m } from 'framer-motion'

/* The app's one "nothing here yet" surface.
 *
 * Lifted from HealthTimeline's `.ht-empty`, which was the only screen treating
 * emptiness as an invitation (dashed card, icon, a line of encouragement, and a
 * way forward) rather than as data. The dashboard and /progress used to render
 * zeroes instead — a "0% COMPLETE / 0 of 7 plans generated" score ring and four
 * 0-value stat tiles — so a user's first ever session opened on what read as a
 * report of failure.
 *
 * Extracted here rather than copied a third time so the three screens cannot
 * drift apart. Styles live in index.css (not a page chunk) precisely because
 * every page is a potential caller.
 *
 * `actions` takes JSX so callers can pass react-router <Link>s. Use Link, not
 * <a href>: an anchor triggers a full document navigation, which throws away the
 * SPA and re-runs the whole ~1.4s boot to move one route.
 */
export default function EmptyState({ icon: Icon, title, description, actions, className = '' }) {
  return (
    <m.div
      className={`empty-state ${className}`.trim()}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
    >
      {Icon && (
        <div className="empty-state-orb" aria-hidden="true">
          <Icon size={34} strokeWidth={1.6} />
        </div>
      )}
      <h3 className="empty-state-title">{title}</h3>
      {description && <p className="empty-state-desc">{description}</p>}
      {actions && <div className="empty-state-actions">{actions}</div>}
    </m.div>
  )
}
