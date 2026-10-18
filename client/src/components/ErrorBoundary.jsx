import React from 'react'
import { m } from 'framer-motion'
import { useLocation } from 'react-router-dom'
import { reportError } from '../lib/errorReporting'
import { isChunkLoadError, isReloadingForDeploy, reloadForNewDeploy } from '../lib/staleDeploy'
import './ErrorBoundary.css'

class ErrorBoundaryInner extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidUpdate(prevProps) {
    if (this.state.hasError && this.props.location.pathname !== prevProps.location.pathname) {
      this.setState({ hasError: false, error: null })
    }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error', error, errorInfo)
    if (isReloadingForDeploy()) return
    // A stale tab after a deploy: the new build is the cure, not this screen.
    const chunk = isChunkLoadError(error)
    if (chunk && reloadForNewDeploy()) return
    // React renders a failed subtree twice before it gives up, and a failed
    // lazy import throws a fresh error object each time; one report.
    const key = `${this.props.location.pathname}|${error?.message}`
    if (this.reportedKey === key) return
    this.reportedKey = key
    // console.error alone reached nobody: Sentry does not capture the console.
    // No replay — this boundary wraps every screen, most of them health data.
    reportError(error, {
      flow: chunk ? 'stale_deploy' : 'error_boundary',
      extra: { path: this.props.location.pathname },
      noReplay: true,
    })
  }

  handleRetry = () => {
    // React.lazy caches a rejected import, so re-rendering a chunk failure
    // throws it again. Only a page load fetches the chunk afresh.
    if (isChunkLoadError(this.state.error)) {
      window.location.reload()
      return
    }
    this.setState({ hasError: false, error: null })
  }

  render() {
    // The page is about to be replaced by the new build; don't flash an error.
    if (this.state.hasError && isReloadingForDeploy()) return null
    if (this.state.hasError) {
      return (
        <div className="error-boundary-page">
          <m.div
            className="error-boundary-card"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <h1 className="error-boundary-title">Something went wrong.</h1>
            <p className="error-boundary-body">
              An unexpected error occurred. You can try again or go back to the dashboard.
            </p>
            <div className="error-boundary-actions">
              <button
                className="btn btn-primary"
                onClick={this.handleRetry}
              >
                Try Again
              </button>
              <a className="btn btn-secondary" href="/dashboard">
                Go to Dashboard
              </a>
            </div>
          </m.div>
        </div>
      )
    }

    return this.props.children
  }
}

export default function ErrorBoundary(props) {
  const location = useLocation()
  return <ErrorBoundaryInner location={location} {...props} />
}
