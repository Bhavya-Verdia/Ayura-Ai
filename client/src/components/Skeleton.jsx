export function SkeletonLine({ width = '100%', height = '14px', style = {} }) {
  return (
    <div
      className="skeleton-line"
      style={{ width, height, borderRadius: '6px', ...style }}
    />
  )
}

export function SkeletonCircle({ size = '40px', style = {} }) {
  return (
    <div
      className="skeleton-line"
      style={{ width: size, height: size, borderRadius: '50%', flexShrink: 0, ...style }}
    />
  )
}

function SkeletonPlanCard() {
  return (
    <div className="skeleton-plan-card" aria-hidden="true">
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
        <SkeletonCircle size="36px" style={{ borderRadius: '10px' }} />
        <SkeletonLine width="55%" height="16px" />
      </div>
      <SkeletonLine width="90%" height="12px" style={{ marginBottom: 7 }} />
      <SkeletonLine width="70%" height="12px" style={{ marginBottom: 20 }} />
      <SkeletonLine width="40%" height="34px" style={{ borderRadius: '10px' }} />
    </div>
  )
}

function SkeletonHeroCard() {
  return (
    <div className="skeleton-hero-card" aria-hidden="true">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
        <div style={{ flex: 1, minWidth: 200 }}>
          <SkeletonLine width="40%" height="13px" style={{ marginBottom: 10 }} />
          <SkeletonLine width="70%" height="28px" style={{ marginBottom: 8 }} />
          <SkeletonLine width="55%" height="13px" />
        </div>
        <div style={{ display: 'flex', gap: 16 }}>
          <SkeletonCircle size="120px" style={{ borderRadius: '50%' }} />
          <SkeletonCircle size="120px" style={{ borderRadius: '50%' }} />
        </div>
      </div>
    </div>
  )
}

export function SkeletonDashboard() {
  return (
    <div className="dash-content" aria-busy="true" aria-label="Loading dashboard">
      <SkeletonHeroCard />
      <div style={{ height: 16 }} />
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 16 }}>
        {Array.from({ length: 6 }, (_, i) => <SkeletonPlanCard key={i} />)}
      </div>
    </div>
  )
}

function SkeletonChatBubble({ isUser = false }) {
  return (
    <div className={`chat-bubble-row ${isUser ? 'user' : 'ai'}`} aria-hidden="true">
      {!isUser && <SkeletonCircle size="32px" />}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, flex: 1, maxWidth: '65%' }}>
        <SkeletonLine height="42px" style={{ borderRadius: '16px' }} />
        <SkeletonLine width="60%" height="10px" />
      </div>
    </div>
  )
}

export function SkeletonChat() {
  return (
    <div className="chat-canvas" aria-busy="true" aria-label="Loading chat">
      <div className="chat-history" style={{ gap: 20, display: 'flex', flexDirection: 'column', padding: 24 }}>
        <SkeletonChatBubble />
        <SkeletonChatBubble isUser />
        <SkeletonChatBubble />
        <SkeletonChatBubble isUser />
      </div>
    </div>
  )
}
