import { SkeletonLine, SkeletonCircle } from './Skeleton'

/* Stand-in for the authenticated app shell while /profile/me is still in flight.
 *
 * The auth gate used to render the full-screen LoadingScreen spinner here, which
 * on a throttled phone meant the sequence was blank → centred spinner → the app
 * appearing all at once (the spinner alone held the screen for ~550ms). A
 * silhouette of the shell reads as the app already being there and filling in,
 * and — because the sidebar/top-bar/tab-bar occupy the same boxes as the real
 * chrome — nothing jumps when the real shell mounts.
 *
 * It deliberately does NOT reuse the real `.dash-sidebar` / `.mobile-bottom-nav`
 * classes: those live in Dashboard.css / MainLayout.css, which are lazy chunks
 * that by definition have not loaded yet at this point. Using them would render
 * an unstyled pile — worse than the spinner. The `.shell-skel-*` rules live in
 * index.css (always loaded) and mirror the real dimensions; see the comment
 * beside them for the numbers that must stay in sync.
 *
 * The content area is intentionally generic (title + cards) rather than
 * dashboard-shaped: this gate covers every in-shell route, and promising a
 * dashboard hero on /settings would be a worse lie than promising nothing.
 */
export default function ShellSkeleton() {
  return (
    <div className="shell-skel fill-viewport" role="status" aria-label="Loading your account">
      <aside className="shell-skel-sidebar" aria-hidden="true">
        <div className="shell-skel-brand">
          <SkeletonCircle size="26px" style={{ borderRadius: '8px' }} />
          <SkeletonLine width="86px" height="14px" />
        </div>
        <div className="shell-skel-profile">
          <SkeletonCircle size="42px" />
          <div style={{ flex: 1, minWidth: 0 }}>
            <SkeletonLine width="72%" height="13px" style={{ marginBottom: '7px' }} />
            <SkeletonLine width="46%" height="11px" />
          </div>
        </div>
        <div className="shell-skel-nav">
          {/* Eight rows, not the real twelve: enough to read as a nav column
              without stacking a dozen more shimmer animations behind a state
              that lasts under a second. */}
          {Array.from({ length: 8 }, (_, i) => (
            <SkeletonLine key={i} height="17px" width={`${64 + ((i * 37) % 3) * 11}%`} />
          ))}
        </div>
      </aside>

      <div className="shell-skel-main">
        <div className="shell-skel-topbar" aria-hidden="true" />
        <div className="shell-skel-content" aria-hidden="true">
          <SkeletonLine width="40%" height="26px" style={{ maxWidth: '320px' }} />
          <div className="shell-skel-grid">
            {Array.from({ length: 4 }, (_, i) => (
              <div className="skeleton-plan-card" key={i}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
                  <SkeletonCircle size="34px" style={{ borderRadius: '10px' }} />
                  <SkeletonLine width="52%" height="15px" />
                </div>
                <SkeletonLine width="88%" height="12px" style={{ marginBottom: '7px' }} />
                <SkeletonLine width="66%" height="12px" />
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="shell-skel-tabbar" aria-hidden="true" />
    </div>
  )
}
