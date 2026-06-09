export default function LoadingScreen({ message = 'Loading your wellness space' }) {
  return (
    <div className="loading-screen" role="status" aria-live="polite" aria-label={message}>
      <div className="loading-mark" aria-hidden="true">
        <span className="loading-mark-ring" />
        <span className="loading-mark-core" />
        <span className="loading-mark-pulse" />
      </div>
      <p className="loading-message">{message}</p>
      <div className="loading-bar">
        <div className="loading-bar-fill" />
      </div>
    </div>
  )
}
