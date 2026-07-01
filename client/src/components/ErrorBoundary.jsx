import React from 'react'
import { m } from 'framer-motion'
import { useLocation } from 'react-router-dom'
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
  }

  render() {
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
                onClick={() => this.setState({ hasError: false, error: null })}
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
